# PyGo Framework — Roadmap de Fases (v0.N.0 → v1.0.0)

Contrato de versionado: **cada fase = un `v0.N.0`**, con exactamente
**un objetivo verificable** (un test que pase, no "avances"). El número de
fases no importa: `v0.37.0` antes de `v1.0.0` es señal de rigor, no de demora.

`v1.0.0` se alcanza cuando el **monolito modular descapotable** sirve una app
CRUD real (HTMX + ORM + auth + un módulo) de punta a punta y el **DSL `.pgo`
está estable** (SemVer, migraciones automáticas garantizadas).

SemVer: `v0.N.0` = fase N (puede romper). `v1.0.0` = API congelada, DSL
estable, migraciones automáticas. Cada fase incrementa N en 1.

---

## v0.1.0 — PoC integrado (Fase 1)  ← ESTADO: COMPLETADO

Objetivo verificable: `TestPoCHelloWorld` pasa — Go supervisor arranca Python
por UDS+MessagePack, `CallPython("hello",{name})` devuelve `Greeting{name}`.

Entregado:
- Transpiler `.pgo` → `gen_go.go` + `gen_py.py` (isomórfico a Python, AST visitor).
- Runtime: socket UDS+MessagePack, `runtime.CallPython`, hot-reload fsnotify,
  pyclient con error cross-language unificado.
- CLI: `pygo new` / `pygo dev` / `pygo build --embed-python` (este último TODO).
- Test de integración end-to-end (PASS).
- **Pendiente de cierre v0.1.0:** revisión con skills de ECC
  (go-reviewer / python-reviewer / security-reviewer) como equipo de QA.

---

## v0.2.0 — gen_go real + router HTTP + HTMX (Fase 2)

Objetivo verificable: `pygo dev` levanta transpile + supervisor + server HTTP
que ruttea `/customers/:id`, delega a Python y renderiza fragmento `.html` HTMX,
sin servidor a medida.

- `gen_go.go` generado es Go compilable: registra rutas en router + delega vía
  `runtime.CallPython` (hoy es stub).
- Router HTTP mínimo (gin ya en go.mod) que mapea `route` del `.pgo`.
- Render de vistas `.html` servidas a HTMX.

---

## v0.3.0 — ORM básico (Fase 3)

Objetivo verificable: `model Customer` crea tabla SQLite y `Customer.find(id)`
/ `Customer.create(...)` funcionan de verdad.

- SQLAlchemy/SQLModel contra SQLite (dev) → PostgreSQL (prod).
- Migraciones DSL→SQL (auto-gen + SQL manual edge).
- `find`/`create`/`update`/`delete` reales en el `gen_py.py`.

---

## v0.4.0 — Auth (Fase 4)

Objetivo verificable: login con sesión + JWT protege rutas marcadas.

- Sessions + JWT middleware.
- `auth` module básico.

---

## v0.5.0 — Build empaquetado (Fase 5)  ← ESTADO: COMPLETADO (spec + CLI)

Objetivo verificable: `pygo build --embed-python` genera `pyoxidizer.bzl` válido
que empaqueta CPython + `core/` + `app_poc.py` en un binario. Si `pyoxidizer`
está en PATH, build real; si no, deja el spec y avisa (sin tirar toolchain).

Entregado:
- `cli/build.go`: `pygo build --embed-python` escribe el spec y corre
  `pyoxidizer build --release` cuando está disponible.
- `core/runtime/pyclient`: `main()` arranca el serve loop (lo invoca el spec).
- Test `TestV050Build`: genera el spec y valida formato (sin instalar Rust).

Nota honesta de alcance: el `pyoxidizer.bzl` empaqueta el **intérprete Python
embebido**; el binario resultante es Python-solo. Para que sirva SIN Go en
producción, `pyclient.main()` debe arrancar un server HTTP nativo (stdlib) que
replique el routing del `router.go` de Go. Esa pieza (server Python embebido)
es trabajo de la siguiente subtarea de empaquetado; en dev sigue usándose
Go+Python con el supervisor. No se rompió nada: el modelo descapotable (dev
Go+Python, prod binario Python) se mantiene.

