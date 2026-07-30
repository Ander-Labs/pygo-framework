# TODO para v1.0.0 - PyGo Framework

## 📊 Estado Actual vs Roadmap Definido

```
┌─────────────────────────────────────────────────────────┐
│   PYGO FRAMEWORK v0.20.0 - AUDITORÍA                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ✅ IMPLEMENTADO (30%)                                  │
│   ├─ DSL .pgo básico                                     │
│   ├─ Transpiler (lexer, parser, generadores)             │
│   ├─ Type mappings completos                             │
│   ├─ Multi-tenancy básico                                │
│   ├─ Router HTTP nativo                                  │
│   ├─ Runtime Python (ORM SQLite)                         │
│   ├─ CI/CD                                               │
│   └─ Ejemplos básicos                                    │
│                                                          │
│   🔴 FALTA CRÍTICO (40%)                                 │
│   ├─ Comunicación Go ↔ Python (MessagePack)              │
│   ├─ Sistema de módulos/plugins                          │
│   ├─ API REST automática                                 │
│   ├─ Autenticación completa                              │
│   ├─ CLI completo                                        │
│   ├─ Sistema de configuración                            │
│   └─ Migraciones de BD                                   │
│                                                          │
│   🟡 FALTA ALTO (20%)                                    │
│   ├─ Motor de reportes                                   │
│   ├─ Workflows                                           │
│   ├─ Admin panel                                         │
│   ├─ Background jobs                                     │
│   ├─ Email/notificaciones                                │
│   ├─ Hot-reload                                          │
│   ├─ Testing framework                                   │
│   └─ Documentación completa                              │
│                                                          │
│   🟢 FALTA MEDIO (10%)                                   │
│   ├─ Cache system                                        │
│   ├─ Auditoría                                           │
│   ├─ i18n                                                │
│   ├─ Asset pipeline                                      │
│   └─ WebSockets                                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🔴 BLOQUEANTES (Debe arreglarse YA)

### **1. BUG: Multi-tenancy no propaga tenant a Python** ⚠️
```
Problema documentado en v0.7.0:
"BUG: handlers que delegan a CallPython deben propagar tenant 
(sino DB default)"

Impacto: ROMPE el aislamiento de tenants cuando hay lógica Python
Prioridad: CRÍTICA
```

### **2. Parser de CRUD incompleto** ⚠️
```
Estado en v0.20.0:
- AST tiene CrudNode
- Lexer tiene TokenCrud
- PERO parser no está completamente implementado
- Sintaxis 'crud ModelName' pendiente

Impacto: No se puede generar CRUD automático
Prioridad: CRÍTICA
```

### **3. Comunicación Go ↔ Python NO IMPLEMENTADA**
```
Lo que falta:
- MessagePack protocol for cross-language communication
- Unix Domain Sockets for Go ↔ Python
- Context propagation (tenant, user, etc.)
- Error handling across languages
```

---

## 🟡 CRÍTICO (Features Enterprise Faltantes)

### **4. ORM Completo** ❌
```
Actual: Solo SQLite básico
Falta:
  ✗ PostgreSQL / MySQL support
  ✗ Migraciones automáticas
  ✗ Query builder avanzado
  ✗ Relaciones complejas (has_many, belongs_to, many_to_many)
  ✗ Scopes y filtros
  ✗ Soft delete
  ✗ Timestamps automáticos
```

### **5. Sistema de Autenticación** ❌
```
Falta TODO:
  ✗ Sessions (cookie-based)
  ✗ JWT tokens
  ✗ OAuth2 (Google, GitHub, etc.)
  ✗ Password hashing (Argon2id)
  ✗ Middleware de protección
  ✗ Login/Logout handlers
  ✗ Password reset
  ✗ 2FA/MFA
```

### **6. Sistema de Módulos** ❌
```
Falta TODO:
  ✗ Estructura de módulos (module.yaml)
  ✗ Hooks del ciclo de vida (on_install, on_uninstall)
  ✗ CLI: pygo module install/uninstall/list
  ✗ Registry/marketplace
  ✗ Dependencias entre módulos
  ✗ Permisos por módulo
```

### **7. Admin Panel Automático** ❌
```
Falta TODO:
  ✗ CRUD automático para modelos
  ✗ Dashboard
  ✗ Filtros, búsqueda, paginación
  ✗ Exportar a CSV/Excel
  ✗ Gestión de usuarios
  ✗ Logs de auditoría
```

### **8. API REST Automática** ❌
```
Actual: Solo rutas manuales
Falta:
  ✗ Generación automática desde modelos
  ✗ Paginación automática
  ✗ Filtros automáticos
  ✗ Sorting
  ✗ Include relaciones
  ✗ Documentación OpenAPI/Swagger
```

### **9. Seguridad** ❌
```
Falta TODO:
  ✗ CSRF protection
  ✗ XSS protection (auto-escaping)
  ✗ Rate limiting
  ✗ CORS
  ✗ Content Security Policy
  ✗ SQL injection protection (ya está en ORM)
  ✗ Security headers
