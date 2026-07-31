package websocket

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gorilla/websocket"
)

func TestNewHub(t *testing.T) {
	hub := NewHub()
	if hub == nil {
		t.Error("Expected non-nil hub")
	}
	if hub.clients == nil {
		t.Error("Expected non-nil clients map")
	}
}

func TestHubRegisterClient(t *testing.T) {
	hub := NewHub()
	client := &Client{
		ID:       "test-client-1",
		Channel:  "test",
		Messages: make(chan []byte, 10),
	}

	hub.RegisterClient(client)

	hub.mu.RLock()
	_, exists := hub.clients["test-client-1"]
	hub.mu.RUnlock()

	if !exists {
		t.Error("Expected client to be registered")
	}
}

func TestHubUnregisterClient(t *testing.T) {
	hub := NewHub()
	client := &Client{
		ID:       "test-client-1",
		Channel:  "test",
		Messages: make(chan []byte, 10),
	}

	hub.RegisterClient(client)
	hub.UnregisterClient(client)

	hub.mu.RLock()
	_, exists := hub.clients["test-client-1"]
	hub.mu.RUnlock()

	if exists {
		t.Error("Expected client to be unregistered")
	}
}

func TestHubBroadcastToChannel(t *testing.T) {
	hub := NewHub()
	client := &Client{
		ID:       "test-client-1",
		Channel:  "channel-a",
		Messages: make(chan []byte, 10),
	}
	hub.RegisterClient(client)

	message := []byte("test message")
	hub.BroadcastToChannel("channel-a", message)

	select {
	case msg := <-client.Messages:
		if string(msg) != "test message" {
			t.Error("Expected correct message")
		}
	case <-time.After(100 * time.Millisecond):
		t.Error("Expected message on channel")
	}
}

func TestHubBroadcastToUser(t *testing.T) {
	hub := NewHub()
	client := &Client{
		ID:       "test-client-1",
		UserID:   "user-123",
		Channel:  "test",
		Messages: make(chan []byte, 10),
	}
	hub.RegisterClient(client)

	message := []byte("user message")
	hub.BroadcastToUser("user-123", message)

	select {
	case msg := <-client.Messages:
		if string(msg) != "user message" {
			t.Error("Expected correct message")
		}
	case <-time.After(100 * time.Millisecond):
		t.Error("Expected message on channel")
	}
}

func TestHubBroadcastGlobal(t *testing.T) {
	hub := NewHub()
	client := &Client{
		ID:       "test-client-1",
		Channel:  "test",
		Messages: make(chan []byte, 10),
	}
	hub.RegisterClient(client)

	message := []byte("global message")
	hub.BroadcastGlobal(message)

	select {
	case msg := <-client.Messages:
		if string(msg) != "global message" {
			t.Error("Expected correct message")
		}
	case <-time.After(100 * time.Millisecond):
		t.Error("Expected message on channel")
	}
}

func TestHubGetOnlineUsers(t *testing.T) {
	hub := NewHub()
	client1 := &Client{ID: "c1", UserID: "user-1", Channel: "test", Messages: make(chan []byte, 10)}
	client2 := &Client{ID: "c2", UserID: "user-2", Channel: "test", Messages: make(chan []byte, 10)}
	client3 := &Client{ID: "c3", UserID: "", Channel: "test", Messages: make(chan []byte, 10)} // No user

	hub.RegisterClient(client1)
	hub.RegisterClient(client2)
	hub.RegisterClient(client3)

	users := hub.GetOnlineUsers()

	if len(users) != 2 {
		t.Errorf("Expected 2 online users, got %d", len(users))
	}
}

func TestHubGetClientCount(t *testing.T) {
	hub := NewHub()

	if hub.GetClientCount() != 0 {
		t.Error("Expected 0 clients")
	}

	client := &Client{ID: "test", Channel: "test", Messages: make(chan []byte, 10)}
	hub.RegisterClient(client)

	if hub.GetClientCount() != 1 {
		t.Error("Expected 1 client")
	}
}

