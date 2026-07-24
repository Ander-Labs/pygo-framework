# PyGo DSL `.pgo` — Especificación (Fase 0, mínima)

## Principio rector: isomorfismo con el lenguaje base

El `.pgo` se escribe con **sintaxis idéntica a Python** (indentación, tipos
anotados con `:`, cuerpos indentados). Esto hace que:

- **`gen_py` sea trivial**: el AST se vuelca a Python con transformación
  mínima (casi un pretty-print + resolución de tipos). No hay que "traducir"
  una sintaxis rara a Python.
- **`gen_go` sea directo**: el AST (no el texto) genera structs/routes Go.
  Como el fuente ya es regular y tipado, el mapping a Go es mecánico.

> La rigidez de estructura y nomenclatura NO es dogma: es lo que hace la
> transpilación barata y el código alineable para sub-agentes.

Regla de oro: **todo se indenta estilo Python**. El transpiler parsea a AST y
genera ambos targets desde el AST, no desde el texto.

---

## 1. Tipos

Primitivos:
`String, Int, Float, Bool, DateTime, UUID, Decimal`

Compuestos (estilo Python typing):
`Array[T]`, `Map[K]V`, `Optional[T]` (azúcar: `T?` o `T | None`)

Especiales:
`ForeignKey[T]`, `Enum { ... }`, `Email`, `URL`, `Phone`

No generics, no union types en Fase 0.

Mapeo a lenguaje base:
- Python: `String` → `str`, `Int` → `int`, `Optional[String]` → `str | None`.
- Go: `String` → `string`, `Optional[String]` → `*string`.

---

## 2. Nodos soportados en Fase 0 (todos indentados)

### 2.1 `model` (declarativo)

```pgo
model Customer:
    id: UUID?
    name: String
    email: Email
    active: Bool = True
    created_at: DateTime?
```

- Python: clase ORM (campos tipados, defaults respetados).
- Go: `struct Customer { ... }` con tags json/msgpack.

### 2.2 `route` + `handler` (lógica → Python)

```pgo
route GET /customers/:id -> get_customer

handler get_customer(id: UUID) -> Customer:
    cust = Customer.find(id)
    if cust is None:
        return error ValidationError("not found", field="id")
    return cust
```

- `route` registra en el router Go (HTMX server).
- `handler` corre en **Python** (vía socket MessagePack). Su cuerpo es Python
  válido → `gen_py` lo emite casi tal cual.
- `return` se serializa y vuelve a Go → respuesta HTTP/HTMX.

### 2.3 `function` (utilidad)

```pgo
function full_name(c: Customer) -> String:
    return c.name
```

Python: función. Go: no genera (solo existe en lado Python).

### 2.4 `worker` (background job, opcional Fase 0)

```pgo
worker send_welcome(email: Email):
    # lógica Python
```

---

## 3. Semántica de generación

| Nodo | Genera en Go | Genera en Python |
|---|---|---|
| `model` | `struct` + (de)serialización MSGP | clase ORM tipada |
| `route` | registro en router + stub handler | — |
| `handler` | stub que delega por socket | función Python (casi 1:1) |
| `function` | — | función Python |
| `worker` | registro en queue | suscriptor Python |

Transpiler Fase 0:
1. Lexer → tokens.
2. Parser → AST (`ModelNode`, `RouteNode`, `HandlerNode`, `FunctionNode`).
3. Validación semántica (tipos, refs, unicidad de rutas).
4. Generadores: `gen_go.go` (handlers/rutas) + `gen_py.py` (modelos/lógica).

El AST usa **visitor pattern** desde Fase 0 (extensibilidad futura, punto 20).

---

## 4. Ejemplo end-to-end (PoC)

`hello.pgo`:
```pgo
model Greeting:
    id: UUID?
    name: String

route GET /hello/:name -> hello

handler hello(name: String) -> Greeting:
    return Greeting(name=name)
```

Flujo:
1. `pygo dev` → genera `gen_go.go` + `gen_py.py`.
2. Supervisor Go escucha socket Unix, lanza Python (registra `hello`).
3. HTMX pide `/hello/Anders` → Go rutrea → delega a Python por socket →
   Python devuelve `Greeting{name:"Anders"}` (MessagePack) → Go renderiza
   fragmento HTML → browser.

---

## 5. Versionado

`pygo.toml` declara `dsl_version = "0.0.1"`. MAJOR = incompatible.
Migraciones automáticas del DSL al subir versión.

---

## 6. Fuera de Fase 0 (crece después)

- Cuerpos de handler con sintaxis Python completa (imports, clases).
- Macros / metaprogramación.
- Generics.
- Plugins de parser (visitor + hooks AST).
