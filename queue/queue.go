// Package queue provides job queuing for PyGo framework.
package queue

import (
	"context"
	"encoding/json"
	"errors"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
)

// Job represents a background job.
type Job struct {
	ID        string          `json:"id"`
	Name      string          `json:"name"`
	Payload   json.RawMessage `json:"payload"`
	Attempts  int             `json:"attempts"`
	MaxAttempts int           `json:"max_attempts"`
	CreatedAt time.Time       `json:"created_at"`
	RunAt     time.Time       `json:"run_at"`
}

// Handler is a function that processes a job.
type Handler func(ctx context.Context, job *Job) error

// Queue defines the interface for job queues.
type Queue interface {
	Enqueue(ctx context.Context, job *Job) error
	Dequeue(ctx context.Context, timeout time.Duration) (*Job, error)
	RegisterHandler(name string, handler Handler)
	Process(ctx context.Context, concurrency int) error
	Len(ctx context.Context) (int, error)
	Close() error
}

// MemoryQueue implements Queue in-memory (for development).
type MemoryQueue struct {
	mu       sync.Mutex
	jobs     []*Job
	handlers map[string]Handler
	wg       *sync.WaitGroup
	stopCh   chan struct{}
}

// NewMemoryQueue creates a new in-memory queue.
func NewMemoryQueue() *MemoryQueue {
	return &MemoryQueue{
		jobs:     make([]*Job, 0),
		handlers: make(map[string]Handler),
		wg:       &sync.WaitGroup{},
		stopCh:   make(chan struct{}),
	}
}

func (q *MemoryQueue) Enqueue(ctx context.Context, job *Job) error {
	q.mu.Lock()
	defer q.mu.Unlock()
	if job.ID == "" {
		job.ID = time.Now().Format("20060102150405.000000000")
	}
	if job.CreatedAt.IsZero() {
		job.CreatedAt = time.Now()
	}
	if job.MaxAttempts == 0 {
		job.MaxAttempts = 3
	}
	q.jobs = append(q.jobs, job)
	return nil
}

func (q *MemoryQueue) Dequeue(ctx context.Context, timeout time.Duration) (*Job, error) {
	q.mu.Lock()
	defer q.mu.Unlock()

	if len(q.jobs) == 0 {
		return nil, ErrQueueEmpty
	}

	// Get the next job that is due
	now := time.Now()
	for i, job := range q.jobs {
		if job.RunAt.Before(now) || job.RunAt.IsZero() {
			// Remove from queue
			q.jobs = append(q.jobs[:i], q.jobs[i+1:]...)
			return job, nil
		}
	}

	return nil, ErrQueueEmpty
}

func (q *MemoryQueue) RegisterHandler(name string, handler Handler) {
	q.handlers[name] = handler
}

func (q *MemoryQueue) Process(ctx context.Context, concurrency int) error {
	for i := 0; i < concurrency; i++ {
		q.wg.Add(1)
		go q.worker(ctx)
	}
	return nil
}

func (q *MemoryQueue) worker(ctx context.Context) {
	defer q.wg.Done()
	for {
		select {
		case <-q.stopCh:
			return
		case <-ctx.Done():
			return
		default:
			job, err := q.Dequeue(ctx, 1*time.Second)
			if err != nil {
				if !errors.Is(err, ErrQueueEmpty) {
					continue
				}
				time.Sleep(100 * time.Millisecond)
				continue
			}

			handler, ok := q.handlers[job.Name]
			if !ok {
				continue
			}

			if err := handler(ctx, job); err != nil && job.Attempts < job.MaxAttempts {
				job.Attempts++
				q.Enqueue(ctx, job)
			}
		}
	}
}

func (q *MemoryQueue) Len(ctx context.Context) (int, error) {
	q.mu.Lock()
	defer q.mu.Unlock()
	return len(q.jobs), nil
}

func (q *MemoryQueue) Close() error {
	close(q.stopCh)
	q.wg.Wait()
	return nil
}

// RedisQueue implements Queue backed by Redis.
type RedisQueue struct {
	client   *redis.Client
	queueKey string
	handlers map[string]Handler
}

// NewRedisQueue creates a Redis-backed queue.
func NewRedisQueue(addr, password, queueName string) *RedisQueue {
	rdb := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: password,
		DB:       0,
	})
	return &RedisQueue{
		client:   rdb,
		queueKey: "pygo:queue:" + queueName,
		handlers: make(map[string]Handler),
	}
}

func (q *RedisQueue) Enqueue(ctx context.Context, job *Job) error {
	data, _ := json.Marshal(job)
	return q.client.LPush(ctx, q.queueKey, string(data)).Err()
}

func (q *RedisQueue) Dequeue(ctx context.Context, timeout time.Duration) (*Job, error) {
	data, err := q.client.BRPop(ctx, timeout, q.queueKey).Result()
	if err == redis.Nil || len(data) < 2 {
		return nil, ErrQueueEmpty
	}
	var job Job
	if err := json.Unmarshal([]byte(data[1]), &job); err != nil {
		return nil, err
	}
	return &job, nil
}

func (q *RedisQueue) RegisterHandler(name string, handler Handler) {
	q.handlers[name] = handler
}

func (q *RedisQueue) Process(ctx context.Context, concurrency int) error {
	for i := 0; i < concurrency; i++ {
		go q.redisWorker(ctx)
	}
	return nil
}

func (q *RedisQueue) redisWorker(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		default:
			job, err := q.Dequeue(ctx, 5*time.Second)
			if err != nil {
				continue
			}
			if handler, ok := q.handlers[job.Name]; ok {
				if err := handler(ctx, job); err != nil && job.Attempts < job.MaxAttempts {
					job.Attempts++
					q.Enqueue(ctx, job)
				}
			}
		}
	}
}

func (q *RedisQueue) Len(ctx context.Context) (int, error) {
	return int(q.client.LLen(ctx, q.queueKey).Val()), nil
}

func (q *RedisQueue) Close() error {
	return q.client.Close()
}

// ErrQueueEmpty is returned when the queue is empty.
var ErrQueueEmpty = errors.New("queue is empty")
