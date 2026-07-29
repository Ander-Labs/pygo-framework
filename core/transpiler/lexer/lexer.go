// Package lexer tokenizes PyGo `.pgo` source into a flat token stream.
//
// The `.pgo` DSL is isomorphic to Python: significant indentation plus
// type annotations with `:`. The lexer therefore emits INDENT / DEDENT /
// NEWLINE tokens (Python-style) so the parser can reconstruct blocks.
package lexer

import (
	"strings"
	"unicode"
)

// TokenType enumerates every kind of token the lexer can produce.
type TokenType int

const (
	// Structural
	TokenEOF TokenType = iota
	TokenNewline
	TokenIndent
	TokenDedent

	// Literals / identifiers
	TokenIdent
	TokenNumber
	TokenString

	// Keywords
	TokenModel
	TokenRoute
	TokenHandler
	TokenFunction
	TokenWorker
	TokenReport
	TokenI18n
	TokenEnum
	TokenForeignKey

	// Type keywords
	TokenType_ // a recognized DSL type name (String, Int, ...)

	// Symbols
	TokenColon     // :
	TokenQuestion  // ?
	TokenArrow     // ->
	TokenAssign    // =
	TokenLBrace    // {
	TokenRBrace    // }
	TokenLParen    // (
	TokenRParen    // )
	TokenComma     // ,
	TokenLBracket  // [
	TokenRBracket  // ]
	TokenPipe      // |  (used for `T | None`)
	TokenSlash     // /  (route paths)

	// Anything else (route path fragments, operators inside bodies, etc.)
	TokenRaw
)

func (t TokenType) String() string {
	switch t {
	case TokenEOF:
		return "EOF"
	case TokenNewline:
		return "NEWLINE"
	case TokenIndent:
		return "INDENT"
	case TokenDedent:
		return "DEDENT"
	case TokenIdent:
		return "IDENT"
	case TokenNumber:
		return "NUMBER"
	case TokenString:
		return "STRING"
	case TokenModel:
		return "MODEL"
	case TokenRoute:
		return "ROUTE"
	case TokenHandler:
		return "HANDLER"
	case TokenFunction:
		return "FUNCTION"
	case TokenWorker:
		return "WORKER"
	case TokenReport:
		return "REPORT"
	case TokenI18n:
		return "I18N"
	case TokenEnum:
		return "ENUM"
	case TokenForeignKey:
		return "FOREIGN_KEY"
	case TokenType_:
		return "TYPE"
	case TokenColon:
		return "COLON"
	case TokenQuestion:
		return "QUESTION"
	case TokenArrow:
		return "ARROW"
	case TokenAssign:
		return "ASSIGN"
	case TokenLBrace:
		return "LBRACE"
	case TokenRBrace:
		return "RBRACE"
	case TokenLParen:
		return "LPAREN"
	case TokenRParen:
		return "RPAREN"
	case TokenComma:
		return "COMMA"
	case TokenLBracket:
		return "LBRACKET"
	case TokenRBracket:
		return "RBRACKET"
	case TokenPipe:
		return "PIPE"
	case TokenSlash:
		return "SLASH"
	case TokenRaw:
		return "RAW"
	default:
		return "UNKNOWN"
	}
}

// Token is a single lexical unit with position info.
type Token struct {
	Type   TokenType
	Value  string
	Line   int
	Column int
	// Indent is the indentation level (number of INDENTs deep) that was in
	// effect when this token was produced. Useful for the parser to capture
	// verbatim handler bodies.
	Indent int
}

// keywords maps reserved words to their token types.
var keywords = map[string]TokenType{
	"model":      TokenModel,
	"route":      TokenRoute,
	"handler":    TokenHandler,
	"function":   TokenFunction,
	"worker":     TokenWorker,
	"report":     TokenReport,
	"i18n":       TokenI18n,
	"enum":       TokenEnum,
	"foreignKey": TokenForeignKey,
}

// dslTypes is the set of recognized DSL type names (Fase 0).
var dslTypes = map[string]bool{
	"String":     true,
	"Int":        true,
	"Float":      true,
	"Bool":       true,
	"DateTime":   true,
	"UUID":       true,
	"Decimal":    true,
	"Array":      true,
	"Map":        true,
	"Optional":   true,
	"ForeignKey": true,
	"Enum":       true,
	"Email":      true,
	"URL":        true,
	"Phone":      true,
}

// IsDSLType reports whether name is a recognized DSL type keyword.
func IsDSLType(name string) bool { return dslTypes[name] }

// Lexer holds tokenizer state.
type Lexer struct {
	lines       []string
	indentStack []int
	tokens      []Token
}

// New creates a lexer for the given source text.
func New(src string) *Lexer {
	// Normalize newlines, split into physical lines.
	src = strings.ReplaceAll(src, "\r\n", "\n")
	src = strings.ReplaceAll(src, "\r", "\n")
	return &Lexer{
		lines:       strings.Split(src, "\n"),
		indentStack: []int{0},
	}
}

