# PyGo Framework

A Go + Python monolit architecture with DSL code generation.

**Licencia:** AGPL-3.0

## Características

- **DSL .pgo**: Lenguaje de dominio específico para definir modelos, handlers y rutas
- **Code Generation**: Genera código Go (structs, handlers, routes) y Python (modelos ORM)
- **Type Mappings**: Soporte para UUID, Email, DateTime, URL, Phone, Decimal, Optional, Array, Map
- **ForeignKey JOINs**: Generación automática de métodos de acceso para relaciones
- **Enum con valores**: Soporte para enums con valores numéricos o strings

## Instalación

```bash
# Requisitos: Go 1.22+, Python 3.10+
git clone https://github.com/Ander-Labs/pygo-framework
cd pygo-framework
go build ./...
```

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
go run ./cli/main.go transpile app.pgo
```

### 3. Ejecutar

```bash
go run ./cli/main.go serve
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

## Arquitectura

```
pygo-framework/
├── cli/           # CLI principal
├── core/
│   ├── transpiler/    # Parser y generadores
│   │   ├── lexer/     # Lexer del DSL
│   │   ├── parser/    # Parser del DSL
│   │   └── generators/  # gen_go.go, gen_py.go
│   └── runtime/       # Runtime Python
│       ├── db.py      # ORM SQLite
│       └── validators.py  # Validadores de tipos
├── examples/       # Ejemplos de aplicaciones
└── ROADMAP.md     # Roadmap de desarrollo
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

# Database commands (coming soon)
pygo db migrate
pygo db rollback

# Module management (coming soon)
pygo module install <name>
pygo module list
```

### Commands

| Command | Description |
|---------|-------------|
| `new <name>` | Create a new PyGo project |
| `dev` | Transpile and start dev server |
| `build` | Build for production |
| `gen [file]` | Transpile .pgo files |
| `test` | Run tests |
| `db migrate` | Run database migrations |
| `module install` | Install a module |
