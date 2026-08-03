// Package http provides routing for PyGo framework.
// Extends Go's net/http with dynamic routes, groups, and middleware.
package http

import (
	"net/http"
	"regexp"
)

// Route represents a registered route.
type Route struct {
	Method  string
	Path    string
	Handler http.HandlerFunc
	Pattern *regexp.Regexp // compiled param pattern
	Params  []string       // param names like [":id", ":slug"]
}

// Router is an enhanced router with dynamic parameters.
type Router struct {
	routes      []Route
	middlewares []MiddlewareFunc
}

// NewRouter creates a new PyGo router.
func NewRouter() *Router {
	return &Router{}
}

// GET registers a GET route.
func (r *Router) GET(path string, handler http.HandlerFunc) {
	r.addRoute("GET", path, handler)
}

// POST registers a POST route.
func (r *Router) POST(path string, handler http.HandlerFunc) {
	r.addRoute("POST", path, handler)
}

// PUT registers a PUT route.
func (r *Router) PUT(path string, handler http.HandlerFunc) {
	r.addRoute("PUT", path, handler)
}

// DELETE registers a DELETE route.
func (r *Router) DELETE(path string, handler http.HandlerFunc) {
	r.addRoute("DELETE", path, handler)
}

// Group creates a route group with a prefix and middleware.
func (r *Router) Group(prefix string) *RouteGroup {
	return &RouteGroup{
		prefix: prefix,
		router: r,
	}
}

// RouteGroup is a group of routes with a common prefix.
type RouteGroup struct {
	prefix      string
	router      *Router
	middlewares []MiddlewareFunc
}

// Use adds middleware to the group.
func (g *RouteGroup) Use(mw ...MiddlewareFunc) *RouteGroup {
	g.middlewares = append(g.middlewares, mw...)
	return g
}

// GET registers a GET route in this group.
func (g *RouteGroup) GET(path string, handler http.HandlerFunc) {
	g.router.addRoute("GET", g.prefix+path, handler)
}

// POST registers a POST route in this group.
func (g *RouteGroup) POST(path string, handler http.HandlerFunc) {
	g.router.addRoute("POST", g.prefix+path, handler)
}

// addRoute compiles a route with dynamic parameters.
func (r *Router) addRoute(method, path string, handler http.HandlerFunc) {
	// Extract params: /users/:id/posts/:post_id → ["id", "post_id"]
	paramRegex := regexp.MustCompile(`:([a-zA-Z_][a-zA-Z0-9_]*)`)
	params := paramRegex.FindAllStringSubmatch(path, -1)

	// Convert /users/:id → /users/([^/]+)
	paramNames := make([]string, 0)
	for _, p := range params {
		paramNames = append(paramNames, p[1])
	}

	// Build regex pattern
	regexPath := paramRegex.ReplaceAllString(path, `([^/]+)`)
	regexStr := "^" + regexPath + "$"
	pattern, _ := regexp.Compile(regexStr)

	r.routes = append(r.routes, Route{
		Method:  method,
		Path:    path,
		Handler: handler,
		Pattern: pattern,
		Params:  paramNames,
	})
}

// ServeHTTP implements http.Handler.
func (r *Router) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	for _, route := range r.routes {
		if route.Method != req.Method {
			continue
		}
		if route.Pattern == nil {
			if route.Path == req.URL.Path {
				route.Handler(w, req)
				return
			}
			continue
		}

		matches := route.Pattern.FindStringSubmatch(req.URL.Path)
		if matches != nil {
			// Extract params (matches[1:] are the captured groups)
			for i, name := range route.Params {
				// params would be stored in context
				_ = matches[i+1]
				_ = name
			}
			route.Handler(w, req)
			return
		}
	}

	// No route found
	http.NotFound(w, req)
}

// HandlerAdapter adapts a Router to http.Handler.
func (r *Router) Handler() http.Handler {
	return r
}
