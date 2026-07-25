package runtime

import (
	"fmt"
	"html/template"
	"net/http"
	"strings"
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
// query) and returns (result, error) by delegating to Python.
//
// net/http's ServeMux does not support :param wildcards, so routes containing a
// ":name" segment are registered on the parent prefix (e.g. "/hello/:id" ->
// "/hello/") and the param is extracted from the real request path.
func (r *Router) Handle(method, path string, h func(args map[string]any) (any, error)) {
	key := method + " " + path
	registerPath := muxPath(path)
	r.mux.HandleFunc(registerPath, func(w http.ResponseWriter, req *http.Request) {
		if req.Method != method {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		args := map[string]any{}
		extractPathParams(req, path, args)
		// Query params.
		for k, vs := range req.URL.Query() {
			if len(vs) > 0 {
				args[k] = vs[0]
			}
		}
		result, err := h(args)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			_, _ = fmt.Fprintf(w, `{"error":%q}`, err.Error())
			return
		}
		if view, ok := r.views[key]; ok {
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			if err := view.Execute(w, result); err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
			}
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = fmt.Fprintf(w, `%v`, result)
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
	return &Server{router: router, sup: sup, addr: addr}
}

// Router returns the router so generated code can RegisterRoutes + RegisterView.
func (s *Server) Router() *Router { return s.router }

// Start launches Python and begins serving (blocks).
func (s *Server) Start() error {
	if err := s.sup.Start(); err != nil {
		return err
	}
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
