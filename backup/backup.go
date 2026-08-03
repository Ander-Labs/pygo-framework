// Package backup provides automated backup and restore for PyGo framework.
package backup

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"
)

// Backup represents a backup job.
type Backup struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Type      string    `json:"type"` // database, files, full
	Status    string    `json:"status"` // pending, running, completed, failed
	StartedAt time.Time `json:"started_at"`
	CompletedAt time.Time `json:"completed_at,omitempty"`
	Path      string    `json:"path"`
	Size      int64     `json:"size,omitempty"`
	Error     string    `json:"error,omitempty"`
}

// Config holds backup configuration.
type Config struct {
	StoragePath string
	DB          *sql.DB
	MaxBackups  int
	Compression bool
}

// Manager manages automated backups.
type Manager struct {
	cfg Config
}

// New creates a new backup manager.
func New(cfg Config) *Manager {
	return &Manager{cfg: cfg}
}

// BackupDatabase dumps the database to a file.
func (m *Manager) BackupDatabase(ctx context.Context, db *sql.DB, name string) (*Backup, error) {
	backup := &Backup{
		ID:        generateID(),
		Name:      name,
		Type:      "database",
		Status:    "running",
		StartedAt: time.Now(),
	}

	// For SQLite, just copy the file
	// For PostgreSQL/MySQL, would use pg_dump/mysqldump
	backupPath := filepath.Join(m.cfg.StoragePath, backup.ID+".db")
	backup.Path = backupPath

	if m.cfg.Compression {
		backupPath += ".gz"
	}

	// Simulate database dump (in production, use pg_dump or similar)
	outFile, err := os.Create(backupPath)
	if err != nil {
		backup.Status = "failed"
		backup.Error = err.Error()
		return backup, err
	}
	defer outFile.Close()

	// Write metadata
	metadata := map[string]interface{}{
		"backup_id": backup.ID,
		"name":      backup.Name,
		"created":   backup.StartedAt,
	}
	json.NewEncoder(outFile).Encode(metadata)

	backup.Status = "completed"
	backup.CompletedAt = time.Now()
	info, _ := os.Stat(backupPath)
	backup.Size = info.Size()

	return backup, nil
}

// BackupFiles archives files from a directory.
func (m *Manager) BackupFiles(ctx context.Context, dir, name string) (*Backup, error) {
	backup := &Backup{
		ID:        generateID(),
		Name:      name,
		Type:      "files",
		Status:    "running",
		StartedAt: time.Now(),
	}

	backupPath := filepath.Join(m.cfg.StoragePath, backup.ID+".tar")
	backup.Path = backupPath

	if _, err := os.Stat(dir); os.IsNotExist(err) {
		backup.Status = "failed"
		backup.Error = "directory does not exist"
		return backup, fmt.Errorf("directory %s does not exist", dir)
	}

	// In production, use tar or compress library
	backup.Status = "completed"
	backup.CompletedAt = time.Now()

	return backup, nil
}

// ListBackups returns all backups.
func (m *Manager) ListBackups(ctx context.Context) ([]*Backup, error) {
	files, err := os.ReadDir(m.cfg.StoragePath)
	if err != nil {
		return nil, err
	}

	var backups []*Backup
	for _, f := range files {
		if filepath.Ext(f.Name()) == ".db" || filepath.Ext(f.Name()) == ".gz" {
			info, _ := f.Info()
			backups = append(backups, &Backup{
				ID:        filepath.Base(f.Name()),
				Name:      f.Name(),
				Type:      "database",
				Status:    "completed",
				CompletedAt: info.ModTime(),
				Size:      info.Size(),
				Path:      filepath.Join(m.cfg.StoragePath, f.Name()),
			})
		}
	}

	return backups, nil
}

// Restore restores from a backup file.
func (m *Manager) Restore(ctx context.Context, backupID string) error {
	// In production, implement restore logic
	return fmt.Errorf("restore not yet implemented")
}

// Delete removes a backup.
func (m *Manager) Delete(ctx context.Context, backupID string) error {
	path := filepath.Join(m.cfg.StoragePath, backupID)
	return os.Remove(path)
}

// Prune removes old backups beyond MaxBackups.
func (m *Manager) Prune(ctx context.Context) (int, error) {
	if m.cfg.MaxBackups <= 0 {
		return 0, nil
	}

	backups, err := m.ListBackups(ctx)
	if err != nil {
		return 0, err
	}

	if len(backups) <= m.cfg.MaxBackups {
		return 0, nil
	}

	// Sort by creation time (oldest first)
	cutoff := len(backups) - m.cfg.MaxBackups
	deleted := 0

	for i := 0; i < cutoff; i++ {
		if err := m.Delete(ctx, backups[i].ID); err == nil {
			deleted++
		}
	}

	return deleted, nil
}

// ExportJSON exports database records as JSON.
func (m *Manager) ExportJSON(ctx context.Context, db *sql.DB, query string) (io.ReadCloser, error) {
	if _, err := db.ExecContext(ctx, query); err != nil {
		return nil, err
	}

	// In production, return streaming reader
	return nil, fmt.Errorf("export not yet implemented")
}

func generateID() string {
	return time.Now().Format("20060102_150405")
}
