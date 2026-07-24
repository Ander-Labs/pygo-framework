// Package parser builds a PyGo AST from a lexer token stream.
//
// Python-style indentation is modelled via the INDENT/DEDENT/NEWLINE tokens
// produced by the lexer. Handler and function bodies are captured verbatim
// from the original source (they are valid Python and gen_py re-emits them
// almost 1:1), so the parser is constructed with both the tokens and the raw
// source lines.
package parser

import (
	"fmt"
	"strings"

	"github.com/ander-labs/pygo/core/transpiler/ast"
	"github.com/ander-labs/pygo/core/transpiler/lexer"
)

// Parser holds parsing state.
type Parser struct {
	tokens []lexer.Token
	src    []string // original physical source lines (1-indexed via [n-1])
	pos    int
}

// New creates a parser over the given tokens and source text.
func New(tokens []lexer.Token, src string) *Parser {
	src = strings.ReplaceAll(src, "\r\n", "\n")
	src = strings.ReplaceAll(src, "\r", "\n")
	return &Parser{
		tokens: tokens,
		src:    strings.Split(src, "\n"),
	}
}

func (p *Parser) cur() lexer.Token  { return p.tokens[p.pos] }
func (p *Parser) peek(n int) lexer.Token {
	i := p.pos + n
	if i >= len(p.tokens) {
		return p.tokens[len(p.tokens)-1] // EOF
	}
	return p.tokens[i]
}
func (p *Parser) advance() lexer.Token {
	t := p.tokens[p.pos]
	if p.pos < len(p.tokens)-1 {
		p.pos++
	}
	return t
}

// skipNewlines consumes any NEWLINE/INDENT/DEDENT tokens (used between decls).
func (p *Parser) skipTrivia() {
	for {
		switch p.cur().Type {
		case lexer.TokenNewline, lexer.TokenIndent, lexer.TokenDedent:
			p.advance()
		default:
			return
		}
	}
}

// Parse consumes the token stream and returns the Program root.
func (p *Parser) Parse() (*ast.Program, error) {
	prog := &ast.Program{}
	for {
		p.skipTrivia()
		t := p.cur()
		if t.Type == lexer.TokenEOF {
			break
		}
		switch t.Type {
		case lexer.TokenModel:
			m, err := p.parseModel()
			if err != nil {
				return nil, err
			}
			prog.Models = append(prog.Models, m)
			prog.Decls = append(prog.Decls, m)
		case lexer.TokenRoute:
			r, err := p.parseRoute()
			if err != nil {
				return nil, err
			}
			prog.Routes = append(prog.Routes, r)
			prog.Decls = append(prog.Decls, r)
		case lexer.TokenHandler:
			h, err := p.parseHandler()
			if err != nil {
				return nil, err
			}
			prog.Handlers = append(prog.Handlers, h)
			prog.Decls = append(prog.Decls, h)
		case lexer.TokenFunction:
			f, err := p.parseFunction()
			if err != nil {
				return nil, err
			}
			prog.Functions = append(prog.Functions, f)
			prog.Decls = append(prog.Decls, f)
		default:
			return nil, fmt.Errorf("line %d: unexpected token %s %q at top level",
				t.Line, t.Type, t.Value)
		}
	}
	return prog, nil
}

// parseModel parses: model Name: NEWLINE INDENT (field NEWLINE)+ DEDENT
func (p *Parser) parseModel() (*ast.ModelNode, error) {
	kw := p.advance() // model
	nameTok := p.cur()
	if nameTok.Type != lexer.TokenIdent {
		return nil, fmt.Errorf("line %d: expected model name, got %q", nameTok.Line, nameTok.Value)
	}
	p.advance()
	if err := p.expect(lexer.TokenColon); err != nil {
		return nil, err
	}
	m := &ast.ModelNode{Name: nameTok.Value, Line: kw.Line}

	p.expectOptional(lexer.TokenNewline)
	if p.cur().Type != lexer.TokenIndent {
		return m, nil // empty model
	}
	p.advance() // INDENT

	for p.cur().Type != lexer.TokenDedent && p.cur().Type != lexer.TokenEOF {
		if p.cur().Type == lexer.TokenNewline {
			p.advance()
			continue
		}
		field, err := p.parseField(true)
		if err != nil {
			return nil, err
		}
		m.Fields = append(m.Fields, field)
		p.expectOptional(lexer.TokenNewline)
	}
	p.expectOptional(lexer.TokenDedent)
	return m, nil
}

