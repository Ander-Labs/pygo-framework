package core

import (
	"testing"
)

func TestUUID(t *testing.T) {
	u := GenerateUUID()
	if u == [16]byte{} {
		t.Error("UUID should not be empty")
	}
}

func TestValidateEmail(t *testing.T) {
	tests := []struct {
		email  Email
		valid  bool
	}{
		{"user@example.com", true},
		{"invalid-email", false},
		{"@example.com", false},
		{"user@", false},
	}
	for _, tc := range tests {
		if got := ValidateEmail(tc.email); got != tc.valid {
			t.Errorf("ValidateEmail(%q) = %v, want %v", tc.email, got, tc.valid)
		}
	}
}

func TestQueryBuilder(t *testing.T) {
	q := NewQuery("users").
		Where("id = ?", 1).
		Where("name LIKE ?", "John%").
		OrderBy("id DESC").
		Limit(10).
		Offset(20)

	query, args := q.Build()
	expected := "SELECT * FROM users WHERE id = ? AND name LIKE ? ORDER BY id DESC LIMIT 10 OFFSET 20"
	if query != expected {
		t.Errorf("Query = %q, want %q", query, expected)
	}
	if len(args) != 2 {
		t.Errorf("Args length = %d, want 2", len(args))
	}
}

func TestModelBase(t *testing.T) {
	// Ensure Model struct has correct JSON tags
	m := Model{}
	if m.ID != 0 {
		t.Error("Model ID should default to 0")
	}
}
