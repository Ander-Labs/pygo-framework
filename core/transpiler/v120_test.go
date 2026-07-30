package transpiler

import (
	"strings"
	"testing"

	"github.com/ander-labs/pygo/core/transpiler/ast"
	"github.com/ander-labs/pygo/core/transpiler/generators"
	"github.com/ander-labs/pygo/core/transpiler/lexer"
	"github.com/ander-labs/pygo/core/transpiler/parser"
)

// TestV120ForeignKeyJOINs verifies ForeignKey[T] fields generate get_<field>() methods.
func TestV120ForeignKeyJOINs(t *testing.T) {
	src := `
model Order:
  user_id: Int
  ref: ForeignKey[User]
`

	l := lexer.New(src)
	tokens, err := l.Tokenize()
	if err != nil {
		t.Fatalf("lex: %v", err)
	}
	p := parser.New(tokens, src)
	prog, err := p.Parse()
	if err != nil {
		t.Fatalf("parse: %v", err)
	}

	// Verify Order model has ref field with ForeignKey type
	if len(prog.Models) != 1 {
		t.Fatalf("expected 1 model, got %d", len(prog.Models))
	}
	order := prog.Models[0]
	if order.Name != "Order" {
		t.Fatalf("model name: got %s", order.Name)
	}

	var refField *ast.FieldNode
	for _, f := range order.Fields {
		if f.Name == "ref" {
			refField = f
			break
		}
	}
	if refField == nil {
		t.Fatalf("missing ref field in Order")
	}
	if refField.Type.Name != "ForeignKey" {
		t.Fatalf("ref field type: got %s, want ForeignKey", refField.Type.Name)
	}
	if refField.Type.Inner == nil || refField.Type.Inner.Name != "User" {
		t.Fatalf("ref field inner type: got %v, want User", refField.Type.Inner)
	}

	goOut, err := generators.GenerateGo(prog, "generated")
	if err != nil {
		t.Fatalf("go gen: %v", err)
	}
	pyOut, err := generators.GeneratePy(prog)
	if err != nil {
		t.Fatalf("py gen: %v", err)
	}

	// ForeignKey JOIN: get_ref() method in Python
	if !strings.Contains(pyOut, "def get_ref(self) -> User:") {
		t.Fatalf("py missing ForeignKey get method:\n%s", pyOut)
	}

	// ForeignKey JOIN: GetRef() method in Go
	if !strings.Contains(goOut, "func (m *Order) GetRef() *User") {
		t.Fatalf("go missing ForeignKey method:\n%s", goOut)
	}

	t.Logf("v0.12.0 ForeignKey JOINs OK")
}