## v0.6.0 — Hot-reload real (Fase 6)

---

## v0.6.0 — Hot-reload real (Fase 6)  ← ESTADO: COMPLETADO

Objetivo verificable: editar `.html` hace hot-swap del fragmento en memoria sin
reiniciar el server; editar `.pgo` re-transpila y relanza solo Python; error de
transpile mantiene el server vivo.

Entregado:
- `runtime.go`: `Supervisor.Restart()` relanza solo Python (Go sigue vivo).
- `router.go`: `SetView()` hot-swap de fragmento + `NewServerWithSocket()`.
- `cli/dev.go`: `watchAndReload` usa `hotreload` (fsnotify) por extensión:
  `.pgo`→retranspile+Restart, `.html`→SetView. Errores logueados, server vivo.
- `cli/dev.go`: `transpile` usa binario prebuilt (evita `go run` interactivo).
- Test `TestV060HotReload`: cambia fragmento en caliente, server no reinicia.

## v0.7.0 — Multi-tenancy básico (Fase 7)  ← ESTADO: COMPLETADO

Objetivo verificable: 2 tenants aislados en una instancia; cada uno crea un
Customer y no ve los datos del otro.

- `tenancy.go`: `TenantFromRequest` resuelve tenant por header `X-Tenant-ID` o
  subdominio.
- `router.go`: `Handle(method, path, h, auth, tenant)`; inyecta `tenant` en args.
- `db.py`: `connect(tenant=None)` abre `pygo_<tenant>.db`.
- `pyclient`: `dispatch` setea `_current_tenant` global (mutex del supervisor
  lo hace seguro) y filtra `tenant` del handler; coercion de tipos en frontera.
- **Bug atrapado**: handlers que delegan a `CallPython` deben propagar
  `tenant` en el args (sino caen a DB default) — cubierto por el test.
- `gen_go.go` emite `, false, false)` (auth, tenant).
- Test `TestV070Tenancy`: acme/globex aislados (globex NO ve customer de acme).

## v0.8.0 — Plataforma de operación (Fase 8)  ← ESTADO: COMPLETADO

Objetivo verificable: el framework es operable (health, graceful shutdown,
CI) y el descapote a puro-Go funciona (`PYGO_TARGET=go`).
- `router.go`: `/healthz` (liveness) + `/readyz` (readiness) en cada server.
- `router.go`: `Start()` captura SIGTERM/SIGINT → graceful shutdown (para Python + socket).
- `gen_go.go`: `PYGO_TARGET=go` emite handlers puros en Go (sin Python) — descapote real.
- `core/transpiler/parser/parser_test.go`: test unit del AST visitor (front-end del compilador).
- `.github/workflows/ci.yml`: CI corre `go vet` + `go build` + `go test ./...` en cada PR.
- Test `TestV080Operations`: healthz 200 + ruta pura-Go sin Python.

## v0.9.0 — Background jobs (Fase 9)  ← ESTADO: COMPLETADO

Objetivo verificable: un `worker` del `.pgo` encola y ejecuta en segundo plano
(sin bloquear el request HTTP); el cliente recibe `202 {"job_id":"..."}` y
puede pollear el estado con `GET /jobs/:id` hasta `done` + resultado.

- `core/runtime/jobs/queue.go`: cola in-memory con `chan Job` + worker
  goroutine (sin Redis, sin frameworks). Executor inyectado para romper ciclo
  de importación `jobs→runtime`.
- `gen_go.go`: `VisitWorker` emite `POST /jobs/<worker>` que encola y
  devuelve job_id, y `GET /jobs/:id` para pollear estado.
- `gen_py.go`: `VisitWorker` registra el handler Python en `HANDLERS`
  (mismo mecanismo que handlers normales).
- `router.go`: `EnqueueJob` / `GetJob` helpers expuestos a código generado.
- Test `TestV090Jobs`: encola `slow_echo`, poll hasta `done`, verifica
  resultado asíncrono.

