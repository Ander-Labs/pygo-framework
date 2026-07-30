// Package ast defines the PyGo `.pgo` abstract syntax tree.
//
// The AST uses the visitor pattern from Fase 0 (per ARCHITECTURE.md §2 and
// DSL-SPEC.md §3) so that new generators can be added without touching the
// node definitions. Every node implements Node and dispatches through Accept.
package ast

// Node is the interface implemented by every AST node.
type Node interface {
	// Accept dispatches to the appropriate Visit* method on v and returns
	// whatever the visitor produces (or an error).
	Accept(v Visitor) (interface{}, error)
	// node is an unexported marker to keep the Node set closed to this package.
	node()
}

// EnumValue is a single enum member with optional value.
type EnumValue struct {
	Name  string // e.g. "active"
	Value string // e.g. "1" (empty means auto-generate from name)
}

// Visitor is implemented by generators (gen_go, gen_py) and any AST consumer.
type Visitor interface {
	VisitProgram(n *Program) (interface{}, error)
	VisitModel(n *ModelNode) (interface{}, error)
	VisitRoute(n *RouteNode) (interface{}, error)
	VisitHandler(n *HandlerNode) (interface{}, error)
	VisitFunction(n *FunctionNode) (interface{}, error)
	VisitField(n *FieldNode) (interface{}, error)
	VisitWorker(n *WorkerNode) (interface{}, error)
	VisitReport(n *ReportNode) (interface{}, error)
	VisitI18nConfig(n *I18nConfigNode) (interface{}, error)
	VisitEnum(n *EnumNode) (interface{}, error)
	VisitForeignKey(n *ForeignKeyNode) (interface{}, error)
	VisitCrud(n *CrudNode) (interface{}, error)
}

// TypeRef describes a resolved DSL type reference, e.g. Optional[String],
// Array[Int], UUID, Email.
type TypeRef struct {
	// Name is the base type name (String, Int, UUID, Optional, Array, ...).
	Name string
	// Optional is true when the field is nullable (`T?`, `T | None`, or
	// Optional[T]). When Optional wraps a type, Inner holds the wrapped type.
	Optional bool
	// Inner is the element/wrapped type for compound types (Array[T],
	// Optional[T], Map[K]V uses Inner for V and Key for K).
	Inner *TypeRef
	// Key is the key type for Map[K]V.
	Key *TypeRef
}

// String renders the type reference back to DSL-ish form (for debugging).
func (t *TypeRef) String() string {
	if t == nil {
		return "<nil>"
	}
	s := t.Name
	if t.Inner != nil {
		s += "[" + t.Inner.String() + "]"
	}
	if t.Optional {
		s += "?"
	}
	return s
}

// FieldNode is a typed field inside a model, or a parameter in a signature.
type FieldNode struct {
	Name    string
	Type    *TypeRef
	Default string // raw default expression, empty if none
	Line    int
}

func (n *FieldNode) node() {}
func (n *FieldNode) Accept(v Visitor) (interface{}, error) {
	return v.VisitField(n)
}

// ModelNode is a `model` declaration (Go struct + Python ORM class).
type ModelNode struct {
	Name   string
	Fields []*FieldNode
	Line   int
}

func (n *ModelNode) node() {}
func (n *ModelNode) Accept(v Visitor) (interface{}, error) {
	return v.VisitModel(n)
}

// RouteNode is a `route METHOD /path -> handler` declaration.
type RouteNode struct {
	Method  string // GET, POST, ...
	Path    string // /hello/:name
	Handler string // handler name it dispatches to
	Line    int
}

func (n *RouteNode) node() {}
func (n *RouteNode) Accept(v Visitor) (interface{}, error) {
	return v.VisitRoute(n)
}