func TestWebSocketHandler(t *testing.T) {
	hub := NewHub()
	handler := WebSocketHandler(hub)

	// Create test server
	server := httptest.NewServer(handler)
	defer server.Close()

	// Connect as WebSocket client
	wsURL := "ws" + server.URL[4:] + "/ws?user_id=test-user&channel=test"
	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("Failed to connect: %v", err)
	}
	defer conn.Close()

	// Wait for presence event
	conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	_, msg, err := conn.ReadMessage()
	if err != nil {
		t.Fatalf("Failed to read message: %v", err)
	}

	// Verify presence event
	if string(msg) == "" {
		t.Error("Expected presence event")
	}
}

func TestWebSocketPingPong(t *testing.T) {
	hub := NewHub()
	handler := WebSocketHandler(hub)

	server := httptest.NewServer(handler)
	defer server.Close()

	wsURL := "ws" + server.URL[4:] + "/ws?user_id=test-user"
	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("Failed to connect: %v", err)
	}
	defer conn.Close()

	// Read initial message
	conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	conn.ReadMessage()

	// Send ping
	pingMsg := `{"type":"ping"}`
	err = conn.WriteMessage(websocket.TextMessage, []byte(pingMsg))
	if err != nil {
		t.Fatalf("Failed to send ping: %v", err)
	}

	// Read pong
	conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	_, msg, err := conn.ReadMessage()
	if err != nil {
		t.Fatalf("Failed to read pong: %v", err)
	}

	if string(msg) != `{"type":"pong"}` {
		t.Errorf("Expected pong, got %s", string(msg))
	}
}

func TestWebSocketBroadcast(t *testing.T) {
	hub := NewHub()
	handler := WebSocketHandler(hub)

	server := httptest.NewServer(handler)
	defer server.Close()

	// Connect two clients
	wsURL := "ws" + server.URL[4:] + "/ws?user_id=user1&channel=chat"
	conn1, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("Failed to connect client 1: %v", err)
	}
	defer conn1.Close()

	wsURL2 := "ws" + server.URL[4:] + "/ws?user_id=user2&channel=chat"
	conn2, _, err := websocket.DefaultDialer.Dial(wsURL2, nil)
	if err != nil {
		t.Fatalf("Failed to connect client 2: %v", err)
	}
	defer conn2.Close()

	// Wait for connections
	time.Sleep(100 * time.Millisecond)

	// Broadcast from client 1
	broadcastMsg := `{"type":"broadcast","data":{"message":"Hello all!"}}`
	err = conn1.WriteMessage(websocket.TextMessage, []byte(broadcastMsg))
	if err != nil {
		t.Fatalf("Failed to send broadcast: %v", err)
	}

	// Client 2 should receive the message
	conn2.SetReadDeadline(time.Now().Add(2 * time.Second))
	_, msg, err := conn2.ReadMessage()
	if err != nil {
		t.Fatalf("Failed to read broadcast on client 2: %v", err)
	}

	if string(msg) != broadcastMsg {
		t.Errorf("Expected broadcast message, got %s", string(msg))
	}
}

func TestGenerateClientID(t *testing.T) {
	id1 := generateClientID()
	id2 := generateClientID()

	if id1 == id2 {
		t.Error("Expected different IDs")
	}

	if len(id1) < 5 {
		t.Error("Expected ID to have reasonable length")
	}
}

func TestPresenceEvent(t *testing.T) {
	event := PresenceEvent{
		Type:   "online",
		UserID: "user-123",
		Time:   time.Now().Unix(),
	}

	if event.Type != "online" {
		t.Error("Expected type 'online'")
	}

	if event.UserID != "user-123" {
		t.Error("Expected user_id 'user-123'")
	}
}

func TestWebSocketMessage(t *testing.T) {
	msg := WebSocketMessage{
		Type: "ping",
		Data: map[string]interface{}{"test": "value"},
	}

	if msg.Type != "ping" {
		t.Error("Expected type 'ping'")
	}

	if msg.Data["test"] != "value" {
		t.Error("Expected data['test'] = 'value'")
	}
}