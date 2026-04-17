// Package heuristics implements behavioural detection logic.
// loitering.go detects when a tracked object stays in a zone too long.
package heuristics

import (
	"sync"
	"time"
)

// LoiteringDetector tracks first-seen timestamps per (trackID, zone) pair
// and reports whether the dwell time exceeds a configurable threshold.
type LoiteringDetector struct {
	mu       sync.Mutex
	firstSeen map[loiterKey]time.Time
}

type loiterKey struct {
	TrackID int
	Zone    string
}

// NewLoiteringDetector creates a ready-to-use LoiteringDetector.
func NewLoiteringDetector() *LoiteringDetector {
	return &LoiteringDetector{
		firstSeen: make(map[loiterKey]time.Time),
	}
}

// Check returns true if trackID has been in zone for longer than threshold.
// It records the first-seen time on the initial call and compares on subsequent calls.
func (d *LoiteringDetector) Check(trackID int, zone string, timestamp time.Time, threshold time.Duration) bool {
	d.mu.Lock()
	defer d.mu.Unlock()

	key := loiterKey{TrackID: trackID, Zone: zone}
	if first, ok := d.firstSeen[key]; ok {
		return timestamp.Sub(first) >= threshold
	}
	d.firstSeen[key] = timestamp
	return false
}

// Reset clears the first-seen record for a specific track+zone pair.
// Call this when an object leaves a zone.
func (d *LoiteringDetector) Reset(trackID int, zone string) {
	d.mu.Lock()
	defer d.mu.Unlock()
	delete(d.firstSeen, loiterKey{TrackID: trackID, Zone: zone})
}

// ResetAll clears all records.
func (d *LoiteringDetector) ResetAll() {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.firstSeen = make(map[loiterKey]time.Time)
}