## v0.10.0 — Reportes + i18n (Fase 10)  ← ESTADO: COMPLETADO

Objetivo verificable: un handler genera un reporte CSV descargable; la UI responde
en 2 idiomas según el header `Accept-Language`.

Entregado:
- **i18n**: middleware `localeFromRequest` en `router.go` extrae el locale del
  header `Accept-Language` y lo inyecta como `_lang` en los args (solo pasado al
  handler si este lo declara, evitando errores de signature mismatch).
- **Diccionarios de locales**: `core/runtime/locales/{en,es}.json` con claves
  traducibles y soporte para `{param}` formatting.
- **Helper `t(key, lang, **params)`** en `pyclient/__init__.py`: carga los JSON
  al startup y traduce con fallback a `en` → key.
- **Reporte CSV**: handler `customer_report` en `gen_py.py` genera CSV nativo
  (Python `csv` module) desde la tabla `greeting`.
- **DSL `report` + `i18n`**: `ReportNode` / `I18nConfigNode` en AST, `VisitReport`
  en `gen_go.go` (emite GET handler) y `gen_py.go` (emite handler CSV), tokens
  `report`/`i18n` en lexer, `parseReport`/`parseI18nConfig` en parser.
- Test `TestV100ReportsI18n`: verifica i18n es/en + CSV report con datos.

## v0.11.0 — Enum + ForeignKey + Array/Map (Cobertura del DSL)

**Estado: COMPLETADO**

Objetivo verificable: el DSL `.pgo` soporta `Enum`, `ForeignKey`, `Array[T]`, `Map[K]V` como tipos de campo de modelo; el transpiler genera código Python+Go correcto.

### Implementación
- **Enum**: `enum Status: active inactive pending` → Go `type Status string` + Python `class Status(str, enum.Enum)`
- **ForeignKey**: `foreignKey user_id -> User` → AST `ForeignKeyNode` con `Name`/`Target`, Go/Fn placeholder
- **Array[T]**: `tags: Array[String]` → Go `[]string` + Python `list[str]`
- **Map[K]V**: `metadata: Map[String]String` → Go `map[string]string` + Python `dict[str, str]`

### Archivos modificados
- `core/transpiler/ast/ast.go`: nodos `EnumNode`, `ForeignKeyNode`, visitas en `Visitor`
- `core/transpiler/lexer/lexer.go`: tokens `TokenEnum`, `TokenForeignKey`
- `core/transpiler/parser/parser.go`: `parseEnum()`, `parseForeignKey()`, handlers en switch
- `core/transpiler/generators/gen_go.go`: `VisitEnum` (type alias), `VisitForeignKey` (no-op), loop de enums en `VisitProgram`
- `core/transpiler/generators/gen_py.go`: `VisitEnum` (class), `VisitForeignKey` (no-op), import `enum`, loop de enums en `VisitProgram`
- `core/transpiler/v110_test.go`: test integrado `TestV110DSLTypes`
- `examples/hello-world/hello.pgo`: ejemplo con todos los tipos

### Prueba (real)
```
v0.11.0 DSL types OK
```
Suite completa: **runtime 10/10 + transpiler 1/1 PASS**.

## v0.12.0 … → v0.N.0 — Cobertura del DSL y del core
Fases incrementales hasta cubrir la superficie del doc: `Enum`, `ForeignKey`,
`Array/Map`, admin panel, auditoría, API REST automática, bus de eventos, etc.
Cada una = un `v0.N.0` con su test.

## v1.0.0 — Primera versión estable
- Hot-reload, multi-tenancy, background jobs, reportes disponibles.
- Cobertura de tests ≥ 80% en core.
- Security audit externo.

A partir de `v1.0.0`: el monolito puede descapotarse (separar servicios Python
a otros pods cambiando solo el transporte UDS→TCP). Cloud/Mobile/Desktop/
Marketplace/MCP siguen congelados hasta aquí.

---

## Regla de oro

> Cada fase es pequeña, cohesionada y verificable. Si una fase no cabe en un
> `v0.N.0` con un solo objetivo testeable, se parte en dos.
