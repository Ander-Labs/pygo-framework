// Package validator provides input validation for PyGo framework.
package validator

import (
	"errors"
	"fmt"
	"reflect"
	"regexp"
	"strings"
)

// Rule defines a validation rule.
type Rule struct {
	Name      string
	Validator func(value interface{}) error
}

// ValidationError describes a validation failure.
type ValidationError struct {
	Field string
	Rule  string
	Msg   string
}

func (e ValidationError) Error() string {
	return fmt.Sprintf("field '%s' failed validation '%s': %s", e.Field, e.Rule, e.Msg)
}

// ValidationErrors is a collection of validation errors.
type ValidationErrors []ValidationError

func (ve ValidationErrors) Error() string {
	var errs []string
	for _, e := range ve {
		errs = append(errs, e.Error())
	}
	return strings.Join(errs, "; ")
}

// Validator holds validation rules.
type Validator struct {
	rules map[string][]Rule
}

// NewValidator creates a new validator.
func NewValidator() *Validator {
	v := &Validator{
		rules: make(map[string][]Rule),
	}
	v.registerDefaultRules()
	return v
}

func (v *Validator) registerDefaultRules() {
	v.Add("required", Rule{
		Name: "required",
		Validator: func(value interface{}) error {
			if value == nil {
				return errors.New("is required")
			}
			v := reflect.ValueOf(value)
			switch v.Kind() {
			case reflect.String:
				if v.Len() == 0 {
					return errors.New("is required")
				}
			case reflect.Slice, reflect.Array, reflect.Map:
				if v.Len() == 0 {
					return errors.New("is required")
				}
			}
			return nil
		},
	})

	v.Add("email", Rule{
		Name: "email",
		Validator: func(value interface{}) error {
			email, ok := value.(string)
			if !ok {
				return errors.New("must be a string")
			}
			emailRegex := regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)
			if !emailRegex.MatchString(email) {
				return errors.New("is not a valid email")
			}
			return nil
		},
	})

	v.Add("min", Rule{
		Name: "min",
		Validator: createMinValidator(),
	})

	v.Add("max", Rule{
		Name: "max",
		Validator: createMaxValidator(),
	})

	v.Add("uuid", Rule{
		Name: "uuid",
		Validator: func(value interface{}) error {
			s, ok := value.(string)
			if !ok {
				return errors.New("must be a string")
			}
			uuidRegex := regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)
			if !uuidRegex.MatchString(s) {
				return errors.New("is not a valid UUID")
			}
			return nil
		},
	})
}

func createMinValidator() func(value interface{}) error {
	return func(value interface{}) error {
		// For actual use, would accept parameter like min:5
		v := reflect.ValueOf(value)
		switch v.Kind() {
		case reflect.String:
			if v.Len() < 1 {
				return errors.New("must be at least 1 character")
			}
		}
		return nil
	}
}

func createMaxValidator() func(value interface{}) error {
	return func(value interface{}) error {
		return nil // placeholder
	}
}

// Add registers a custom validation rule.
func (v *Validator) Add(name string, rule Rule) {
	v.rules[name] = append(v.rules[name], rule)
}

// ValidateStruct validates a struct using `validate` tags.
func (v *Validator) ValidateStruct(s interface{}) ValidationErrors {
	var errors ValidationErrors
	val := reflect.ValueOf(s)
	if val.Kind() == reflect.Ptr {
		val = val.Elem()
	}

	if val.Kind() != reflect.Struct {
		return nil
	}

	t := val.Type()
	for i := 0; i < t.NumField(); i++ {
		field := t.Field(i)
		fieldVal := val.Field(i)
		tag := field.Tag.Get("validate")
		if tag == "" {
			continue
		}

		rules := strings.Split(tag, ",")
		for _, ruleName := range rules {
			ruleName = strings.TrimSpace(ruleName)
			if ruleName == "" {
				continue
			}

			rulesFound, ok := v.rules[ruleName]
			if !ok {
				continue
			}

			for _, rule := range rulesFound {
				if err := rule.Validator(fieldVal.Interface()); err != nil {
					errors = append(errors, ValidationError{
						Field: field.Name,
						Rule:  rule.Name,
						Msg:   err.Error(),
					})
				}
			}
		}
	}

	return errors
}

// ValidateStruct validates a struct and returns error if validation fails.
func ValidateStruct(s interface{}) error {
	v := NewValidator()
	errs := v.ValidateStruct(s)
	if len(errs) > 0 {
		return errs
	}
	return nil
}
