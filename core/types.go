// Package core provides the core types and ORM for PyGo framework.
package core

import (
	"crypto/rand"
	"database/sql"
	"fmt"
	"time"
)

// AutoID is an auto-incrementing integer field.
type AutoID int64

// UUID is a 128-bit identifier field (native, no external deps).
type UUID [16]byte

// GenerateUUID generates a random UUID v4.
func GenerateUUID() UUID {
	var u UUID
	rand.Read(u[:])
	u[6] = (u[6] & 0x0f) | 0x40 // v4
	u[8] = (u[8] & 0x3f) | 0x80 // variant
	return u
}

func (u UUID) String() string {
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		u[0:4], u[4:6], u[6:8], u[8:10], u[10:16])
}

// Email is a validated email field.
type Email string

// DateTime is a timestamp field.
type DateTime time.Time

// String is a string field with optional validation.
type String string

// Boolean is a boolean field.
type Boolean bool

// Integer is an integer field.
type Integer int64

// Float is a floating point field.
type Float float64

// Decimal is a high-precision decimal field.
type Decimal struct {
	value string
}

// Model is the base struct for all models.
type Model struct {
	ID        AutoID  `db:"id" json:"id"`
	CreatedAt DateTime `db:"created_at" json:"created_at"`
	UpdatedAt DateTime `db:"updated_at" json:"updated_at"`
}

// BaseModel is an interface for all models.
type BaseModel interface {
	GetID() AutoID
	GetCreatedAt() DateTime
	GetUpdatedAt() DateTime
}

// RegisterModel registers a model in the database.
func RegisterModel(db *sql.DB, model interface{}) error {
	// Placeholder for model registration
	_ = db
	_ = model
	return nil
}

// ValidateEmail validates an email address.
func ValidateEmail(e Email) bool {
	s := string(e)
	at := -1
	for i, c := range s {
		if c == '@' {
			if at != -1 {
				return false // más de un @
			}
			at = i
		}
	}
	return at > 0 && at < len(s)-1
}

// QueryBuilder builds SQL queries.
type QueryBuilder struct {
	table   string
	where   []string
	args    []interface{}
	orderBy string
	limitV  int
	offsetV int
}

// NewQuery creates a new QueryBuilder for a table.
func NewQuery(table string) *QueryBuilder {
	return &QueryBuilder{table: table}
}

// Where adds a WHERE clause.
func (q *QueryBuilder) Where(condition string, args ...interface{}) *QueryBuilder {
	q.where = append(q.where, condition)
	q.args = append(q.args, args...)
	return q
}

// OrderBy sets the ORDER BY clause.
func (q *QueryBuilder) OrderBy(order string) *QueryBuilder {
	q.orderBy = order
	return q
}

// Limit sets the LIMIT clause.
func (q *QueryBuilder) Limit(n int) *QueryBuilder {
	q.limitV = n
	return q
}

// Offset sets the OFFSET clause.
func (q *QueryBuilder) Offset(n int) *QueryBuilder {
	q.offsetV = n
	return q
}

// Build returns the SQL query and args.
func (q *QueryBuilder) Build() (string, []interface{}) {
	query := fmt.Sprintf("SELECT * FROM %s", q.table)
	for i, w := range q.where {
		if i == 0 {
			query += " WHERE "
		} else {
			query += " AND "
		}
		query += w
	}
	if q.orderBy != "" {
		query += " ORDER BY " + q.orderBy
	}
	if q.limitV > 0 {
		query += fmt.Sprintf(" LIMIT %d", q.limitV)
	}
	if q.offsetV > 0 {
		query += fmt.Sprintf(" OFFSET %d", q.offsetV)
	}
	return query, q.args
}
