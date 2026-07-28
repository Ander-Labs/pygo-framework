package runtime

import (
	"net/http"
	"strings"
)

// TenantFromRequest resolves the active tenant for a request.
//
// Priority: explicit X-Tenant-ID header, then the leftmost subdomain of Host
// (e.g. "acme.app.test" -> "acme"), then "default".
//
// Isolation is enforced by the Python db layer, which opens pygo_<tenant>.db
// based on the tenant passed in args. Because the Supervisor serializes
// CallPython with a mutex, a per-request tenant context is safe.
func TenantFromRequest(req *http.Request) string {
	if t := req.Header.Get("X-Tenant-ID"); t != "" {
		return t
	}
	host := req.Host
	if i := strings.Index(host, "."); i > 0 {
		return host[:i]
	}
	return "default"
}
