package client

import (
	"context"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"sync"
	"time"
)

// Message represents a message in the Go-Python protocol.
type Message struct {
	Handler string                 `json:"handler"`
	Args    map[string]interface{} `json:"args"`
	Context map[string]interface{} `json:"context"`
}

// Client handles communication between Go and Python processes.
type Client struct {
	socketPath string
	timeout    time.Duration
	mu         sync.Mutex
	conn       net.Conn
}

// NewClient creates a new client for Go-Python communication.
func NewClient(socketPath string) *Client {
	if socketPath == "" {
		socketPath = "/tmp/pygo.sock"
	}
	return &Client{
		socketPath: socketPath,
		timeout:    30 * time.Second,
	}
}

// connect establishes a connection to the Python server.
func (c *Client) connect() error {
	if c.conn != nil {
		return nil
	}

	var d net.Dialer
	ctx, cancel := context.WithTimeout(context.Background(), c.timeout)
	defer cancel()

	conn, err := d.DialContext(ctx, "unix", c.socketPath)
	if err != nil {
		return fmt.Errorf("failed to connect to %s: %w", c.socketPath, err)
	}

	c.conn = conn
	return nil
}

// CallPython invokes a Python handler from Go.
func (c *Client) CallPython(ctx context.Context, handler string, args map[string]interface{}) (interface{}, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if err := c.connect(); err != nil {
		return nil, err
	}

	// Build message with context propagation
	msg := Message{
		Handler: handler,
		Args:    args,
		Context: extractContext(ctx),
	}

	// Use JSON for now (MessagePack to be added in v1.0)
	data, err := json.Marshal(msg)
	if err != nil {
		return nil, fmt.Errorf("marshal error: %w", err)
	}

	// Write length prefix + data
	length := make([]byte, 4)
	binary.BigEndian.PutUint32(length, uint32(len(data)))

	if _, err := c.conn.Write(length); err != nil {
		return nil, fmt.Errorf("write length: %w", err)
	}
	if _, err := c.conn.Write(data); err != nil {
		return nil, fmt.Errorf("write data: %w", err)
	}

	// Read response length
	respLen := make([]byte, 4)
	if _, err := io.ReadFull(c.conn, respLen); err != nil {
		return nil, fmt.Errorf("read response length: %w", err)
	}

	respSize := binary.BigEndian.Uint32(respLen)
	respData := make([]byte, respSize)
	if _, err := io.ReadFull(c.conn, respData); err != nil {
		return nil, fmt.Errorf("read response data: %w", err)
	}

	var result interface{}
	if err := json.Unmarshal(respData, &result); err != nil {
		return nil, fmt.Errorf("unmarshal response: %w", err)
	}

	return result, nil
}

// extractContext extracts tenant and user info from context.
// This fixes the multi-tenancy bug where tenant was not propagated.
func extractContext(ctx context.Context) map[string]interface{} {
	result := make(map[string]interface{})

	if tenant, ok := ctx.Value("tenant").(string); ok && tenant != "" {
		result["tenant"] = tenant
	}
	if user, ok := ctx.Value("user").(map[string]interface{}); ok {
		result["user"] = user
	}

	return result
}
