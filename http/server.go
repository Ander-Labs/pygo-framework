// Package http provides HTTP server and routing built on Go's net/http.
package http

import (
	"database/sql"
	"net/http"
	"time"
)

// Server is the PyGo HTTP server.
type Server struct {
	mux      *http.ServeMux
	db       *sql.DB
	template string
	mw       []MiddlewareFunc
}

// NewServer creates a new PyGo HTTP server.
func NewServer() *Server {
	return &Server{
		mux: http.NewServeMux(),
	}
}

// WithDB attaches a database connection.
func (s *Server) WithDB(db *sql.DB) *Server {
	s.db = db
	return s
}

// GET registers a GET handler.
func (s *Server) GET(path string, handler http.HandlerFunc) {
	s.mux.HandleFunc("GET "+path, handler)
}

// POST registers a POST handler.
func (s *Server) POST(path string, handler http.HandlerFunc) {
	s.mux.HandleFunc("POST "+path, handler)
}

// PUT registers a PUT handler.
func (s *Server) PUT(path string, handler http.HandlerFunc) {
	s.mux.HandleFunc("PUT "+path, handler)
}

// DELETE registers a DELETE handler.
func (s *Server) DELETE(path string, handler http.HandlerFunc) {
	s.mux.HandleFunc("DELETE "+path, handler)
}

// Run starts the server.
func (s *Server) Run(addr string) error {
	srv := &http.Server{
		Addr:         addr,
		Handler:      s.wrappedMux(),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 30 * time.Second,
	}
	return srv.ListenAndServe()
}

// Template renders an HTML template.
func (s *Server) Template(tmpl string) *Server {
	s.template = tmpl
	return s
}

// NotFound registers a custom 404 handler.
func (s *Server) NotFound(handler http.HandlerFunc) {
	s.mux.HandleFunc("NOT_FOUND", handler)
}

// MiddlewareFunc is a middleware function.
type MiddlewareFunc func(http.Handler) http.Handler

// Use applies middleware to the server.
type handlerFunc http.Handler
type middlewareChain []MiddlewareFunc

func (s *Server) Use(mw ...MiddlewareFunc) *Server {
	for _, m := range mw {
		s.mw = append(s.mw, m)
	}
	return s
}

func (s *Server) wrappedMux() http.Handler {
	var h http.Handler = s.mux
	for i := len(s.mw) - 1; i >= 0; i-- {
		h = s.mw[i](h)
	}
	return h
}
