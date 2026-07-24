// Package socket implements the Unix Domain Socket transport between the Go
// server and the Python runtime. Payloads are MessagePack-encoded frames of the
// shape {handler: string, args: map}. Each frame is length-prefixed (4-byte
// big-endian uint32) so Send/Recv can operate on a streaming connection.
package socket

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"os"
	"sync"

	"github.com/vmihailenco/msgpack/v5"
)

// DefaultSocketPath is the default UDS path used when none is configured.
const DefaultSocketPath = "/tmp/pygo.sock"

// Payload is the wire message exchanged between Go and Python.
// Handler is the target handler name; Args carries its keyword arguments.
type Payload struct {
	Handler string                 `msgpack:"handler"`
	Args    map[string]interface{} `msgpack:"args"`
}

// Response is what Python returns for a given Payload. Exactly one of Result or
// Error is meaningful: if Error is non-nil the call failed cross-language.
type Response struct {
	Result interface{} `msgpack:"result"`
	Error  *CrossError `msgpack:"error"`
}

// CrossError is the unified cross-language error struct (see ARCHITECTURE.md §6).
// It is produced on either side (Go or Python) and carried over the socket so
// both runtimes speak the same error shape.
type CrossError struct {
	Type    string                 `msgpack:"type"`
	Message string                 `msgpack:"message"`
	Field   string                 `msgpack:"field"`
	Source  string                 `msgpack:"source"` // "python" | "go"
	Stack   string                 `msgpack:"stack"`
	Context map[string]interface{} `msgpack:"context"`
}

// Error implements the error interface so *CrossError can flow as a Go error.
func (e *CrossError) Error() string {
	if e == nil {
		return "<nil CrossError>"
	}
	if e.Field != "" {
		return fmt.Sprintf("%s: %s (field=%s, source=%s)", e.Type, e.Message, e.Field, e.Source)
	}
	return fmt.Sprintf("%s: %s (source=%s)", e.Type, e.Message, e.Source)
}

// NewGoError builds a CrossError originating on the Go side.
func NewGoError(typ, message string) *CrossError {
	return &CrossError{Type: typ, Message: message, Source: "go", Context: map[string]interface{}{}}
}

// Listener wraps a net.Listener bound to a UDS path. Go acts as the socket
// server; the Python client dials in.
type Listener struct {
	path string
	ln   net.Listener
}

// Listen creates (and cleans up any stale) UDS at path and starts listening.
// If path is empty, DefaultSocketPath is used.
func Listen(path string) (*Listener, error) {
	if path == "" {
		path = DefaultSocketPath
	}
	// Remove any stale socket file from a previous crashed run.
	if _, err := os.Stat(path); err == nil {
		if rmErr := os.Remove(path); rmErr != nil {
			return nil, fmt.Errorf("socket: removing stale socket %q: %w", path, rmErr)
		}
	}
	ln, err := net.Listen("unix", path)
	if err != nil {
		return nil, fmt.Errorf("socket: listen on %q: %w", path, err)
	}
	return &Listener{path: path, ln: ln}, nil
}

// Path returns the UDS filesystem path.
func (l *Listener) Path() string { return l.path }

// Accept blocks until a client connects and returns the wrapped Conn.
func (l *Listener) Accept() (*Conn, error) {
	c, err := l.ln.Accept()
	if err != nil {
		return nil, err
	}
	return &Conn{c: c}, nil
}

// Close closes the listener and removes the socket file.
func (l *Listener) Close() error {
	err := l.ln.Close()
	_ = os.Remove(l.path)
	return err
}

// Conn is a length-prefixed MessagePack framed connection. It is safe for one
// concurrent writer and one concurrent reader; a mutex guards each direction so
// request/response round-trips do not interleave frames.
type Conn struct {
	c        net.Conn
	writeMu  sync.Mutex
	readMu   sync.Mutex
}

// Dial connects to a UDS server at path (used by tests / Go-side clients).
func Dial(path string) (*Conn, error) {
	if path == "" {
		path = DefaultSocketPath
	}
	c, err := net.Dial("unix", path)
	if err != nil {
		return nil, fmt.Errorf("socket: dial %q: %w", path, err)
	}
	return &Conn{c: c}, nil
}

// Send marshals v to MessagePack and writes it as a length-prefixed frame.
func (c *Conn) Send(v interface{}) error {
	b, err := msgpack.Marshal(v)
	if err != nil {
		return fmt.Errorf("socket: marshal: %w", err)
	}
	c.writeMu.Lock()
	defer c.writeMu.Unlock()
	var hdr [4]byte
	binary.BigEndian.PutUint32(hdr[:], uint32(len(b)))
	if _, err := c.c.Write(hdr[:]); err != nil {
		return fmt.Errorf("socket: write header: %w", err)
	}
	if _, err := c.c.Write(b); err != nil {
		return fmt.Errorf("socket: write body: %w", err)
	}
	return nil
}

// Recv reads one length-prefixed frame and unmarshals it into v.
func (c *Conn) Recv(v interface{}) error {
	c.readMu.Lock()
	defer c.readMu.Unlock()
	var hdr [4]byte
	if _, err := io.ReadFull(c.c, hdr[:]); err != nil {
		return err // may be io.EOF on clean disconnect
	}
	n := binary.BigEndian.Uint32(hdr[:])
	body := make([]byte, n)
	if _, err := io.ReadFull(c.c, body); err != nil {
		return fmt.Errorf("socket: read body: %w", err)
	}
	if err := msgpack.Unmarshal(body, v); err != nil {
		return fmt.Errorf("socket: unmarshal: %w", err)
	}
	return nil
}

// Close closes the underlying connection.
func (c *Conn) Close() error { return c.c.Close() }
