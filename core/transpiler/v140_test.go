package transpiler

import (
	"strings"
	"testing"

	"github.com/ander-labs/pygo/core/transpiler/ast"
	"github.com/ander-labs/pygo/core/transpiler/generators"
	"github.com/ander-labs/pygo/core/transpiler/lexer"
	"github.com/ander-labs/pygo/core/transpiler/parser"
)

// TestV140OptionalDecimal verifies Optional types and Decimal mapping.
func TestV140OptionalDecimal(t *testing.T) {
	src := `
model Product:
  name: String
  description: String?
  price: Decimal
  discount: Decimal?
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

	// Verify model has correct fields
	if len(prog.Models) != 1 {
		t.Fatalf("expected 1 model, got %d", len(prog.Models))
	}
	product := prog.Models[0]
	if product.Name != "Product" {
		t.Fatalf("model name: got %s", product.Name)
	}

	fieldsByName := make(map[string]*ast.FieldNode)
	for _, f := range product.Fields {
		fieldsByName[f.Name] = f
	}

	// Verify Optional fields
	desc := fieldsByName["description"]
	if desc == nil {
		t.Fatal("missing description field")
	}
	if !desc.Type.Optional {
		t.Fatal("description should be Optional")
	}

	discount := fieldsByName["discount"]
	if discount == nil {
		t.Fatal("missing discount field")
	}
	if !discount.Type.Optional {
		t.Fatal("discount should be Optional")
	}

	// Verify Decimal fields
	price := fieldsByName["price"]
	if price == nil {
		t.Fatal("missing price field")
	}
	if price.Type.Name != "Decimal" {
		t.Fatalf("price field type: got %s", price.Type.Name)
	}

	goOut, err := generators.GenerateGo(prog, "generated")
	if err != nil {
		t.Fatalf("go gen: %v", err)
	}
	pyOut, err := generators.GeneratePy(prog)
	if err != nil {
		t.Fatalf("py gen: %v", err)
	}

	// Go: Optional -> pointer, Decimal -> string
	if !strings.Contains(goOut, "Description *string") {
		t.Fatalf("go missing Optional String field:\n%s", goOut)
	}
	if !strings.Contains(goOut, "Discount *string") {
		t.Fatalf("go missing Optional Decimal field:\n%s", goOut)
	}
	if !strings.Contains(goOut, "Price string") {
		t.Fatalf("go missing Decimal field:\n%s", goOut)
	}

	// Python: Optional -> T | None, Decimal -> Decimal
	if !strings.Contains(pyOut, "description: str | None") {
		t.Fatalf("py missing Optional String field:\n%s", pyOut)
	}
	if !strings.Contains(pyOut, "discount: Decimal | None") {
		t.Fatalf("py missing Optional Decimal field:\n%s", pyOut)
	}
	if !strings.Contains(pyOut, "price: Decimal") {
		t.Fatalf("py missing Decimal field:\n%s", pyOut)
	}

	t.Logf("v0.14.0 Optional/Decimal OK")
}