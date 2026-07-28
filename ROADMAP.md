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

## v0.9.0 — Background jobs (Fase 9)
Objetivo verificable: `worker` del `.pgo` encola y ejecuta fuera del request.
- Queue in-memory → Redis opcional.
- `worker` node en el transpiler.

## v0.10.0 — Reportes + i18n (Fase 10)
Objetivo verificable: reporte PDF/CSV desde un modelo; UI en 2 idiomas.

## v1.0.0 — Primera versión estable

Criterio de salida:
- App CRUD real end-to-end (HTMX + ORM + auth + 1 módulo) funciona.
- DSL `.pgo` estable, SemVer, migraciones automáticas.
- `pygo build --embed-python` produce binario desplegable.
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
