# PyGo DSL `.pgo` — Especificación (Fase 0, mínima)

Gramática mínima para Fase 0. El objetivo es validar el transpiler
(`.pgo` → Go handler + Python modelo) y el interop, **no** cubrir toda la
superficie de Python/Go. La gramática crece por versión (SemVer estricto).

Principio: `.pgo` = lógica. `.yaml` = declaraciones. `.html` = vistas.

---

## 1. Tipos

Primitivos:
`String, Int, Float, Bool, DateTime, UUID, Decimal`

Compuestos:
`Array[T]`, `Map[K]V`, `Optional[T]` (azúcar: `T?`)

Especiales:
`ForeignKey[T]`, `Enum { ... }`, `Email`, `URL`, `Phone`

No generics, no union types.

---

## 2. Nodos soportados en Fase 0

### 2.1 `model` (declarativo, puede ir en `.yaml` o `.pgo`)

```pgo
model Customer {
    id: UUID?          # autogenerado si es ?
    name: String
    email: Email
    active: Bool = true
    created_at: DateTime?
}
```

Genera (Python): clase ORM con los campos.
Genera (Go): struct para (de)serialización en el handler.

### 2.2 `route` + `handler`

```pgo
route GET /customers/:id -> get_customer

handler get_customer(id: UUID) -> Customer {
    cust = Customer.find(id)
    if cust is None {
        return error ValidationError("not found", field="id")
    }
    return cust
}
```

- `route` registra la ruta en el router Go (HTMX server).
- `handler` es la lógica que corre en **Python** (vía socket MessagePack).
- El `return` de un handler se serializa y vuelve a Go → respuesta HTTP/HTMX.

### 2.3 `function` (utilidad reutilizable)

```pgo
function full_name(c: Customer) -> String {
    return c.name
}
```

### 2.4 `worker` (background job, Fase 0 opcional)

```pgo
worker send_welcome(email: Email) {
    # lógica en Python
}
```

---

## 3. Semántica de generación

| Nodo | Genera en Go | Genera en Python |
|---|---|---|
| `model` | struct + (de)serialización MSGP | clase ORM (SQLAlchemy-style) |
| `route` | registro en router + stub handler | — |
| `handler` | stub que delega por socket | función ejecutable |
| `function` | — | función |
| `worker` | registro en queue | suscriptor |

El transpiler de Fase 0:
1. Lexer → tokens.
2. Parser → AST (`ModelNode`, `RouteNode`, `HandlerNode`, `FunctionNode`).
3. Validación semántica (tipos, referencias, unicidad de rutas).
4. Generadores: `gen_go.go` (handlers/rutas) + `gen_py.py` (modelos/lógica).

---

## 4. Ejemplo end-to-end (PoC)

`hello.pgo`:
```pgo
model Greeting {
    id: UUID?
    name: String
}

route GET /hello/:name -> hello

handler hello(name: String) -> Greeting {
    return Greeting(name: name)
}
```

Flujo:
1. `pygo dev` → transpiler genera `gen_go.go` + `gen_py.py`.
2. Supervisor Go arranca, escucha socket Unix, lanza Python (registra `hello`).
3. HTMX pide `/hello/Anders` → Go ruthea → delega a Python por socket →
   Python devuelve `Greeting{name:"Anders"}` (MessagePack) → Go renderiza
   fragmento HTML → browser.

---

## 5. Versionado

`pygo.toml` declara `dsl_version = "0.0.1"`. Cambios incompatibles → MAJOR.
Migraciones automáticas del DSL se generan al subir versión.

---

## 6. Fuera de Fase 0 (crece después)

- Funciones arbitrarias de Python completas.
- Macros / metaprogramación.
- Tipos genéricos.
- Plugins de parser (visitor pattern + hooks AST, punto 20 del doc).
