package runtime

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/ander-labs/pygo/core/runtime/jobs"
)
// poll /jobs/:id until status=done, verify result.
func TestV090Jobs(t *testing.T) {
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

	const addr = "127.0.0.1:18088"
	server := NewServerWithSocket(addr, sock, appPath)
	server.Router().Handle("POST", "/jobs/slow_echo", func(args map[string]any) (any, error) {
		// enqueue a job directly via jobs package
		j := jobs.Enqueue("slow_echo", args)
		return map[string]any{
			"job_id": j.ID,
			"status": string(j.Status),
		}, nil
	}, false, false)
	server.Router().Handle("GET", "/jobs/:id", func(args map[string]any) (any, error) {
		id, _ := args["id"].(string)
		return GetJob(id)
	}, false, false)

	go func() { _ = server.Start() }()
	defer server.Stop()

	base := "http://" + addr
	client := &http.Client{Timeout: 10 * time.Second}
	waitFor(t, base+"/hello/Anders", client)

	// Enqueue a job.
	resp, err := client.Post(base+"/jobs/slow_echo?message=HelloAsync", "application/json", nil)
	if err != nil {
		t.Fatalf("enqueue: %v", err)
	}
	b, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusAccepted {
		t.Fatalf("enqueue status %d: %s", resp.StatusCode, b)
	}
	var enq map[string]any
	if err := json.Unmarshal(b, &enq); err != nil {
		t.Fatalf("enqueue body not json: %s", b)
	}
	jobID, _ := enq["job_id"].(string)
	if jobID == "" {
		t.Fatalf("no job_id in response: %v", enq)
	}

	// Poll until done (max 5s).
	deadline := time.Now().Add(5 * time.Second)
	var status string
	var result any
	for time.Now().Before(deadline) {
		gr, err := client.Get(base + "/jobs/" + jobID)
		if err != nil {
			t.Fatalf("poll: %v", err)
		}
		gb, _ := io.ReadAll(gr.Body)
		gr.Body.Close()
		var st map[string]any
		if err := json.Unmarshal(gb, &st); err != nil {
			t.Fatalf("poll body not json: %s", gb)
		}
		status, _ = st["status"].(string)
		if status == "done" {
			result = st["result"]
			break
		}
		if status == "failed" {
			t.Fatalf("job failed: %v", st["error"])
		}
		time.Sleep(50 * time.Millisecond)
	}
	if status != "done" {
		t.Fatalf("job did not complete in time, last status=%s", status)
	}
	if result == nil {
		t.Fatalf("result is nil")
	}
	resultMap, ok := result.(map[string]any)
	if !ok {
		t.Fatalf("result not map: %v", result)
	}
	if resultMap["echo"] != "HelloAsync" {
		t.Fatalf("unexpected echo: %v", resultMap)
	}
	if resultMap["status"] != "ok" {
		t.Fatalf("unexpected status in result: %v", resultMap)
	}

	t.Logf("v0.9.0 OK: job=%s echo=%v", jobID, resultMap["echo"])
}