# PyGo Framework

An ultralight Go + Python full-stack framework with DSL code generation and HTMX UI.

**Licencia:** AGPL-3.0
**Documentación:** https://pygo-docs.vercel.app/

## Características

- **`.pgo` DSL**: Lenguaje isomórfico a Python con code generation 1:1
- **Code Generation**: Genera código Go (handlers, routes) y Python (modelos ORM)
- **Type Mappings**: Soporte para UUID, Email, DateTime, URL, Phone, Decimal, Optional, Array, Map
- **ForeignKey & JOINs**: Generación automática de métodos de acceso para relaciones
- **Enum con valores**: Soporte para enums con valores numéricos o strings
- **MessagePack + UDS**: Go↔Python interoperability via Unix Domain Sockets
- **HTMX First**: UI server-driven, sin frameworks JavaScript cliente
- **Ultra ligero**: Go `net/http` + Python `stdlib` only — cero frameworks pesados

## Instalación

```bash
# Opción 1: Universal installer
curl -fsSL https://raw.githubusercontent.com/PyGo-Labs/pygo-framework/main/install.sh | bash

# Opción 2: Desde el código fuente
git clone https://github.com/PyGo-Labs/pygo-framework.git
cd pygo-framework
go build -o pygo ./cmd/pygo
```

## Comandos CLI

| Command | Description |
|---------|-------------|
| `pygo new <name>` | Create a new PyGo project |
| `pygo dev` | Transpile and start dev server |
| `pygo build --embed-python` | Build for production |
| `pygo gen [file]` | Generate gen_py.py and gen_go.go |
| `pygo test` | Run tests |

## Uso rápido

### 1. Crear un archivo .pgo

```pgo
# Definir enums
enum Status:
  active
  inactive
  pending

# Definir modelo
model User:
  id: UUID
  email: Email
  name: String
  status: Status
  created: DateTime
  tags: Array[String]

# Definir handler
handler hello:
  greet(name: String) -> String:
    return f"Hello, {name}!"

# Definir ruta
route GET /hello/:name -> hello
```

### 2. Generar código

```bash
pygo gen web/app.pgo
```

### 3. Ejecutar

```bash
pygo dev
```

## DSL Reference

### Modelos

```pgo
model ModelName:
  campo1: Tipo
  campo2: Tipo?
  campo3: Array[Tipo]
  campo4: Map[String]Tipo
```

### Tipos soportados

| Tipo DSL | Go | Python |
|----------|-----|--------|
| String | string | str |
| Int | int | int |
| Float | float64 | float |
| Bool | bool | bool |
| UUID | string | str |
| Email | string | str |
| DateTime | time.Time | datetime |
| URL | string | str |
| Phone | string | str |
| Decimal | string | Decimal |
| Status | string | str |
| Array[T] | []T | list[T] |
| Map[K]V | map[K]V | dict[K, V] |
| Optional | *T | T \| None |
| Enum | string/int | str/int enum |

### Enums

```pgo
# Enum con valores string (por defecto)
enum Status:
  active
  inactive

# Enum con valores numéricos
enum Priority:
  low=1
  medium=2
  high=3
```

### ForeignKey y JOINs

```pgo
model Order:
  id: UUID
  user_id: UUID
  user: ForeignKey[User]  # Genera get_user() método

foreignKey user_id -> User  # Documentación de relación
```

### Handlers

```pgo
handler createUser:
  create(name: String, email: Email) -> User:
    # Código Python
    user = User(name=name, email=email)
    user.save()
    return user
```

### Rutas

```pgo
route GET /users/:id -> getUser
route POST /users -> createUser
route GET /users -> listUsers
```

### Workers

```pgo
worker emailSender:
  send_email(to: String, subject: String, body: String):
    # Código Python para enviar email
    send_email(to, subject, body)
```

## Ejemplos

### Hello World

```bash
cd examples/hello-world
go run ../cli/main.go serve
```

### Blog completo (v0.19.0)

```bash
cd examples/blog
go run ../cli/main.go serve
```

## Ejemplos

### Hello World

```bash
cd examples/hello-world
pygo gen
pygo dev
```

### Blog completo

```bash
cd examples/blog
pygo gen
pygo dev
```

## Arquitectura

```
pygo/
├── cmd/              # CLI entry point
├── cli/              # CLI commands (new, dev, gen, build, test)
├── core/
│   ├── transpiler/   # Parser, lexer, AST, generators
│   │   ├── lexer/
│   │   ├── parser/
│   │   ├── ast/
│   │   └── generators/  # gen_go.go, gen_py.go
│   └── runtime/      # Python runtime (db, validators, jobs, websockets)
├── examples/         # Example applications
├── templates/        # Project scaffolding templates
├── scripts/          # Helper scripts
└── install.sh        # Python dependency installer
```

## Roadmap

Ver [ROADMAP.md](ROADMAP.md) para el plan de desarrollo.

## Contribuir

1. Fork del repositorio
2. Crear rama feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit con mensaje claro: `git commit -m "feat: descripción"`
4. Push a tu fork: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

## Créditos

Desarrollado por Anderson Ruiz (Ander-Labs).

## CLI

The PyGo CLI provides commands for project management:

```sh
# Create a new project
pygo new my-app

# Development mode (transpile and serve)
pygo dev

# Build for production
pygo build --embed-python

# Transpile .pgo files
pygo gen web/app.pgo

# Run tests
pygo test -v

# Environment health check
pygo doctor
```

### Commands

| Command | Description |
|---------|-------------|
| `pygo new <name>` | Create a new PyGo project |
| `pygo dev` | Transpile and start dev server |
| `pygo build --embed-python` | Build for production |
| `pygo gen [file]` | Generate gen_py.py and gen_go.go |
| `pygo test` | Run tests |
| `pygo doctor` | Check environment |
