package validator

import (
	"testing"
)

func TestValidateStruct(t *testing.T) {
	type TestModel struct {
		Email string `validate:"required,email"`
		Name  string `validate:"required"`
	}

	v := NewValidator()

	// Valid
	m := TestModel{Email: "user@example.com", Name: "John"}
	errs := v.ValidateStruct(m)
	if len(errs) != 0 {
		t.Errorf("Expected 0 errors, got %d", len(errs))
	}

	// Missing email
	m = TestModel{Email: "", Name: "John"}
	errs = v.ValidateStruct(m)
	if len(errs) == 0 {
		t.Error("Expected error for missing email")
	}

	// Missing name
	m = TestModel{Email: "user@example.com", Name: ""}
	errs = v.ValidateStruct(m)
	if len(errs) == 0 {
		t.Error("Expected error for missing name")
	}

	// Invalid email
	m = TestModel{Email: "notanemail", Name: "John"}
	errs = v.ValidateStruct(m)
	// Check it's from email rule
	found := false
	for _, e := range errs {
		if e.Rule == "email" {
			found = true
		}
	}
	if !found {
		t.Error("Expected email validation error")
	}
}

func TestCustomRules(t *testing.T) {
	v := NewValidator()

	// Add custom rule
	v.Add("custom", Rule{
		Name: "custom",
		Validator: func(value interface{}) error {
			if value == nil {
				return ErrRuleViolation("custom rule failed")
			}
			return nil
		},
	})
}

// ErrRuleViolation is a custom validation error.
type ErrRuleViolation string

func (e ErrRuleViolation) Error() string { return string(e) }
