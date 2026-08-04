package websocket

import (
	"fmt"
	"math/rand"
	"encoding/json"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // TODO: Add proper origin check
	},
}

// Client represents a WebSocket client
type Client struct {
	ID       string
	Conn     *websocket.Conn
	Channel  string
	Messages chan []byte
	UserID   string
	Metadata map[string]interface{}
}

// Hub manages WebSocket connections
type Hub struct {
	clients    map[string]*Client
	broadcast  chan []byte
	register   chan *Client
	unregister chan *Client
	mu         sync.RWMutex
}

// NewHub creates a new WebSocket hub
func NewHub() *Hub {
	return &Hub{
		clients:    make(map[string]*Client),
		broadcast:  make(chan []byte, 100),
		register:   make(chan *Client, 100),
		unregister: make(chan *Client, 100),
	}
}

// RegisterClient registers a new client
func (h *Hub) RegisterClient(client *Client) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.clients[client.ID] = client
}

// UnregisterClient removes a client
func (h *Hub) UnregisterClient(client *Client) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if _, ok := h.clients[client.ID]; ok {
		delete(h.clients, client.ID)
		close(client.Messages)
	}
}

// BroadcastToChannel sends a message to all clients in a channel
func (h *Hub) BroadcastToChannel(channel string, message []byte) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	for _, client := range h.clients {
		if client.Channel == channel {
			client.Messages <- message
		}
	}
}

// BroadcastToUser sends a message to a specific user
func (h *Hub) BroadcastToUser(userID string, message []byte) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	for _, client := range h.clients {
		if client.UserID == userID {
			client.Messages <- message
		}
	}
}

// BroadcastGlobal sends a message to all clients
func (h *Hub) BroadcastGlobal(message []byte) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	for _, client := range h.clients {
		client.Messages <- message
	}
}

// GetOnlineUsers returns list of online user IDs
func (h *Hub) GetOnlineUsers() []string {
	h.mu.RLock()
	defer h.mu.RUnlock()
	users := make([]string, 0)
	for _, client := range h.clients {
		if client.UserID != "" {
			users = append(users, client.UserID)
		}
	}
	return users
}

// GetClientCount returns number of online clients
func (h *Hub) GetClientCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.clients)
}

// WebSocketHandler handles WebSocket connections
func WebSocketHandler(hub *Hub) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()

		// Get user ID from query or header
		userID := r.URL.Query().Get("user_id")
		channel := r.URL.Query().Get("channel")
		if channel == "" {
			channel = "default"
		}

		client := &Client{
			ID:       generateClientID(),
			Conn:     conn,
			Channel:  channel,
			Messages: make(chan []byte, 256),
			UserID:   userID,
			Metadata: make(map[string]interface{}),
		}

		// Register client
		hub.register <- client
		defer func() { hub.unregister <- client }()

		// Send presence event
		sendPresence(conn, "online", client)

		// Listen for messages to send
		go func() {
			for msg := range client.Messages {
				conn.WriteMessage(websocket.TextMessage, msg)
			}
		}()

		// Handle incoming messages
		for {
			_, message, err := conn.ReadMessage()
			if err != nil {
				break
			}

			// Parse message
			var msg WebSocketMessage
			if err := json.Unmarshal(message, &msg); err != nil {
				continue
			}

			// Handle message type
			switch msg.Type {
			case "ping":
				conn.WriteMessage(websocket.TextMessage, []byte(`{"type":"pong"}`))
			case "presence":
				sendPresence(conn, "user_online", client)
			case "broadcast":
				hub.BroadcastToChannel(channel, message)
			}
		}
	}
}

// WebSocketMessage represents a WebSocket message
type WebSocketMessage struct {
	Type    string                 `json:"type"`
	Data    map[string]interface{} `json:"data,omitempty"`
	Channel string                 `json:"channel,omitempty"`
}

// PresenceEvent represents a presence change
type PresenceEvent struct {
	Type   string `json:"type"`
	UserID string `json:"user_id"`
	Time   int64  `json:"time"`
}

// generateClientID generates a unique client ID
func generateClientID() string {
	return fmt.Sprintf("ws_%d_%d", time.Now().UnixNano(), rand.Intn(100000))
}

// sendPresence sends a presence event to the client
func sendPresence(conn *websocket.Conn, status string, client *Client) {
	event := PresenceEvent{
		Type:   status,
		UserID: client.UserID,
		Time:   time.Now().Unix(),
	}
	data, _ := json.Marshal(event)
	conn.WriteMessage(websocket.TextMessage, data)
}