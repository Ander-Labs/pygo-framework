package runtime

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// TestV070Tenancy verifies two tenants get isolated databases: a Customer
// created under tenant "acme" is not visible under tenant "globex".
func TestV070Tenancy(t *testing.T) {
	repoRoot, err := repoRoot()
	if err != nil {
		t.Fatalf("repo root: %v", err)
	}
	appDir := filepath.Join(repoRoot, "examples", "hello-world")
	appPath := filepath.Join(appDir, "app_poc.py")
	if _, err := os.Stat(appPath); err != nil {
		t.Fatalf("app_poc.py missing: %v", err)
	}
	if err := os.Setenv("PYTHONPATH", repoRoot); err != nil {
		t.Fatal(err)
	}
	sock := filepath.Join(t.TempDir(), "pygo.sock")
	if err := os.Setenv("PYGO_SOCKET", sock); err != nil {
		t.Fatal(err)
	}
	// Ensure clean tenant DBs.
	for _, tn := range []string{"acme", "globex"} {
		_ = os.Remove(filepath.Join(appDir, "pygo_"+tn+".db"))
	}

	const addr = "127.0.0.1:18084"
	server := NewServerWithSocket(addr, sock, appPath)
	// Protected-less routes with tenant isolation on.
	server.Router().Handle("POST", "/customers", func(args map[string]any) (any, error) {
		return CallPython("create_customer", args)
	}, false, true)
	server.Router().Handle("GET", "/customers/:id", func(args map[string]any) (any, error) {
		id := toString(args["id"])
		return CallPython("get_customer", map[string]any{"id": id, "tenant": args["tenant"]})
	}, false, true)

	go func() { _ = server.Start() }()
	defer server.Stop()

	base := "http://" + addr
	client := &http.Client{Timeout: 5 * time.Second}
	waitFor(t, base+"/hello/Anders", client)

	// Create "Acme Inc" under tenant acme.
	acmeBody := createCustomer(t, client, base, "acme", "Acme Inc", "acme@ex.com")
	t.Logf("acme create raw: %v", acmeBody)
	if acmeBody["name"] != "Acme Inc" {
		t.Fatalf("acme create wrong: %v", acmeBody)
	}
	acmeID := acmeBody["id"]

	// Create "Globex" under tenant globex.
	globexBody := createCustomer(t, client, base, "globex", "Globex", "globex@ex.com")
	if globexBody["name"] != "Globex" {
		t.Fatalf("globex create wrong: %v", globexBody)
	}

	// Create a second acme customer so acme has rows the globex DB lacks.
	acmeBody2 := createCustomer(t, client, base, "acme", "Acme Two", "acme2@ex.com")
	acmeID2 := acmeBody2["id"]

	// acme sees its own customers.
	acmeUnderAcme := getCustomer(t, client, base, "acme", acmeID)
	if acmeUnderAcme["name"] != "Acme Inc" {
		t.Fatalf("acme should see its own customer: %v", acmeUnderAcme)
	}
	// globex MUST NOT see acme's second customer (that rowid lives only in acme's DB).
	acme2UnderGlobex := getCustomer(t, client, base, "globex", acmeID2)
	if acme2UnderGlobex != nil {
		t.Fatalf("globex MUST NOT see acme's customer (leak!): %v", acme2UnderGlobex)
	}
	// globex still sees its OWN customer (isolation, not emptiness).
	globexUnderGlobex := getCustomer(t, client, base, "globex", globexBody["id"])
	if globexUnderGlobex["name"] != "Globex" {
		t.Fatalf("globex should see its own customer: %v", globexUnderGlobex)
	}
	t.Logf("v0.7.0 OK: acme=%v globex_see_acme2=%v globex_own=%v",
		acmeUnderAcme, acme2UnderGlobex, globexUnderGlobex)
}

func createCustomer(t *testing.T, client *http.Client, base, tenant, name, email string) map[string]any {
	t.Helper()
	q := url.Values{}
	q.Set("name", name)
	q.Set("email", email)
	req, _ := http.NewRequest("POST", base+"/customers?"+q.Encode(), nil)
	req.Header.Set("X-Tenant-ID", tenant)
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("create %s: %v", tenant, err)
	}
	defer resp.Body.Close()
	b, _ := io.ReadAll(resp.Body)
	var out map[string]any
	if err := json.Unmarshal(b, &out); err != nil {
		t.Fatalf("create body not json: %s", b)
	}
	return out
}

func getCustomer(t *testing.T, client *http.Client, base, tenant string, id any) map[string]any {
	t.Helper()
	url := base + "/customers/" + toString(id)
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("X-Tenant-ID", tenant)
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("get %s: %v", tenant, err)
	}
	defer resp.Body.Close()
	b, _ := io.ReadAll(resp.Body)
	var out map[string]any
	if err := json.Unmarshal(b, &out); err != nil {
		t.Fatalf("get body not json: %s", b)
	}
	t.Logf("getCustomer raw: %s", b)
	// nil when not found (result is null -> map is empty after unmarshal of {"result":null}?)
	if v, ok := out["result"]; ok && v == nil {
		return nil
	}
	if v, ok := out["error"]; ok && v != nil {
		return nil
	}
	return out
}

var _ = bytes.MinRead
