// Package logger provides structured logging for PyGo framework.
package logger

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"runtime"
	"sync"
	"time"
)

// LogLevel represents the logging level.
type LogLevel int

const (
	LevelDebug LogLevel = iota
	LevelInfo
	LevelWarn
	LevelError
	LevelFatal
)

var levelNames = []string{"debug", "info", "warn", "error", "fatal"}

func (l LogLevel) String() string {
	if int(l) >= 0 && int(l) < len(levelNames) {
		return levelNames[l]
	}
	return "unknown"
}

// Entry represents a log entry.
type Entry struct {
	Timestamp  time.Time `json:"timestamp"`
	Level      string    `json:"level"`
	Message    string    `json:"message"`
	Fields     Fields    `json:"fields,omitempty"`
	Caller     string    `json:"caller,omitempty"`
	Function   string    `json:"func,omitempty"`
}

// Fields holds key-value pairs for structured logging.
type Fields map[string]interface{}

// Logger is the PyGo logger.
type Logger struct {
	mu        sync.Mutex
	output    io.Writer
	level     LogLevel
	fields    Fields
	formatter Formatter
}

// Formatter formats log entries.
type Formatter interface {
	Format(entry *Entry) ([]byte, error)
}

// JSONFormatter formats entries as JSON.
type JSONFormatter struct{}

func (f *JSONFormatter) Format(entry *Entry) ([]byte, error) {
	return json.Marshal(entry)
}

// TextFormatter formats entries as plain text.
type TextFormatter struct{}

func (f *TextFormatter) Format(entry *Entry) ([]byte, error) {
	return []byte(fmt.Sprintf("%s [%s] %s %v\n",
		entry.Timestamp.Format("2006-01-02 15:04:05"),
		entry.Level,
		entry.Message,
		entry.Fields)), nil
}

// New creates a new Logger.
func New(opts ...Option) *Logger {
	l := &Logger{
		output:    os.Stdout,
		level:     LevelInfo,
		formatter: &TextFormatter{},
	}
	for _, opt := range opts {
		opt(l)
	}
	return l
}

// Option configures a Logger.
type Option func(*Logger)

// WithLevel sets the log level.
func WithLevel(level LogLevel) Option {
	return func(l *Logger) {
		l.level = level
	}
}

// WithJSONFormat sets JSON output.
func WithJSONFormat() Option {
	return func(l *Logger) {
		l.formatter = &JSONFormatter{}
	}
}

// WithOutput sets the output writer.
func WithOutput(w io.Writer) Option {
	return func(l *Logger) {
		l.output = w
	}
}

// WithFields adds persistent fields.
func WithFields(fields Fields) Option {
	return func(l *Logger) {
		l.fields = fields
	}
}

// Debug logs a debug message.
func (l *Logger) Debug(args ...interface{}) {
	l.log(LevelDebug, fmt.Sprint(args...))
}

// Info logs an info message.
func (l *Logger) Info(args ...interface{}) {
	l.log(LevelInfo, fmt.Sprint(args...))
}

// Warn logs a warning message.
func (l *Logger) Warn(args ...interface{}) {
	l.log(LevelWarn, fmt.Sprint(args...))
}

// Error logs an error message.
func (l *Logger) Error(args ...interface{}) {
	l.log(LevelError, fmt.Sprint(args...))
}

// Fatal logs a fatal message and exits.
func (l *Logger) Fatal(args ...interface{}) {
	l.log(LevelFatal, fmt.Sprint(args...))
	os.Exit(1)
}

func (l *Logger) log(level LogLevel, msg string) {
	if level < l.level {
		return
	}

	pc, file, line, _ := runtime.Caller(3)
	caller := fmt.Sprintf("%s:%d", file, line)
	funcName := runtime.FuncForPC(pc).Name()

	entry := &Entry{
		Timestamp: time.Now(),
		Level:     level.String(),
		Message:   msg,
		Fields:    l.fields,
		Caller:    caller,
		Function:  funcName,
	}

	data, err := l.formatter.Format(entry)
	if err != nil {
		return
	}

	l.mu.Lock()
	defer l.mu.Unlock()
	fmt.Fprint(l.output, string(data))
}

// WithContext returns a new logger with context fields.
func (l *Logger) WithContext(ctx context.Context) *Logger {
	// In production, extract trace IDs, user IDs, etc. from context
	return l
}

// DefaultLogger returns the default logger instance.
var DefaultLogger = New(
	WithLevel(LevelInfo),
	WithJSONFormat(),
)

// SetLevel changes the log level.
func SetLevel(level LogLevel) {
	DefaultLogger.level = level
}
