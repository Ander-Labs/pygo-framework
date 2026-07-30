package client

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// Client handles communication between Go and Python processes.
type Client struct {
	socketPath string
	timeout    time.Duration
}

// NewClient creates a new client for Go-Python communication.
func NewClient(socketPath string) *Client {
	if socketPath == "" {
		socketPath = filepath.Join(os.TempDir(), "pygo.sock")
	}
	return &Client{
		socketPath: socketPath,
		timeout:    30 * time.Second,
	}
}

// CallPython invokes a Python handler from Go.
// TODO: Implement MessagePack serialization and Unix Domain Socket communication.
// This is the critical missing piece for Go ↔ Python communication.
func (c *Client) CallPython(ctx context.Context, handler string, args map[string]interface{}) (interface{}, error) {
	// Placeholder: In v1.0, this will:
	// 1. Serialize args using MessagePack
	// 2. Connect to Unix Domain Socket at c.socketPath
	// 3. Send request with handler name
	// 4. Receive response
	// 5. Deserialize response
	// 6. Propagate context (tenant, user, etc.)
	return nil, fmt.Errorf("Go-Python communication not yet implemented")
}