// Tokenize runs the lexer and returns the full token stream ending in EOF.
func (l *Lexer) Tokenize() ([]Token, error) {
	for i, raw := range l.lines {
		lineNo := i + 1

		// Compute indentation (spaces; tabs count as 1 for simplicity).
		indent := 0
		j := 0
		for j < len(raw) && (raw[j] == ' ' || raw[j] == '\t') {
			indent++
			j++
		}
		content := raw[j:]
		trimmed := strings.TrimRight(content, " \t")

		// Blank line or full-line comment: skip (no NEWLINE emitted so blank
		// lines inside a block don't confuse indentation).
		if trimmed == "" || strings.HasPrefix(strings.TrimSpace(trimmed), "#") {
			continue
		}

		// Emit INDENT / DEDENT tokens based on indentation change.
		l.handleIndent(indent, lineNo)

		// Tokenize the line content.
		if err := l.lexLine(trimmed, lineNo, j); err != nil {
			return nil, err
		}

		l.emit(Token{Type: TokenNewline, Value: "\\n", Line: lineNo})
	}

	// Close any open indentation blocks at EOF.
	for len(l.indentStack) > 1 {
		l.indentStack = l.indentStack[:len(l.indentStack)-1]
		l.emit(Token{Type: TokenDedent, Line: len(l.lines)})
	}
	l.emit(Token{Type: TokenEOF, Line: len(l.lines)})
	return l.tokens, nil
}

func (l *Lexer) currentIndentLevel() int {
	return len(l.indentStack) - 1
}

func (l *Lexer) handleIndent(indent, lineNo int) {
	top := l.indentStack[len(l.indentStack)-1]
	if indent > top {
		l.indentStack = append(l.indentStack, indent)
		l.emit(Token{Type: TokenIndent, Line: lineNo})
		return
	}
	for indent < l.indentStack[len(l.indentStack)-1] {
		l.indentStack = l.indentStack[:len(l.indentStack)-1]
		l.emit(Token{Type: TokenDedent, Line: lineNo})
	}
}

func (l *Lexer) lexLine(content string, lineNo, colBase int) error {
	i := 0
	n := len(content)
	for i < n {
		c := content[i]
		col := colBase + i + 1

		switch {
		case c == ' ' || c == '\t':
			i++
			continue
		case c == '#':
			// Rest of line is a comment.
			return nil
		case c == '"' || c == '\'':
			s, adv := lexString(content[i:], c)
			l.emit(Token{Type: TokenString, Value: s, Line: lineNo, Column: col, Indent: l.currentIndentLevel()})
			i += adv
			continue
		case c == '-' && i+1 < n && content[i+1] == '>':
			l.emit(Token{Type: TokenArrow, Value: "->", Line: lineNo, Column: col, Indent: l.currentIndentLevel()})
			i += 2
			continue
		}

		if isIdentStart(rune(c)) {
			start := i
			for i < n && isIdentPart(rune(content[i])) {
				i++
			}
			word := content[start:i]
			tt := TokenIdent
			if kw, ok := keywords[word]; ok {
				tt = kw
			} else if dslTypes[word] {
				tt = TokenType_
			}
			l.emit(Token{Type: tt, Value: word, Line: lineNo, Column: col, Indent: l.currentIndentLevel()})
			continue
		}

		if unicode.IsDigit(rune(c)) {
			start := i
			for i < n && (unicode.IsDigit(rune(content[i])) || content[i] == '.') {
				i++
			}
			l.emit(Token{Type: TokenNumber, Value: content[start:i], Line: lineNo, Column: col, Indent: l.currentIndentLevel()})
			continue
		}

		// Single-char symbols.
		var tt TokenType
		switch c {
		case ':':
			tt = TokenColon
		case '?':
			tt = TokenQuestion
		case '=':
			tt = TokenAssign
		case '{':
			tt = TokenLBrace
		case '}':
			tt = TokenRBrace
		case '(':
			tt = TokenLParen
		case ')':
			tt = TokenRParen
		case ',':
			tt = TokenComma
		case '[':
			tt = TokenLBracket
		case ']':
			tt = TokenRBracket
		case '|':
			tt = TokenPipe
		case '/':
			tt = TokenSlash
		default:
			tt = TokenRaw
		}
		l.emit(Token{Type: tt, Value: string(c), Line: lineNo, Column: col, Indent: l.currentIndentLevel()})
		i++
	}
	return nil
}

func lexString(s string, quote byte) (string, int) {
	// s starts with the quote char. Return the raw literal including quotes
	// and the number of bytes consumed.
	i := 1
	for i < len(s) {
		if s[i] == '\\' && i+1 < len(s) {
			i += 2
			continue
		}
		if s[i] == quote {
			i++
			break
		}
		i++
	}
	return s[:i], i
}

func isIdentStart(r rune) bool {
	return unicode.IsLetter(r) || r == '_'
}

func isIdentPart(r rune) bool {
	return unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_'
}

func (l *Lexer) emit(t Token) {
	l.tokens = append(l.tokens, t)
}
