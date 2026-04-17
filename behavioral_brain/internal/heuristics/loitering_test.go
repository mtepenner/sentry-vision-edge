// loitering_test.go
package heuristics

import (
	"testing"
	"time"
)

func TestLoitering_FirstCallReturnsFalse(t *testing.T) {
	d := NewLoiteringDetector()
	ts := time.Now()
	if d.Check(1, "zone-A", ts, 10*time.Second) {
		t.Error("expected false on first observation")
	}
}

func TestLoitering_BelowThreshold(t *testing.T) {
	d := NewLoiteringDetector()
	base := time.Now()
	d.Check(1, "zone-A", base, 30*time.Second)
	// 5 seconds later – still below 30 s threshold
	if d.Check(1, "zone-A", base.Add(5*time.Second), 30*time.Second) {
		t.Error("expected false when below threshold")
	}
}

func TestLoitering_AboveThreshold(t *testing.T) {
	d := NewLoiteringDetector()
	base := time.Now()
	d.Check(1, "zone-A", base, 10*time.Second)
	// 15 seconds later – above 10 s threshold
	if !d.Check(1, "zone-A", base.Add(15*time.Second), 10*time.Second) {
		t.Error("expected true when above threshold")
	}
}

func TestLoitering_ExactlyAtThreshold(t *testing.T) {
	d := NewLoiteringDetector()
	base := time.Now()
	d.Check(2, "zone-B", base, 10*time.Second)
	if !d.Check(2, "zone-B", base.Add(10*time.Second), 10*time.Second) {
		t.Error("expected true when exactly at threshold")
	}
}

func TestLoitering_DifferentTracksIsolated(t *testing.T) {
	d := NewLoiteringDetector()
	base := time.Now()
	d.Check(1, "zone-A", base, 10*time.Second)
	d.Check(2, "zone-A", base.Add(5*time.Second), 10*time.Second)
	// Track 1 has been there 15 s – should trigger
	if !d.Check(1, "zone-A", base.Add(15*time.Second), 10*time.Second) {
		t.Error("track 1 should trigger")
	}
	// Track 2 has been there 10 s – exactly at threshold
	if !d.Check(2, "zone-A", base.Add(15*time.Second), 10*time.Second) {
		t.Error("track 2 should trigger")
	}
}

func TestLoitering_Reset(t *testing.T) {
	d := NewLoiteringDetector()
	base := time.Now()
	d.Check(1, "zone-A", base, 5*time.Second)
	d.Reset(1, "zone-A")
	// After reset the clock should start fresh
	if d.Check(1, "zone-A", base.Add(10*time.Second), 5*time.Second) {
		t.Error("after reset, first call should return false")
	}
}

func TestLoitering_ResetAll(t *testing.T) {
	d := NewLoiteringDetector()
	base := time.Now()
	d.Check(1, "zone-A", base, 5*time.Second)
	d.Check(2, "zone-B", base, 5*time.Second)
	d.ResetAll()
	if d.Check(1, "zone-A", base.Add(10*time.Second), 5*time.Second) {
		t.Error("after ResetAll, track 1 should be cleared")
	}
	if d.Check(2, "zone-B", base.Add(10*time.Second), 5*time.Second) {
		t.Error("after ResetAll, track 2 should be cleared")
	}
}

func TestLoitering_DifferentZonesSameTrack(t *testing.T) {
	d := NewLoiteringDetector()
	base := time.Now()
	d.Check(1, "zone-A", base, 10*time.Second)
	// Different zone – independent timer
	if d.Check(1, "zone-B", base.Add(15*time.Second), 10*time.Second) {
		t.Error("zone-B has not been entered yet, should return false on first call")
	}
}
