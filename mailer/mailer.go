// Package mailer provides email sending for PyGo framework.
package mailer

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"html/template"
	"net/smtp"
	"time"
)

// Message represents an email message.
type Message struct {
	From    string            `json:"from"`
	To      []string          `json:"to"`
	Cc      []string          `json:"cc,omitempty"`
	Bcc     []string          `json:"bcc,omitempty"`
	Subject string            `json:"subject"`
	HTML    string            `json:"html,omitempty"`
	Text    string            `json:"text,omitempty"`
	Vars    map[string]interface{} `json:"vars,omitempty"`
}

// Client is the PyGo mailer client.
type Client struct {
	host     string
	port     int
	username string
	password string
	from     string
}

// Config holds SMTP configuration.
type Config struct {
	Host     string
	Port     int
	Username string
	Password string
	From     string
}

// New creates a new mailer client.
func New(cfg Config) *Client {
	return &Client{
		host:     cfg.Host,
		port:     cfg.Port,
		username: cfg.Username,
		password: cfg.Password,
		from:     cfg.From,
	}
}

// Send sends an email message.
func (c *Client) Send(ctx context.Context, msg *Message) error {
	if msg.From == "" {
		msg.From = c.from
	}
	if len(msg.To) == 0 {
		return errors.New("no recipients specified")
	}

	auth := smtp.PlainAuth("", c.username, c.password, c.host)
	addr := fmt.Sprintf("%s:%d", c.host, c.port)

	htmlBody := msg.HTML
	if len(msg.Vars) > 0 {
		tmpl, err := template.New("email").Parse(htmlBody)
		if err != nil {
			return err
		}
		var buf bytes.Buffer
		if err := tmpl.Execute(&buf, msg.Vars); err != nil {
			return err
		}
		htmlBody = buf.String()
	}

	mime := "MIME-version: 1.0;\r\n"
	contentType := fmt.Sprintf("Content-Type: multipart/alternative; boundary=\"boundary\"\r\n\r\n")
	body := fmt.Sprintf("%s%s", mime, contentType)

	body += "--boundary\r\n"
	body += fmt.Sprintf("Content-Type: text/plain; charset=\"utf-8\"\r\n\r\n%s\r\n\r\n", msg.Text)
	body += "--boundary\r\n"
	body += fmt.Sprintf("Content-Type: text/html; charset=\"utf-8\"\r\n\r\n%s\r\n\r\n", htmlBody)
	body += "--boundary--\r\n"

	headers := fmt.Sprintf("From: %s\r\nTo: %s\r\nSubject: %s\r\n",
		msg.From, joinStrings(msg.To, ", "), msg.Subject)

	msgData := headers + body

	return smtp.SendMail(addr, auth, msg.From, msg.To, []byte(msgData))
}

// SendQueued queues an email for sending (uses queue package).
func (c *Client) SendQueued(ctx context.Context, msg *Message) error {
	// In production, push to queue for async processing
	// For now, send directly
	return c.Send(ctx, msg)
}

// SendBulk sends multiple messages efficiently.
func (c *Client) SendBulk(ctx context.Context, messages []*Message) error {
	for _, msg := range messages {
		if err := c.Send(ctx, msg); err != nil {
			return err
		}
	}
	return nil
}

// RenderTemplate renders an HTML template with variables.
func RenderTemplate(tmpl string, vars map[string]interface{}) (string, error) {
	t, err := template.New("email").Parse(tmpl)
	if err != nil {
		return "", err
	}
	var buf bytes.Buffer
	if err := t.Execute(&buf, vars); err != nil {
		return "", err
	}
	return buf.String(), nil
}

func joinStrings(parts []string, sep string) string {
	result := ""
	for i, p := range parts {
		if i > 0 {
			result += sep
		}
		result += p
	}
	return result
}

// DefaultClient is the default mailer (configurable).
var DefaultClient *Client

// Send uses the default client.
func Send(ctx context.Context, msg *Message) error {
	if DefaultClient == nil {
		return errors.New("default mailer client not configured")
	}
	return DefaultClient.Send(ctx, msg)
}

// SendWithTemplate sends an email using a template.
func SendWithTemplate(ctx context.Context, to []string, subject, tmpl string, vars map[string]interface{}) error {
	htmlBody, err := RenderTemplate(tmpl, vars)
	if err != nil {
		return err
	}
	msg := &Message{
		To:      to,
		Subject: subject,
		HTML:    htmlBody,
		Vars:    vars,
	}
	return Send(ctx, msg)
}

// Now returns current time (for testing).
func Now() time.Time {
	return time.Now()
}