// HandlerNode is a `handler` definition. Its body is emitted almost verbatim
// to Python (the `.pgo` body IS valid Python).
type HandlerNode struct {
	Name       string
	Params     []*FieldNode
	ReturnType *TypeRef
	// Body holds the raw source lines of the handler body, with the block's
	// leading indentation already stripped to a common base (so gen_py can
	// re-indent under `def`).
	Body []string
	Line int
}

func (n *HandlerNode) node() {}
func (n *HandlerNode) Accept(v Visitor) (interface{}, error) {
	return v.VisitHandler(n)
}

// FunctionNode is a `function` definition (Python-only utility).
type FunctionNode struct {
	Name       string
	Params     []*FieldNode
	ReturnType *TypeRef
	Body       []string
	Line       int
}

func (n *FunctionNode) node() {}
func (n *FunctionNode) Accept(v Visitor) (interface{}, error) {
	return v.VisitFunction(n)
}

// WorkerNode is a `worker` declaration: an async job handler that runs in the
// background queue, not blocking the HTTP request.
type WorkerNode struct {
	Name   string
	Params []*FieldNode
	Body   []string // raw Python body (executed via CallPython)
	Line   int
}

func (n *WorkerNode) node() {}
func (n *WorkerNode) Accept(v Visitor) (interface{}, error) {
	return v.VisitWorker(n)
}

// ReportNode is a `report` declaration: generates a CSV/PDF report from a model.
type ReportNode struct {
	Name       string
	Model      string   // model to report on
	Fields     []string // fields to include (empty = all)
	Format     string   // "csv" or "pdf" (v0.10: only csv)
	Path       string   // endpoint path, e.g. "/reports/customers.csv"
	Line       int
}

func (n *ReportNode) node() {}
func (n *ReportNode) Accept(v Visitor) (interface{}, error) {
	return v.VisitReport(n)
}

// I18nConfigNode is an `i18n` configuration block.
type I18nConfigNode struct {
	DefaultLocale string   // e.g. "en"
	Locales       []string // e.g. ["en", "es"]
	Line          int
}

func (n *I18nConfigNode) node() {}
func (n *I18nConfigNode) Accept(v Visitor) (interface{}, error) {
	return v.VisitI18nConfig(n)
}

// EnumNode is an `enum` declaration: a named set of values.
// e.g. enum Status: active inactive pending
// or: enum Status: active=1 inactive=2 pending=3
type EnumNode struct {
	Name   string
	Values []EnumValue
	Line   int
}

func (n *EnumNode) node() {}
func (n *EnumNode) Accept(v Visitor) (interface{}, error) {
	return v.VisitEnum(n)
}

// ForeignKeyNode is a `foreignKey` declaration: a named reference to another model.
// e.g. foreignKey User
type ForeignKeyNode struct {
	Name       string // field name
	Target     string // model name it references
	Line       int
}

func (n *ForeignKeyNode) node() {}
func (n *ForeignKeyNode) Accept(v Visitor) (interface{}, error) {
	return v.VisitForeignKey(n)
}

// CrudNode represents an auto-generated CRUD API for a model.
// Syntax: crud ModelName
type CrudNode struct {
	Line int    // line number for error messages
	Name string // model name to generate CRUD handlers for
}

func (n *CrudNode) node() {}
func (n *CrudNode) Accept(v Visitor) (interface{}, error) {
	return v.VisitCrud(n)
}

// Program is the root node holding all top-level declarations in order.
type Program struct {
	Models    []*ModelNode
	Cruds     []*CrudNode
	Routes    []*RouteNode
	Handlers  []*HandlerNode
	Functions []*FunctionNode
	Workers   []*WorkerNode
	Reports   []*ReportNode
	I18n      *I18nConfigNode
	Enums     []*EnumNode
	ForeignKeys []*ForeignKeyNode
	// Decls preserves original source order of top-level nodes.
	Decls []Node
}

func (n *Program) node() {}
func (n *Program) Accept(v Visitor) (interface{}, error) {
	return v.VisitProgram(n)
}
