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

## v0.5.0 — Build empaquetado (Fase 5)

Objetivo verificable: `pygo build --embed-python` produce binario único que
corre sin `venv` ni Python del sistema, con psycopg/SQLAlchemy.

- PyOxidizer integration.
- Test de C-extensions (mi bandera de riesgo de Fase 0).

---

## v0.6.0 — Hot-reload real (Fase 6)

Objetivo verificable: editar `.pgo` reinicia solo el proceso afectado; `.html`
hot-swap sin reinicio; error de compilación mantiene el server vivo.

- Reinicio granular según tipo de archivo (ya hay fsnotify, falta wiring).

---

## v0.7.0 — Multi-tenancy básico (Fase 7)

Objetivo verificable: 2 tenants aislados en una instancia.

- `tenancy` module (single/multi DB).

---

## v0.8.0 — Background jobs (Fase 8)

Objetivo verificable: `worker` del `.pgo` encola y ejecuta fuera del request.

- Queue in-memory → Redis opcional.
- `worker` node en el transpiler.

---

## v0.9.0 — Reportes + i18n (Fase 9)

Objetivo verificable: reporte PDF/CSV desde un modelo; UI en 2 idiomas.

---

## v0.10.0 … → v0.N.0 — Cobertura del DSL y del core

Fases incrementales hasta cubrir la superficie del doc: `Enum`, `ForeignKey`,
`Array/Map`, admin panel, auditoría, API REST automática, bus de eventos, etc.
Cada una = un `v0.N.0` con su test.

---

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
