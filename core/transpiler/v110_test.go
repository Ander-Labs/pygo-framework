package transpiler

import (
	"strings"
	"testing"

	"github.com/ander-labs/pygo/core/transpiler/generators"
	"github.com/ander-labs/pygo/core/transpiler/lexer"
	"github.com/ander-labs/pygo/core/transpiler/parser"
)

func TestV110DSLTypes(t *testing.T) {
	src := `
model Product:
  name: String
  price: Float
  tags: Array[String]
  metadata: Map[String]String

enum Status:
  active
  inactive
  pending

foreignKey user_id -> User

model Order:
  user: String
  status: Status
  ref: ForeignKey[User]
  items: Array[String]
  extras: Map[String]String
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

	if len(prog.Enums) != 1 {
		t.Fatalf("expected 1 enum, got %d", len(prog.Enums))
	}
	if prog.Enums[0].Name != "Status" {
		t.Fatalf("enum name: got %s", prog.Enums[0].Name)
	}
	if len(prog.Enums[0].Values) != 3 {
		t.Fatalf("enum values: got %v", prog.Enums[0].Values)
	}

	if len(prog.ForeignKeys) != 1 {
		t.Fatalf("expected 1 foreignKey, got %d", len(prog.ForeignKeys))
	}
	if prog.ForeignKeys[0].Target != "User" {
		t.Fatalf("foreignKey target: got %s", prog.ForeignKeys[0].Target)
	}

	goOut, err := generators.GenerateGo(prog, "generated")
	if err != nil {
		t.Fatalf("go gen: %v", err)
	}
	pyOut, err := generators.GeneratePy(prog)
	if err != nil {
		t.Fatalf("py gen: %v", err)
	}

	if !strings.Contains(goOut, "type Status string") {
		t.Fatalf("go missing enum type:\n%s", goOut)
	}
	if !strings.Contains(pyOut, "class Status(str, enum.Enum)") {
		t.Fatalf("py missing enum class:\n%s", pyOut)
	}
	if !strings.Contains(pyOut, "extras: dict[str, str]") {
			t.Fatalf("py missing Map metadata:\n%s", pyOut)
		}

		// ForeignKey JOINs - verify field type is string (placeholder for FK id)
			if !strings.Contains(goOut, "Ref string") {
				t.Fatalf("go missing ForeignKey field:\n%s", goOut)
			}
			if !strings.Contains(pyOut, "ref: str") {
				t.Fatalf("py missing ForeignKey field:\n%s", pyOut)
			}

			t.Logf("v0.11.0 DSL types OK")
}
