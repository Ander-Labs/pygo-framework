# PyGo Framework — Arquitectura (v0.0.0 / Fase 0)

Este documento fija las fronteras técnicas del framework **antes** de escribir
código. Consolida las 10 decisiones críticas de `PYGO-generalidades/Idea-base.md`
(PARTE 2) con las elecciones tomadas. Todo lo que no esté aquí se decide
durante el desarrollo (puntos 11-20 del doc).

Objetivo del framework: **monolito modular descapotable** — arranca como un solo
proceso (Go orquesta Python vía supervisor local) y puede separarse en servicios
cuando el dev lo necesite, sin reescribir la lógica.

---

## 1. Protocolo de comunicación Go ↔ Python  ✅ DECIDIDO

- **Transporte:** Unix Domain Sockets (en Linux/macOS) con fallback a
  localhost TCP en Windows (WSL2).
- **Serialización:** **MessagePack** (binario, sin `.proto`, ~5x más rápido que
  JSON, fácil de inspeccionar con `msgpacktool`).
- **Patrón:** Go es el **server** (escucha el socket); Python es el **client**
  que el supervisor lanza y que se conecta al socket para registrar sus
  handlers de negocio. Go hace el routing HTTP/HTMX y delega la lógica a
  Python por el socket.
- **Por qué no gRPC:** evitamos codegen de `.proto` y acoplamiento; el volumen
  es I/O-bound (CRM/ERP), no necesitamos streaming tipado pesado.
- **Descapotable:** si mañana el servicio Python se mueve a otro pod, el socket
  se reemplaza por TCP y la lógica no cambia. El transporte es un detalle del
  supervisor, no de la lógica.

## 2. Estructura del AST del transpilador  ✅ DECIDIDO (mínimo Fase 0)

Nodos soportados en Fase 0: `Model`, `Route`, `Handler`, `Function`.
Cada nodo tiene `Pos()`, `nodeType()`, y campos propios. El AST se construye
en Go (lexer → parser → AST → validación semántica → generadores Go y Python).
Ver `DSL-SPEC.md` para la gramática concreta.

## 3. Sistema de tipos del DSL `.pgo`  ✅ DECIDIDO (mínimo Fase 0)

Primitivos: `String, Int, Float, Bool, DateTime, UUID, Decimal`.
Compuestos: `Array[T], Map[K]V, Optional[T]` (con `?` estilo TS).
Especiales: `ForeignKey, Enum, Email, URL, Phone`.
**No** generics, **no** union types (PARTE 2, punto 3).

## 4. Empaquetado de Python en el binario  ✅ DECIDIDO

- **Desarrollo:** Python interpretado en `venv/` junto al binario Go, con
  hot-reload del proceso Python.
- **Producción:** **PyOxidizer** embebe Python en el binario único
  (`pygo build --embed-python`). Sin hot-reload en prod, binario zero-dep.
- CLI: `pygo dev` (interpretado) / `pygo build --embed-python` (binario).

## 5. Mecanismo de hot-reload  ✅ DECIDIDO

- `fsnotify` (Go) vigila `.pgo`, `.yaml`, `.html`, `.toml`.
- `.pgo` en `/web` → recompila Go + reinicia proceso Go.
- `.pgo` en `/core` o `.yaml` → reinicia solo proceso Python.
- `.html` → hot-swap de templates sin reiniciar.
- `pygo.toml` → reinicia ambos.
- Si hay error de compilación, **el proceso vivo se mantiene** y el error se
  muestra en el browser (no se cae el server).

## 6. Manejo de errores cross-language  ✅ DECIDIDO

Struct unificado:
```json
{ "type": "ValidationError", "message": "...", "field": "email",
  "source": "python|go", "stack": "...", "context": {} }
```
Se traduce a respuesta HTTP coherente y se loguea en ambos lados con el mismo
`request_id`.

## 7. Configuración unificada  ✅ DECIDIDO (orden de carga)

1. `pygo.toml` (raíz)
2. `config/*.yaml`
3. `modules/*/module.yaml`
4. Variables de entorno (override)
5. `.env` (solo dev)

Schemas validados al arranque. Secrets en env/`.env`, encriptados at-rest en
prod (punto 15, durante desarrollo).

## 8. Bus de eventos interno  ✅ DECIDIDO

Híbrido: **memoria por defecto** (monolito), **Redis opcional** (multi-servidor).
La interfaz es la misma; el backend se elige por config. Sigue el principio
"ligero pero potente".

## 9. Formato de migraciones  ✅ DECIDIDO

Híbrido: **DSL para el 90%** (auto-generadas desde modelos `.pgo`), **SQL
manual para el 10%** edge. Cubre SQLite (dev) → PostgreSQL (prod).

## 10. Inyección de dependencias  ✅ DECIDIDO

Auto-wiring simple estilo FastAPI: `ctx` siempre disponible, servicios
registrados en `pygo.toml`. **No** container complejo.

---

## Reglas rígidas de archivos (del doc, confirmadas)

| Extensión | Responsabilidad |
|---|---|
| `.pgo` | SOLO lógica (handlers, métodos, workers) |
| `.yaml` | SOLO declaraciones (modelos simples, config) |
| `.html` | SOLO vistas (HTMX) |
| `.toml` | SOLO config del proyecto (`pygo.toml`) |

Sin excepciones. Esto es lo que hace alineable el código para sub-agentes.

---

## Stack confirmado

- **Backend:** Go (web/HTMX routing) + Python (lógica/datos).
- **Frontend:** HTMX + Tailwind + Alpine.js.
- **DSL:** `.pgo` (Fase 0, mínimo) + YAML declarativo.
- **DB:** SQLite (dev) → PostgreSQL (prod).
- **Cache:** memory → Redis (opcional).
- **Queue:** in-memory → Redis (opcional).
- **Licencia:** AGPL v3 (core 100% libre).

---

## Qué está FUERA de alcance hasta PyGo estable

PyGo Cloud, PyGo Mobile, PyGo Desktop, Marketplace, MCP Extensions, IDE
plugins. Se congelan hasta v1.0. El foco es el core + PoC funcional.

---

## Reutilización de `Ander-Labs/ECC` (biblioteca de consulta)

El repo ECC (clonado localmente) contiene agents/skills/commands/plugins que
pueden reutilizarse para cubrir huecos de equipo:
- Skills de codegen / scaffolding → aceleran los generadores del transpiler.
- Agents de revisión → suplen code review de un equipo grande.
- Plugins de CI/CD → validación de módulos `.pgo`.
ECC se usa como **referencia**, no se instala en el framework.
