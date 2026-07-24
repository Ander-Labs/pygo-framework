# PyGo Framework — Arquitectura (v0.0.0 / Fase 0)

Este documento fija las fronteras técnicas del framework **antes** de escribir
código. Consolida las 10 decisiones críticas de `PYGO-generalidades/Idea-base.md`
(PARTE 2) con las **mejores opciones escalables** elegidas para PyGo. Todo lo
que no esté aquí se decide durante el desarrollo (puntos 11-20 del doc).

Objetivo: **monolito modular descapotable** — arranca como un proceso (Go
orquesta Python vía supervisor local) y se separa en servicios cuando el dev lo
necesita, sin reescribir la lógica.

Principio rector del DSL: **`.pgo` es isomórfico a Python** (indentación y
tipos). `gen_py` es casi 1:1; `gen_go` es mecánico desde el AST. Ver
`DSL-SPEC.md`.

---

## 1. Protocolo Go ↔ Python  →  **MessagePack + Unix Domain Sockets**  ✅

- **Transporte:** UDS (Linux/macOS), fallback localhost TCP en Windows/WSL2.
- **Serialización:** **MessagePack** — binario, sin `.proto`, ~5x más rápido
  que JSON, inspeccionable con `msgpacktool`.
- **Patrón:** Go = server del socket; Python = client que el supervisor lanza
  y registra handlers de negocio. Go hace routing HTTP/HTMX y delega lógica a
  Python por el socket.
- **Escalabilidad:** el transporte es detalle del supervisor. Para descapotar,
  el socket UDS se cambia por TCP y la lógica no cambia. Idéntica interfaz.
- **Por qué no gRPC:** evita codegen `.proto` y acoplamiento; el volumen es
  I/O-bound (CRM/ERP), no streaming tipado pesado.

## 2. AST del transpilador  →  **Visitor pattern desde Fase 0**  ✅

Nodos Fase 0: `Model`, `Route`, `Handler`, `Function`. AST construido en Go.
Se usa **visitor pattern** desde el inicio (extensibilidad, punto 20 del doc)
aunque solo haya 2 generadores. Así crecer el DSL no rompe los generadores.

## 3. Sistema de tipos  →  **primitivos + `?`/`|None` + FK/Enum/Email/URL/Phone**  ✅

Sin generics, sin union types (Fase 0). Mapeo directo: Python `str`/Go `string`,
etc. Ver `DSL-SPEC.md`.

## 4. Empaquetado Python  →  **dev interpretado / prod PyOxidizer**  ✅

- Dev: Python en `venv/`, hot-reload del proceso Python.
- Prod: **PyOxidizer** embebe Python en binario único (`pygo build --embed-python`).
- ⚠️ **Testear PyOxidizer temprano (Fase 1)** con C-extensions reales
  (psycopg/SQLAlchemy) — no dejar para v1.0.

## 5. Hot-reload  →  **fsnotify granular + proceso vivo en error**  ✅

- `fsnotify` vigila `.pgo/.yaml/.html/.toml`.
- `.pgo` en `/web` → recompila Go + reinicia Go. `.pgo`/`yaml` en `/core` →
  reinicia Python. `.html` → hot-swap sin reiniciar. `pygo.toml` → reinicia ambos.
- Si hay error de compilación, **el proceso vivo se mantiene** y el error se
  muestra en el browser.
- ⚠️ Build de Go en cada cambio de `/web` puede ser lento: usar `go build`
  cacheado o `go run` con watch en dev.

## 6. Errores cross-language  →  **struct unificado + request_id**  ✅

```json
{ "type": "ValidationError", "message": "...", "field": "email",
  "source": "python|go", "stack": "...", "context": {} }
```
Traducido a HTTP coherente y logueado en ambos lados con el mismo `request_id`.

## 7. Config unificada  →  **toml → yaml → module.yaml → env → .env**  ✅

- Orden de carga fijado. Schemas validados al arranque.
- ⚠️ Secrets: `.env` plano en dev está bien; en **prod encriptados at-rest**
  (punto 15). Definir en Fase 1, no en v1.0, para no filtrar credenciales.

## 8. Bus de eventos  →  **híbrido memoria/Redis (misma interfaz)**  ✅

Memoria por defecto (monolito). Redis opcional (multi-servidor). Misma interfaz
de eventos → cambiar backend = descapotar sin tocar lógica.

## 9. Migraciones  →  **DSL 90% + SQL 10%**  ✅

Auto-gen desde modelos `.pgo` (evita drift). SQL manual para edge cases.
Portabilidad SQLite (dev) → PostgreSQL (prod) vía DSL.

## 10. Inyección de dependencias  →  **auto-wiring estilo FastAPI, sin container**  ✅

`ctx` siempre disponible; servicios registrados en `pygo.toml`. Sin container
complejo (preserva DX).

---

## Reglas rígidas de archivos (confirmadas)

| Ext | Responsabilidad |
|---|---|
| `.pgo` | SOLO lógica (handlers, métodos, workers) — sintaxis idéntica a Python |
| `.yaml` | SOLO declaraciones (modelos simples, config) |
| `.html` | SOLO vistas (HTMX) |
| `.toml` | SOLO config (`pygo.toml`) |

Sin excepciones. Esto alinea el código para sub-agentes.

---

## Stack confirmado

- **Backend:** Go (routing/HTMX) + Python (lógica/datos).
- **Frontend:** HTMX + Tailwind + Alpine.js.
- **DSL:** `.pgo` isomórfico a Python (Fase 0 mínimo) + YAML declarativo.
- **DB:** SQLite (dev) → PostgreSQL (prod).
- **Cache/Queue:** memory → Redis (opcional).
- **Licencia:** AGPL v3 (core 100% libre).

---

## Fuera de alcance hasta PyGo estable

PyGo Cloud, Mobile, Desktop, Marketplace, MCP, IDE plugins. Congelados hasta
v1.0. Foco: core + PoC funcional.

---

## Reutilización de `Ander-Labs/ECC` (biblioteca de consulta)

ECC (clonado local) tiene agents/skills/commands/plugins reutilizables para
cubrir huecos de equipo:
- Skills de codegen/scaffolding → aceleran generadores del transpiler.
- Agents de revisión → suplen code review de equipo grande.
- Plugins CI/CD → validación de módulos `.pgo`.
Se usa como **referencia**, no se instala en el framework.
