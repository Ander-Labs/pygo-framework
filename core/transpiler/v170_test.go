package transpiler

import (
	"strings"
	"testing"

	"github.com/ander-labs/pygo/core/transpiler/generators"
	"github.com/ander-labs/pygo/core/transpiler/lexer"
	"github.com/ander-labs/pygo/core/transpiler/parser"
)

// TestV170NestedArray verifies Array[Array[T]] type mapping.
func TestV170NestedArray(t *testing.T) {
	src := `
model Matrix:
  data: Array[Array[String]]
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

	goOut, err := generators.GenerateGo(prog, "generated")
	if err != nil {
		t.Fatalf("go gen: %v", err)
	}
	pyOut, err := generators.GeneratePy(prog)
	if err != nil {
		t.Fatalf("py gen: %v", err)
	}

	// Go: Array[Array[String]] -> [][]string
	if !strings.Contains(goOut, "Data [][]string") {
		t.Fatalf("go missing Array[Array[T]]:\n%s", goOut)
	}

	// Python: Array[Array[String]] -> list[list[str]]
	if !strings.Contains(pyOut, "data: list[list[str]]") {
		t.Fatalf("py missing Array[Array[T]]:\n%s", pyOut)
	}

	t.Logf("v0.17.0 Array[Array[T]] OK")
}

// TestV170MapArray verifies Map[K]Array[V] type mapping.
func TestV170MapArray(t *testing.T) {
	src := `
model Groups:
  tags: Map[String]Array[Int]
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

	goOut, err := generators.GenerateGo(prog, "generated")
	if err != nil {
		t.Fatalf("go gen: %v", err)
	}
	pyOut, err := generators.GeneratePy(prog)
	if err != nil {
		t.Fatalf("py gen: %v", err)
	}

	// Go: Map[String]Array[Int] -> map[string][]int
	if !strings.Contains(goOut, "Tags map[string][]int") {
		t.Fatalf("go missing Map[K]Array[V]:\n%s", goOut)
	}

	// Python: Map[String]Array[Int] -> dict[str, list[int]]
	if !strings.Contains(pyOut, "tags: dict[str, list[int]]") {
		t.Fatalf("py missing Map[K]Array[V]:\n%s", pyOut)
	}

	t.Logf("v0.17.0 Map[K]Array[V] OK")
}