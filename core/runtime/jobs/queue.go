// Package jobs provides an in-memory background job queue. It uses a buffered
// channel + a worker goroutine — no external deps (no Redis, no frameworks).
// The actual Python execution is delegated via an Executor callback provided
// at Init time (avoids import cycle jobs→runtime).
package jobs

import (
	"crypto/rand"
	"encoding/hex"
	"sync"
	"time"
)

// Executor is the function that runs a job (e.g., calls Python via runtime.CallPython).
type Executor func(handler string, args map[string]any) (any, error)

// Status is the lifecycle state of a job.
type Status string

const (
	StatusQueued  Status = "queued"
	StatusRunning Status = "running"
	StatusDone    Status = "done"
	StatusFailed  Status = "failed"
)

// Job tracks a single background execution.
type Job struct {
	ID       string
	Handler  string
	Args     map[string]any
	Status   Status
	Result   any
	Error    string
	Created  time.Time
	Finished time.Time
}

// Queue is an in-memory job queue with a single worker goroutine.
type Queue struct {
	mu   sync.RWMutex
	jobs map[string]*Job
	in   chan *Job
	quit chan struct{}
	exec Executor // injected at Init
}

// global queue (the runtime uses a single queue by default).
var defaultQueue *Queue

// Init starts the default queue with the given executor. Safe to call once.
func Init(exec Executor) {
	if defaultQueue != nil {
		return
	}
	defaultQueue = &Queue{
		jobs: make(map[string]*Job),
		in:   make(chan *Job, 128),
		quit: make(chan struct{}),
		exec: exec,
	}
	go defaultQueue.loop()
}

// Enqueue adds a job to the default queue and returns the job immediately
// (status=queued).
func Enqueue(handler string, args map[string]any) *Job {
	if defaultQueue == nil {
		panic("jobs.Init not called")
	}
	j := &Job{
		ID:      newID(),
		Handler: handler,
		Args:    args,
		Status:  StatusQueued,
		Created: time.Now(),
	}
	defaultQueue.mu.Lock()
	defaultQueue.jobs[j.ID] = j
	defaultQueue.mu.Unlock()
	defaultQueue.in <- j
	return j
}

// Get returns a job by ID (nil if not found).
func Get(id string) *Job {
	if defaultQueue == nil {
		return nil
	}
	defaultQueue.mu.RLock()
	defer defaultQueue.mu.RUnlock()
	j := defaultQueue.jobs[id]
	if j == nil {
		return nil
	}
	// Return a copy so callers can't mutate the live job.
	cp := *j
	return &cp
}

// EnqueueJob is the package-level entry gen_go calls. It returns a map so the
// router can JSON-encode it directly as a 202 response.
func EnqueueJob(handler string, args map[string]interface{}) (interface{}, error) {
	j := Enqueue(handler, args)
	return map[string]interface{}{
		"job_id": j.ID,
		"status": string(j.Status),
	}, nil
}

// GetJob returns a job's status by ID. gen_go uses this for the /jobs/:id route.
func GetJob(id string) (interface{}, error) {
	j := Get(id)
	if j == nil {
		return nil, JobNotFoundError(id)
	}
	return map[string]interface{}{
		"job_id":  j.ID,
		"status":  string(j.Status),
		"result":  j.Result,
		"error":   j.Error,
	}, nil
}

// JobNotFoundError is returned when a job ID doesn't exist.
type JobNotFoundError string

func (e JobNotFoundError) Error() string {
	return "job not found: " + string(e)
}

// loop is the worker goroutine. It pulls jobs from the channel and executes
// them via the injected Executor.
func (q *Queue) loop() {
	for {
		select {
		case j := <-q.in:
			q.execute(j)
		case <-q.quit:
			return
		}
	}
}

func (q *Queue) execute(j *Job) {
	q.mu.Lock()
	j.Status = StatusRunning
	q.mu.Unlock()

	result, err := q.exec(j.Handler, j.Args)

	q.mu.Lock()
	defer q.mu.Unlock()
	j.Finished = time.Now()
	if err != nil {
		j.Status = StatusFailed
		j.Error = err.Error()
	} else {
		j.Status = StatusDone
		j.Result = result
	}
}

// Shutdown stops the worker goroutine (graceful).
func Shutdown() {
	if defaultQueue == nil {
		return
	}
	close(defaultQueue.quit)
	defaultQueue = nil
}

func newID() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return "job_" + hex.EncodeToString(b)
}