// parseField parses `name: Type[?] [= default]`. When allowDefault is false
// (function/handler params) the default clause is still tolerated.
func (p *Parser) parseField(allowDefault bool) (*ast.FieldNode, error) {
	nameTok := p.cur()
	if nameTok.Type != lexer.TokenIdent {
		return nil, fmt.Errorf("line %d: expected field name, got %q", nameTok.Line, nameTok.Value)
	}
	p.advance()
	if err := p.expect(lexer.TokenColon); err != nil {
		return nil, err
	}
	tr, err := p.parseType()
	if err != nil {
		return nil, err
	}
	f := &ast.FieldNode{Name: nameTok.Value, Type: tr, Line: nameTok.Line}

	if p.cur().Type == lexer.TokenAssign {
		p.advance()
		f.Default = p.parseDefaultExpr()
	}
	return f, nil
}

// parseType parses a type reference: Base, Base?, Base | None, Base[Inner],
// Optional[Inner], Array[Inner], Map[Key]Val.
func (p *Parser) parseType() (*ast.TypeRef, error) {
	t := p.cur()
	if t.Type != lexer.TokenType_ && t.Type != lexer.TokenIdent {
		return nil, fmt.Errorf("line %d: expected type, got %q", t.Line, t.Value)
	}
	p.advance()
	tr := &ast.TypeRef{Name: t.Value}

	// Bracketed inner types: [Inner] (and Map[K]V second bracket handled loosely).
	if p.cur().Type == lexer.TokenLBracket {
		p.advance()
		inner, err := p.parseType()
		if err != nil {
			return nil, err
		}
		if err := p.expect(lexer.TokenRBracket); err != nil {
			return nil, err
		}
		if tr.Name == "Map" {
			tr.Key = inner
			if p.cur().Type == lexer.TokenType_ || p.cur().Type == lexer.TokenIdent {
				val, err := p.parseType()
				if err != nil {
					return nil, err
				}
				tr.Inner = val
			}
		} else {
			tr.Inner = inner
		}
	}

	// Optional sugar: `?`
	if p.cur().Type == lexer.TokenQuestion {
		p.advance()
		tr.Optional = true
	}

	// Optional sugar: `| None`
	if p.cur().Type == lexer.TokenPipe {
		p.advance()
		none := p.cur()
		if none.Type == lexer.TokenIdent && none.Value == "None" {
			p.advance()
			tr.Optional = true
		}
	}

	if tr.Name == "Optional" {
		tr.Optional = true
	}
	return tr, nil
}

// parseDefaultExpr reads default tokens until NEWLINE / DEDENT / EOF / comma.
func (p *Parser) parseDefaultExpr() string {
	var parts []string
	for {
		t := p.cur()
		if t.Type == lexer.TokenNewline || t.Type == lexer.TokenDedent ||
			t.Type == lexer.TokenEOF || t.Type == lexer.TokenComma ||
			t.Type == lexer.TokenRParen {
			break
		}
		parts = append(parts, t.Value)
		p.advance()
	}
	return strings.Join(parts, "")
}

// parseRoute parses: route METHOD /path -> handler
func (p *Parser) parseRoute() (*ast.RouteNode, error) {
	kw := p.advance() // route
	methodTok := p.cur()
	if methodTok.Type != lexer.TokenIdent {
		return nil, fmt.Errorf("line %d: expected HTTP method, got %q", methodTok.Line, methodTok.Value)
	}
	p.advance()

	// Path: reconstruct from tokens until ARROW.
	var pathSB strings.Builder
	for p.cur().Type != lexer.TokenArrow && p.cur().Type != lexer.TokenNewline && p.cur().Type != lexer.TokenEOF {
		pathSB.WriteString(p.cur().Value)
		p.advance()
	}
	if err := p.expect(lexer.TokenArrow); err != nil {
		return nil, err
	}
	handlerTok := p.cur()
	if handlerTok.Type != lexer.TokenIdent {
		return nil, fmt.Errorf("line %d: expected handler name after ->, got %q", handlerTok.Line, handlerTok.Value)
	}
	p.advance()

	r := &ast.RouteNode{
		Method:  strings.ToUpper(methodTok.Value),
		Path:    pathSB.String(),
		Handler: handlerTok.Value,
		Line:    kw.Line,
	}
	p.expectOptional(lexer.TokenNewline)
	return r, nil
}

