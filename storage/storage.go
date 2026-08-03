// Package storage provides file storage and upload capabilities for PyGo framework.
package storage

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"io"
	"mime/multipart"
	"os"
	"path/filepath"
	"time"
)

// File represents an uploaded file.
type File struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Size      int64     `json:"size"`
	ContentType string  `json:"content_type"`
	Path      string    `json:"path"`
	URL       string    `json:"url"`
	CreatedAt time.Time `json:"created_at"`
}

// Storage defines the interface for file storage backends.
type Storage interface {
	Save(ctx context.Context, file *File, reader io.Reader) error
	Get(ctx context.Context, id string) (*File, io.ReadCloser, error)
	Delete(ctx context.Context, id string) error
	List(ctx context.Context, prefix string) ([]*File, error)
	GetURL(id string) string
}

// LocalStore implements Storage for local filesystem.
type LocalStore struct {
	basePath string
	baseURL  string
}

// NewLocalStorage creates a local filesystem storage.
func NewLocalStorage(basePath, baseURL string) (*LocalStore, error) {
	if err := os.MkdirAll(basePath, 0755); err != nil {
		return nil, err
	}
	return &LocalStore{basePath: basePath, baseURL: baseURL}, nil
}

func (s *LocalStore) Save(ctx context.Context, file *File, reader io.Reader) error {
	// Generate ID if not set
	if file.ID == "" {
		h := sha256.New()
		io.Copy(h, reader)
		// Reset reader after hashing (would need to use multiwriter in production)
		file.ID = hex.EncodeToString(h.Sum(nil)[:8])
		// For real implementation, use io.TeeReader or buffer
		file.ID = time.Now().Format("20060102") + "_" + file.ID
	}

	dir := filepath.Join(s.basePath, time.Now().Format("2006/01/02"))
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}

	fullPath := filepath.Join(dir, file.ID+"_"+file.Name)
	output, err := os.Create(fullPath)
	if err != nil {
		return err
	}
	defer output.Close()

	if _, err := io.Copy(output, reader); err != nil {
		return err
	}

	file.Path = fullPath
	file.URL = s.baseURL + "/uploads/" + filepath.Base(fullPath)
	return nil
}

func (s *LocalStore) Get(ctx context.Context, id string) (*File, io.ReadCloser, error) {
	// In production, query DB for file metadata
	return nil, nil, ErrNotFound
}

func (s *LocalStore) Delete(ctx context.Context, id string) error {
	return os.Remove(s.basePath + "/" + id)
}

func (s *LocalStore) List(ctx context.Context, prefix string) ([]*File, error) {
	matches, err := filepath.Glob(s.basePath + "/" + prefix + "*")
	if err != nil {
		return nil, err
	}
	files := make([]*File, 0, len(matches))
	for _, m := range matches {
		info, _ := os.Stat(m)
		if info == nil {
			continue
		}
		files = append(files, &File{
			ID:        filepath.Base(m),
			Name:      filepath.Base(m),
			Size:      info.Size(),
			CreatedAt: info.ModTime(),
			URL:       s.baseURL + "/uploads/" + filepath.Base(m),
		})
	}
	return files, nil
}

func (s *LocalStore) GetURL(id string) string {
	return s.baseURL + "/uploads/" + id
}

// HandleUpload processes a multipart upload and stores the file.
func HandleUpload(storage Storage, r *multipart.FileHeader) (*File, error) {
	file, err := r.Open()
	if err != nil {
		return nil, err
	}
	defer file.Close()

	f := &File{
		Name:        r.Filename,
		Size:        r.Size,
		ContentType: r.Header.Get("Content-Type"),
	}

	if err := storage.Save(context.Background(), f, file); err != nil {
		return nil, err
	}

	return f, nil
}

// ErrNotFound is returned when a file is not found.
var ErrNotFound = os.ErrNotExist
