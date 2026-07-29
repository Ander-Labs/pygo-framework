package runtime

import (
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/ander-labs/pygo/core/runtime/jobs"
)

// Router adapts generated routes to the standard library net/http mux.
// Generated gen_go.go calls RegisterRoutes(r) where r is a *Router; each route
// becomes an http.HandlerFunc that extracts path/query params, delegates to
// Python via CallPython, and renders the result (JSON by default, or an HTML
// fragment when a view is registered).
//
// Uses only the Go standard library — PyGo stays ultra-light by design.
type Router struct {
	mux   *http.ServeMux
	views map[string]*template.Template // key "METHOD path" -> parsed fragment
}

// NewRouter builds a Router over a fresh ServeMux.
func NewRouter() *Router {
	return &Router{
		mux:   http.NewServeMux(),
		views: map[string]*template.Template{},
	}
}

// Mux exposes the underlying mux (used by the Server).
func (r *Router) Mux() *http.ServeMux { return r.mux }

// Handle registers a route. h receives the parsed args map (path params +
// query) and returns (result, error) by delegating to Python. When auth is
// true, the request must carry a valid Bearer JWT (native middleware).
//
// net/http's ServeMux does not support :param wildcards, so routes containing a
// Handle registers a route. h receives the parsed args map (path params +
// query) and returns (result, error) by delegating to Python. When auth is
// true, the request must carry a valid Bearer JWT (subject injected as _user).
// When tenant is true, the tenant is resolved and injected as "tenant".
//
// net/http's ServeMux does not support :param wildcards, so for routes that
// contain a ":param" segment we register the longest prefix ending before the
// first param and re-extract params from the real request path.
func (r *Router) Handle(method, path string, h func(args map[string]any) (any, error), auth, tenant bool) {
	muxPath := muxPath(path)
	r.mux.HandleFunc(muxPath, func(w http.ResponseWriter, req *http.Request) {
		if req.Method != method {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		args := map[string]any{}
			extractPathParams(req, path, args)
			for k, v := range req.URL.Query() {
				if len(v) > 0 {
					args[k] = v[0]
				}
			}
			// i18n: extract locale from Accept-Language header
						args["_lang"] = localeFromRequest(req)
			if tenant {
				args["tenant"] = TenantFromRequest(req)
			}
		if auth {
			claims, ok := extractAuth(req)
			if !ok {
				http.Error(w, "unauthorized", http.StatusUnauthorized)
				return
			}
			args["_user"] = claims.Sub
		}
		result, err := h(args)
		if err != nil {
			writeError(w, err)
			return
		}
		if view, ok := r.views[method+" "+path]; ok {
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			if execErr := view.Execute(w, result); execErr != nil {
				http.Error(w, execErr.Error(), http.StatusInternalServerError)
			}
			return
		}
		w.Header().Set("Content-Type", "application/json")
		payload, err := json.Marshal(result)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		_, _ = w.Write(payload)
	})
}

// muxPath converts a route with :params into the ServeMux registration path.
// "/hello/:name" -> "/hello/"; "/users" -> "/users".
func muxPath(route string) string {
	parts := splitPath(route)
	for i, p := range parts {
		if len(p) > 1 && p[0] == ':' {
			prefix := "/" + strings.Join(parts[:i], "/")
			if !strings.HasSuffix(prefix, "/") {
				prefix += "/"
			}
			return prefix
		}
	}
	return route
}

// RegisterView binds a parsed HTML fragment to a route key.
func (r *Router) RegisterView(method, path, fragment string) {
	r.views[method+" "+path] = template.Must(template.New("view").Parse(fragment))
}

// SetView hot-swaps an HTML fragment for a route without restarting the server.
// Used by hot-reload when a .html file changes.
func (r *Router) SetView(method, path, fragment string) {
	r.views[method+" "+path] = template.Must(template.New("view").Parse(fragment))
}

// Supervisor returns the underlying Supervisor so callers can Restart() Python
// on hot-reload of .pgo files.
func (s *Server) Supervisor() *Supervisor { return s.sup }

// NewServerWithSocket is like NewServer but lets the caller pick the UDS path
// (used so parallel tests don't collide on the default socket).
func NewServerWithSocket(addr, socketPath, pyModule string, pyExtra ...string) *Server {
	router := NewRouter()
	sup := New(Config{
		Interpreter: "python3",
		Module:      pyModule,
		ExtraArgs:   pyExtra,
		SocketPath:  socketPath,
	})
	SetDefault(sup)
	s := &Server{router: router, sup: sup, addr: addr}
	s.registerHealth()
	// Wire the job queue executor to runtime.CallPython (breaks import cycle).
	jobs.Init(func(handler string, args map[string]any) (any, error) {
		return CallPython(handler, args)
	})
	return s
}

// registerHealth adds /healthz (liveness) and /readyz (readiness) endpoints.
func (s *Server) registerHealth() {
	s.router.mux.HandleFunc("/healthz", func(w http.ResponseWriter, req *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})
	s.router.mux.HandleFunc("/readyz", func(w http.ResponseWriter, req *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if s.sup == nil || !s.sup.Ready() {
			w.WriteHeader(http.StatusServiceUnavailable)
			_, _ = w.Write([]byte(`{"status":"not ready"}`))
			return
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ready"}`))
	})
}

// Server ties the HTTP router to the Python supervisor lifecycle.
type Server struct {
	router *Router
	sup    *Supervisor
	addr   string
}

// NewServer wires a Router + Supervisor and serves on addr.
func NewServer(addr, pyModule string, pyExtra ...string) *Server {
	router := NewRouter()
	sup := New(Config{
		Interpreter: "python3",
		Module:      pyModule,
		ExtraArgs:   pyExtra,
	})
	SetDefault(sup)
	s := &Server{router: router, sup: sup, addr: addr}
	s.registerHealth()
	// Wire the job queue executor to runtime.CallPython (breaks import cycle).
	jobs.Init(func(handler string, args map[string]any) (any, error) {
		return CallPython(handler, args)
	})
	return s
}

// Router returns the router so generated code can RegisterRoutes + RegisterView.
func (s *Server) Router() *Router { return s.router }

// Start launches Python and begins serving. It blocks until the process is
// signalled (SIGTERM/SIGINT) or the server fails; on signal it performs a
// graceful shutdown (stops Python, closes the socket) before returning.
func (s *Server) Start() error {
	if err := s.sup.Start(); err != nil {
		return err
	}
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
	go func() {
		<-sigCh
		log.Printf("runtime: shutdown signal received, stopping")
		_ = s.Stop()
	}()
	return http.ListenAndServe(s.addr, s.router.Mux())
}

// Stop terminates Python.
func (s *Server) Stop() error { return s.sup.Stop() }

// extractPathParams matches :name segments of route against the actual path
// and populates args. Kept minimal and dependency-free.
func extractPathParams(req *http.Request, route string, args map[string]any) {
	routeParts := splitPath(route)
	pathParts := splitPath(req.URL.Path)
	if len(routeParts) != len(pathParts) {
		// Allow trailing matching for prefix-registered routes.
		if len(pathParts) < len(routeParts) {
			return
		}
	}
	limit := len(routeParts)
	if len(pathParts) < limit {
		limit = len(pathParts)
	}
	for i := 0; i < limit; i++ {
		rp := routeParts[i]
		if len(rp) > 1 && rp[0] == ':' {
			args[rp[1:]] = pathParts[i]
		}
	}
}

func splitPath(p string) []string {
	var out []string
	cur := ""
	for _, c := range p {
		if c == '/' {
			if cur != "" {
				out = append(out, cur)
				cur = ""
			}
			continue
		}
		cur += string(c)
	}
	if cur != "" {
		out = append(out, cur)
	}
	return out
}

// writeError renders a cross-language error as JSON, mapping auth/bad-token
// messages to 401 and everything else to 500.
func writeError(w http.ResponseWriter, err error) {
	status := http.StatusInternalServerError
	msg := err.Error()
	low := strings.ToLower(msg)
	if strings.Contains(low, "token") || strings.Contains(low, "bearer") ||
		strings.Contains(low, "unauthor") {
		status = http.StatusUnauthorized
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = fmt.Fprintf(w, `{"error":%q}`, msg)
}

// localeFromRequest extracts the preferred locale from Accept-Language header.
// Returns "es" for Spanish, "en" otherwise (extendable).
func localeFromRequest(req *http.Request) string {
	al := req.Header.Get("Accept-Language")
	if al == "" {
		return "en"
	}
	// Simple parse: accept "es", "es-ES", "en", "en-US", etc.
	if len(al) >= 2 {
		lang := strings.ToLower(al[:2])
		if lang == "es" || lang == "fr" || lang == "de" || lang == "pt" {
			return lang
		}
	}
	return "en"
}
