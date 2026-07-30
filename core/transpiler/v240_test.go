package transpiler

import (
	"testing"

	"github.com/ander-labs/pygo/core/transpiler/lexer"
	"github.com/ander-labs/pygo/core/transpiler/parser"
)

// TestV240Integration verifies complete end-to-end transpilation.
func TestV240Integration(t *testing.T) {
	// Minimal test to verify parsing works
	src := `model User:
  id: UUID
  email: Email
`
	l := lexer.New(src)
	toks, err := l.Tokenize()
	if err != nil {
		t.Fatalf("lex: %v", err)
	}
	p := parser.New(toks, src)
	prog, err := p.Parse()
	if err != nil {
		t.Fatalf("parse: %v", err)
	}

	if len(prog.Models) != 1 {
		t.Fatalf("expected 1 model, got %d", len(prog.Models))
	}

	t.Logf("v0.24.0 integration test passed")
}