// parseHandler parses a handler definition + verbatim body.
func (p *Parser) parseHandler() (*ast.HandlerNode, error) {
	kw := p.advance() // handler
	name, params, ret, err := p.parseSignature()
	if err != nil {
		return nil, err
	}
	body := p.captureBody()
	return &ast.HandlerNode{
		Name:       name,
		Params:     params,
		ReturnType: ret,
		Body:       body,
		Line:       kw.Line,
	}, nil
}

// parseFunction parses a function definition + verbatim body.
func (p *Parser) parseFunction() (*ast.FunctionNode, error) {
	kw := p.advance() // function
	name, params, ret, err := p.parseSignature()
	if err != nil {
		return nil, err
	}
	body := p.captureBody()
	return &ast.FunctionNode{
		Name:       name,
		Params:     params,
		ReturnType: ret,
		Body:       body,
		Line:       kw.Line,
	}, nil
}

// parseSignature parses `name(params) [-> RetType]:` and stops after the colon.
func (p *Parser) parseSignature() (name string, params []*ast.FieldNode, ret *ast.TypeRef, err error) {
	nameTok := p.cur()
	if nameTok.Type != lexer.TokenIdent {
		return "", nil, nil, fmt.Errorf("line %d: expected name, got %q", nameTok.Line, nameTok.Value)
	}
	name = nameTok.Value
	p.advance()

	if err = p.expect(lexer.TokenLParen); err != nil {
		return
	}
	for p.cur().Type != lexer.TokenRParen && p.cur().Type != lexer.TokenEOF {
		if p.cur().Type == lexer.TokenComma {
			p.advance()
			continue
		}
		var f *ast.FieldNode
		f, err = p.parseField(true)
		if err != nil {
			return
		}
		params = append(params, f)
	}
	if err = p.expect(lexer.TokenRParen); err != nil {
		return
	}

	if p.cur().Type == lexer.TokenArrow {
		p.advance()
		ret, err = p.parseType()
		if err != nil {
			return
		}
	}
	if err = p.expect(lexer.TokenColon); err != nil {
		return
	}
	return
}

// captureBody grabs the verbatim source lines of an indented block following
// a `:`-terminated signature. It uses the INDENT/DEDENT tokens to find the
// span, and slices the original source for exact text. Leading common
// indentation is stripped so gen_py can re-indent under `def`.
func (p *Parser) captureBody() []string {
	p.expectOptional(lexer.TokenNewline)
	if p.cur().Type != lexer.TokenIndent {
		return nil
	}
	p.advance() // consume INDENT

	// First body line is the source line of the current token.
	startLine := p.cur().Line

	depth := 1
	lastLine := startLine
	for depth > 0 && p.cur().Type != lexer.TokenEOF {
		switch p.cur().Type {
		case lexer.TokenIndent:
			depth++
		case lexer.TokenDedent:
			depth--
			if depth == 0 {
				p.advance()
				goto done
			}
		default:
			if p.cur().Line > lastLine {
				lastLine = p.cur().Line
			}
		}
		p.advance()
	}
done:
	// Slice raw source lines [startLine-1 .. lastLine-1].
	var raw []string
	for i := startLine - 1; i < lastLine && i < len(p.src); i++ {
		raw = append(raw, p.src[i])
	}
	return dedentCommon(raw)
}

// dedentCommon strips the smallest common leading-whitespace prefix from the
// non-blank lines.
func dedentCommon(lines []string) []string {
	min := -1
	for _, ln := range lines {
		if strings.TrimSpace(ln) == "" {
			continue
		}
		n := len(ln) - len(strings.TrimLeft(ln, " \t"))
		if min == -1 || n < min {
			min = n
		}
	}
	if min <= 0 {
		return lines
	}
	out := make([]string, len(lines))
	for i, ln := range lines {
		if len(ln) >= min {
			out[i] = ln[min:]
		} else {
			out[i] = strings.TrimLeft(ln, " \t")
		}
	}
	return out
}

func (p *Parser) expect(tt lexer.TokenType) error {
	if p.cur().Type != tt {
		return fmt.Errorf("line %d: expected %s, got %s %q", p.cur().Line, tt, p.cur().Type, p.cur().Value)
	}
	p.advance()
	return nil
}

func (p *Parser) expectOptional(tt lexer.TokenType) {
	if p.cur().Type == tt {
		p.advance()
	}
}
