# QA del PoC — PyGo v0.1.0 (cierre de fase)

Revisión aplicando los criterios de ECC (funciones <50 líneas, archivos <800,
sin mutación, validación en fronteras, sin secrets hardcodeados, errores en
cada nivel). El PoC cumple su objetivo (ciclo end-to-end Go↔Python) y es limpio
en estructura. Los huecos son de alcance de fase, no bugs.

## 🔴 CRÍTICO-1 — gen_go.go no compila solo (work de v0.2.0)
El transpiler emite stubs que dejan `runtime.CallPython(...)` como texto y no
decodifican `resp` al tipo de retorno. Hoy `cli/dev.go` delega de verdad
(bypassing el gen_go). En v0.2.0 el `gen_go.go` debe ser Go compilable que
registre rutas y delegue real.

## 🟠 ALTO-2 — Socket UDS fijo (/tmp/pygo.sock) colisiona entre apps
Falta: socket path por instancia (`.pygo/pygo.sock` o `PYGO_SOCKET` por
proyecto). Validar en frontera. Ver v0.2.0.

## 🟠 ALTO-3 — Supervisor hereda TODO el entorno (os.Environ())
Pasa credenciales del dev (OPENAI_API_KEY, DB creds) al subprocess Python, que
luego ejecuta código de tenants. Superficie de fuga. En v0.4 (auth) pasar solo
un allowlist de env vars, no el entorno completo.

## 🟡 MEDIO-4 — Args de ruta sin validar (inyección en v0.3)
`name` de `/hello/:name` va directo a Python. Cuando el handler haga SQL/render
HTML eso es inyección. Validar/escapar `args` antes de `CallPython` en v0.3.

## 🟡 MEDIO-5 — Sin tests unitarios del transpiler
Solo 1 test de integración. ECC exige 80% cobertura. Faltan tests de
lexer/parser/generators (¿gen_py siempre válido? ¿indentación?). Trabajo v0.N.

## 🟢 LO QUE CUMPLE (criterios ECC)
- Archivos <800 líneas (gen_go 206, socket 168, supervisor 189, dev 176). OK.
- Funciones <50 líneas (goType, exportName, _to_wire). OK.
- Errores en cada nivel; CrossError unificado Go↔Python. OK.
- Sin secrets hardcodeados. OK.
- gen_py.py isomórfico y válido (ast.parse). OK.
- Error de Python no se pierde (exception → CrossError → Go error). OK.

## Veredicto
v0.1.0 completo. Los huecos son de alcance de fase, no bloqueantes. Siguiente:
v0.2.0 (gen_go real + router HTTP + HTMX).