```

---

## 🟢 IMPORTANTE (Features de Framework)

### **10. Motor de Reportes** ❌
```
Falta TODO:
  ✗ Generación de PDF
  ✗ Exportación a Excel/CSV
  ✗ Gráficos
  ✗ Filtros avanzados
  ✗ Templates personalizables
```

### **11. Background Jobs Completo** ⚠️
```
Actual: Workers básicos
Falta:
  ✗ Queue system (Redis backend)
  ✗ Scheduler (cron-like)
  ✗ Retries automáticos
  ✗ Job status tracking
  ✗ Dashboard de jobs
```

### **12. Cache System** ❌
```
Falta TODO:
  ✗ Memory cache
  ✗ Redis cache (opcional)
  ✗ Fragment caching
  ✗ Query caching
  ✗ Cache invalidation
```

### **13. Email System** ❌
```
Falta TODO:
  ✗ SMTP integration
  ✗ Templates (Jinja2)
  ✗ Queue de emails
  ✗ Email preview en desarrollo
```

### **14. File Upload** ❌
```
Falta TODO:
  ✗ Storage (local, S3)
  ✗ Validaciones (tamaño, tipo)
  ✗ Image processing
  ✗ File preview
```

### **15. WebSockets** ❌
```
Falta TODO:
  ✗ Real-time con HTMX ws extension
  ✗ Channels
  ✗ Pub/Sub
```

### **16. i18n (Internacionalización)** ❌
```
Falta TODO:
  ✗ Sistema de traducciones
  ✗ Formatos regionales (fecha, moneda, número)
  ✗ Timezones
  ✗ Detección automática de locale
```

### **17. Testing Framework Completo** ⚠️
```
Actual: Tests básicos
Falta:
  ✗ Fixtures automáticos
  ✗ Mocking
  ✗ Coverage reports
  ✗ E2E testing (Playwright)
  ✗ Test database isolation
```

---

## 🔵 DESEABLE (Ecosistema)

### **18. Workflows** ❌
```
Falta TODO:
  ✗ Máquinas de estado
  ✗ Transiciones automáticas
  ✗ Historial
  ✗ Notificaciones
```

### **19. Auditoría** ❌
```
Falta TODO:
  ✗ Log de cambios en modelos
  ✗ Tracking de usuarios
  ✗ Exportación de logs
```

### **20. Marketplace/Registry** ❌
```
Falta TODO:
  ✗ Publicación de módulos
  ✗ Versionado semántico
  ✗ CI/CD para módulos
  ✗ Revisión automática
```

### **21. PyGo Cloud** ❌
```
Falta TODO:
  ✗ Hosting gestionado
  ✗ Deploy automático
  ✗ Auto-scaling
  ✗ SSL automático
```

### **22. Extensiones para IDEs** ❌
```
Falta TODO:
  ✗ VS Code extension
  ✗ JetBrains plugin
  ✗ MCP Server para agentes IA
```

### **23. PyGo Mobile/Desktop** ❌
```
Falta TODO:
  ✗ Tauri integration
  ✗ Build para iOS/Android/Windows/Mac/Linux
```

---

## 🎯 Prioridades de Implementación

### **SEMANA 1-2: Arreglar Bloqueables**
1. ✅ **Arreglar BUG de multi-tenancy** (propagación de tenant a Python)
2. ✅ **Completar parser de CRUD** (sintaxis `crud ModelName`)
3. ✅ **Implementar comunicación Go ↔ Python** (MessagePack + Unix Sockets)

### **SEMANA 3-4: ORM y Autenticación**
4. ✅ **PostgreSQL support** (además de SQLite)
5. ✅ **Migraciones automáticas** (generar desde modelos)
6. ✅ **Sistema de autenticación** (sessions + JWT + OAuth2)
7. ✅ **CLI completo** (new, dev, build, gen, db, test, module)

### **SEMANA 5-6: Sistema de Módulos y API**
8. ✅ **Sistema de módulos** (module.yaml, hooks, CLI)
9. ✅ **API REST automática** (desde modelos)
10. ✅ **Admin panel automático** (CRUD para modelos)

### **SEMANA 7-8: Enterprise Features**
11. ✅ **Motor de reportes** (PDF, Excel, CSV)
12. ✅ **Background jobs** (queue, scheduler, retries)
13. ✅ **Email system** (SMTP, templates, queue)
14. ✅ **Cache system** (memory, Redis)

### **SEMANA 9-10: Estabilidad y v1.0.0**
15. ✅ **Seguridad** (CSRF, XSS, Rate limiting, CORS)
16. ✅ **Testing framework** (fixtures, mocking, coverage)
17. ✅ **Auditoría** (log de cambios, tracking)
18. ✅ **i18n** (sistema de traducciones)
19. ✅ **Documentación** (Docusaurus, más ejemplos)
20. ✅ **v1.0.0 estable** - Release