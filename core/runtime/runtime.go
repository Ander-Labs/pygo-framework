// Package runtime supervises the Python subprocess and exposes CallPython, the
// bridge the transpiler-generated gen_go.go uses to delegate handlers to Python.
//
// Lifecycle:
//  1. Supervisor.Start opens the UDS listener (Go is the server).
//  2. It launches `python3 <module>` with PYGO_SOCKET set to the socket path.
//  3. It waits (Accept) for the Python client to dial in.
//  4. CallPython sends a {handler, args} frame and blocks for the response.
//
// The package keeps a process-wide default Supervisor so generated code can call
// the package-level runtime.CallPython without threading a handle everywhere.
package runtime

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"sync"
	"time"

	"github.com/ander-labs/pygo/core/runtime/socket"
)

// Config parameterizes a Supervisor.
type Config struct {
	// SocketPath is the UDS path; empty means socket.DefaultSocketPath.
	SocketPath string
	// Interpreter is the Python executable (default "python3").
	Interpreter string
	// Module is the Python entrypoint (e.g. "app.py" or "-m core.runtime.pyclient").
	Module string
	// ExtraArgs are appended after the module.
	ExtraArgs []string
	// AcceptTimeout bounds how long we wait for Python to connect.
	AcceptTimeout time.Duration
}

// Supervisor owns the Python subprocess and its socket connection.
type Supervisor struct {
	cfg  Config
	ln   *socket.Listener
	conn *socket.Conn
	cmd  *exec.Cmd

	mu      sync.Mutex // serializes CallPython round-trips
	started bool
}

var (
	defaultMu   sync.RWMutex
	defaultSupv *Supervisor
)

// New builds a Supervisor from cfg, filling defaults.
func New(cfg Config) *Supervisor {
	if cfg.SocketPath == "" {
		cfg.SocketPath = socket.DefaultSocketPath
	}
	if cfg.Interpreter == "" {
		cfg.Interpreter = "python3"
	}
	if cfg.AcceptTimeout == 0 {
		cfg.AcceptTimeout = 10 * time.Second
	}
	return &Supervisor{cfg: cfg}
}

// SetDefault registers s as the process-wide Supervisor used by the package-level
// CallPython helper.
func SetDefault(s *Supervisor) {
	defaultMu.Lock()
	defaultSupv = s
	defaultMu.Unlock()
}

// Start opens the socket, launches Python and waits for it to connect.
func (s *Supervisor) Start() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.started {
		return nil
	}

	ln, err := socket.Listen(s.cfg.SocketPath)
	if err != nil {
		return err
	}
	s.ln = ln

	args := append([]string{s.cfg.Module}, s.cfg.ExtraArgs...)
	cmd := exec.Command(s.cfg.Interpreter, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Env = append(os.Environ(), "PYGO_SOCKET="+ln.Path())
	if err := cmd.Start(); err != nil {
		_ = ln.Close()
		return fmt.Errorf("runtime: starting python (%s %v): %w", s.cfg.Interpreter, args, err)
	}
	s.cmd = cmd

	// Wait for Python to dial in, bounded by AcceptTimeout.
	type acceptResult struct {
		conn *socket.Conn
		err  error
	}
	ch := make(chan acceptResult, 1)
	go func() {
		c, err := ln.Accept()
		ch <- acceptResult{conn: c, err: err}
	}()

	select {
	case res := <-ch:
		if res.err != nil {
			_ = s.stopLocked()
			return fmt.Errorf("runtime: accepting python connection: %w", res.err)
		}
		s.conn = res.conn
	case <-time.After(s.cfg.AcceptTimeout):
		_ = s.stopLocked()
		return fmt.Errorf("runtime: timed out after %s waiting for python to connect", s.cfg.AcceptTimeout)
	}

	s.started = true
	log.Printf("runtime: python connected on %s (pid=%d)", ln.Path(), cmd.Process.Pid)
	return nil
}

// CallPython sends handler+args over the socket and returns Python's result.
// A cross-language error from Python is returned as a *socket.CrossError.
func (s *Supervisor) CallPython(handler string, args map[string]interface{}) (interface{}, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if !s.started || s.conn == nil {
		return nil, socket.NewGoError("RuntimeError", "supervisor not started")
	}
	if args == nil {
		args = map[string]interface{}{}
	}
	if err := s.conn.Send(socket.Payload{Handler: handler, Args: args}); err != nil {
		return nil, socket.NewGoError("TransportError", err.Error())
	}
	var resp socket.Response
	if err := s.conn.Recv(&resp); err != nil {
		return nil, socket.NewGoError("TransportError", err.Error())
	}
	if resp.Error != nil {
		return nil, resp.Error
	}
	return resp.Result, nil
}

// Restart terminates and relaunches only the Python subprocess, keeping the Go
// server alive. Used by hot-reload when a .pgo changes.
func (s *Supervisor) Restart() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.stopLocked(); err != nil {
		return err
	}
	// Re-open the socket and relaunch Python.
	ln, err := socket.Listen(s.cfg.SocketPath)
	if err != nil {
		return err
	}
	s.ln = ln
	args := append([]string{s.cfg.Module}, s.cfg.ExtraArgs...)
	cmd := exec.Command(s.cfg.Interpreter, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Env = append(os.Environ(), "PYGO_SOCKET="+ln.Path())
	if err := cmd.Start(); err != nil {
		_ = ln.Close()
		return fmt.Errorf("runtime: restarting python: %w", err)
	}
	s.cmd = cmd

	type acceptResult struct {
		conn *socket.Conn
		err  error
	}
	ch := make(chan acceptResult, 1)
	go func() {
		c, err := ln.Accept()
		ch <- acceptResult{conn: c, err: err}
	}()
	select {
	case res := <-ch:
		if res.err != nil {
			_ = s.stopLocked()
			return fmt.Errorf("runtime: accepting python after restart: %w", res.err)
		}
		s.conn = res.conn
	case <-time.After(s.cfg.AcceptTimeout):
		_ = s.stopLocked()
		return fmt.Errorf("runtime: timed out waiting for python after restart")
	}
	s.started = true
	log.Printf("runtime: python restarted on %s (pid=%d)", ln.Path(), cmd.Process.Pid)
	return nil
}

// Ready reports whether Python is connected and serving.
func (s *Supervisor) Ready() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.started && s.conn != nil
}

// Stop terminates the Python subprocess and closes the socket.
func (s *Supervisor) Stop() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.stopLocked()
}

// stopLocked assumes s.mu is held.
func (s *Supervisor) stopLocked() error {
	if s.conn != nil {
		_ = s.conn.Close()
		s.conn = nil
	}
	if s.cmd != nil && s.cmd.Process != nil {
		_ = s.cmd.Process.Kill()
		_, _ = s.cmd.Process.Wait()
	}
	if s.ln != nil {
		_ = s.ln.Close()
		s.ln = nil
	}
	s.started = false
	return nil
}

// CallPython is the package-level entry the generated gen_go.go uses. It
// delegates to the default Supervisor registered via SetDefault.
func CallPython(handler string, args map[string]interface{}) (interface{}, error) {
	defaultMu.RLock()
	s := defaultSupv
	defaultMu.RUnlock()
	if s == nil {
		return nil, socket.NewGoError("RuntimeError", "no default supervisor registered (call runtime.SetDefault)")
	}
	return s.CallPython(handler, args)
}
