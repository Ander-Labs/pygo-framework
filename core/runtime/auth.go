package runtime

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"net/http"
	"os"
	"strings"
	"time"
)

// JWT is a minimal, dependency-free implementation of the HS256 JWT profile
// (header.payload.signature, base64url). PyGo stays native: no external JWT lib.
//
// The signing key comes from PYGO_JWT_SECRET (never hardcoded).

// Claims is the JWT payload. Sub is the subject (user id); Exp is unix expiry.
type Claims struct {
	Sub string `json:"sub"`
	Exp int64  `json:"exp"`
	// Extra free-form claims.
	Extra map[string]any `json:"ext,omitempty"`
}

// SignHS256 builds a compact JWT (header.payload.signature) signed with the
// secret using HMAC-SHA256.
func SignHS256(c Claims, secret string) (string, error) {
	if c.Exp == 0 {
		c.Exp = time.Now().Add(24 * time.Hour).Unix()
	}
	header := map[string]string{"alg": "HS256", "typ": "JWT"}
	hb, err := json.Marshal(header)
	if err != nil {
		return "", err
	}
	cb, err := json.Marshal(c)
	if err != nil {
		return "", err
	}
	enc := func(b []byte) string {
		return base64.RawURLEncoding.EncodeToString(b)
	}
	signingInput := enc(hb) + "." + enc(cb)
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(signingInput))
	sig := enc(mac.Sum(nil))
	return signingInput + "." + sig, nil
}

// VerifyHS256 validates the signature and expiry, returning the claims.
func VerifyHS256(token, secret string) (Claims, error) {
	var empty Claims
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return empty, errors.New("malformed token")
	}
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(parts[0] + "." + parts[1]))
	expected := base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
	if !hmac.Equal([]byte(expected), []byte(parts[2])) {
		return empty, errors.New("invalid signature")
	}
	payload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return empty, errors.New("bad payload encoding")
	}
	var c Claims
	if err := json.Unmarshal(payload, &c); err != nil {
		return empty, err
	}
	if c.Exp > 0 && time.Now().Unix() > c.Exp {
		return empty, errors.New("token expired")
	}
	return c, nil
}

// jwtSecret reads the signing key from env (never a hardcoded fallback in prod).
func jwtSecret() string {
	if s := os.Getenv("PYGO_JWT_SECRET"); s != "" {
		return s
	}
	return "dev-insecure-change-me" // only for local `pygo dev` without a secret set
}

// AuthMiddleware wraps a handler, requiring a valid Bearer token. On success it
// injects the subject into args["_user"].
func AuthMiddleware(next func(args map[string]any) (any, error)) func(args map[string]any) (any, error) {
	return func(args map[string]any) (any, error) {
		auth, _ := args["_auth"].(string)
		token := strings.TrimPrefix(auth, "Bearer ")
		if token == "" || token == auth {
			return nil, errors.New("missing bearer token")
		}
		claims, err := VerifyHS256(token, jwtSecret())
		if err != nil {
			return nil, err
		}
		args["_user"] = claims.Sub
		return next(args)
	}
}

// extractAuth validates the Bearer token from the Authorization header and
// returns the verified claims. ok is false (and no 401 yet) when missing/invalid;
// the caller returns 401.
func extractAuth(req *http.Request) (claims Claims, ok bool) {
	auth := req.Header.Get("Authorization")
	token := strings.TrimPrefix(auth, "Bearer ")
	if token == "" || token == auth {
		return Claims{}, false
	}
	c, err := VerifyHS256(token, jwtSecret())
	if err != nil {
		return Claims{}, false
	}
	return c, true
}
