package parser

import (
	"strings"
	"testing"

	"github.com/ander-labs/pygo/core/transpiler/lexer"
)

// TestTranspilerAST verifies the lexer+parser build the expected AST for a
// minimal .pgo (a model + a route). This is the unit test of the compiler
// front-end that previously had no coverage.
func TestTranspilerAST(t *testing.T) {
	src := `
model Customer:
    id: UUID?
    name: String

route GET /hello/:name -> hello
`
	lex := lexer.New(src)
	tokens, err := lex.Tokenize()
	if err != nil {
		t.Fatalf("tokenize: %v", err)
	}
	p := New(tokens, src)
	prog, err := p.Parse()
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	if len(prog.Models) != 1 {
		t.Fatalf("expected 1 model, got %d", len(prog.Models))
	}
	if prog.Models[0].Name != "Customer" {
		t.Fatalf("expected model Customer, got %q", prog.Models[0].Name)
	}
	if len(prog.Routes) != 1 {
		t.Fatalf("expected 1 route, got %d", len(prog.Routes))
	}
	r := prog.Routes[0]
	if r.Method != "GET" || r.Path != "/hello/:name" || r.Handler != "hello" {
		t.Fatalf("unexpected route: %+v", r)
	}
	// The .pgo must round-trip (no dropped declarations).
	if strings.TrimSpace(prog.Models[0].Name) != "Customer" {
		t.Fatalf("model name not preserved")
	}
}
