// boundary_cross_test.go
package heuristics

import (
	"testing"
)

func TestBoundaryCross_NoCross(t *testing.T) {
	bc := NewBoundaryCrosser([]Line{
		{A: Point{0, 100}, B: Point{640, 100}},
	})
	// Movement entirely above the tripwire
	if bc.Check(1, Point{100, 50}, Point{200, 50}) {
		t.Error("expected no crossing when moving above the line")
	}
}

func TestBoundaryCross_CrossesLine(t *testing.T) {
	bc := NewBoundaryCrosser([]Line{
		{A: Point{0, 100}, B: Point{640, 100}},
	})
	// Moves from y=50 (above) to y=150 (below) – crosses the horizontal tripwire at y=100
	if !bc.Check(1, Point{200, 50}, Point{200, 150}) {
		t.Error("expected crossing detected")
	}
}

func TestBoundaryCross_CrossesVerticalLine(t *testing.T) {
	bc := NewBoundaryCrosser([]Line{
		{A: Point{320, 0}, B: Point{320, 480}},
	})
	// Moves from x=100 to x=400 – crosses the vertical tripwire at x=320
	if !bc.Check(2, Point{100, 240}, Point{400, 240}) {
		t.Error("expected vertical crossing detected")
	}
}

func TestBoundaryCross_DiagonalCross(t *testing.T) {
	bc := NewBoundaryCrosser([]Line{
		{A: Point{0, 0}, B: Point{100, 100}},
	})
	// Movement vector (0,100)→(100,0) intersects diagonal (0,0)→(100,100)
	if !bc.Check(3, Point{0, 100}, Point{100, 0}) {
		t.Error("expected diagonal crossing")
	}
}

func TestBoundaryCross_NoLines(t *testing.T) {
	bc := NewBoundaryCrosser(nil)
	if bc.Check(1, Point{0, 0}, Point{100, 100}) {
		t.Error("expected no crossing with no lines")
	}
}

func TestBoundaryCross_MultipleLines_OnlyCrossOne(t *testing.T) {
	bc := NewBoundaryCrosser([]Line{
		{A: Point{0, 100}, B: Point{640, 100}},
		{A: Point{0, 300}, B: Point{640, 300}},
	})
	// Only crosses the first line (y=100)
	if !bc.Check(1, Point{100, 50}, Point{100, 150}) {
		t.Error("expected crossing of first line")
	}
}

func TestBoundaryCross_AddLine(t *testing.T) {
	bc := NewBoundaryCrosser(nil)
	bc.AddLine(Line{A: Point{0, 200}, B: Point{640, 200}})
	if !bc.Check(1, Point{100, 100}, Point{100, 300}) {
		t.Error("expected crossing after AddLine")
	}
}

func TestBoundaryCross_ParallelNoIntersect(t *testing.T) {
	bc := NewBoundaryCrosser([]Line{
		{A: Point{0, 100}, B: Point{100, 100}},
	})
	// Parallel movement along y=200 – never crosses y=100
	if bc.Check(1, Point{0, 200}, Point{100, 200}) {
		t.Error("expected no crossing for parallel movement")
	}
}

func TestBoundaryCross_EndpointTouches(t *testing.T) {
	bc := NewBoundaryCrosser([]Line{
		{A: Point{0, 0}, B: Point{100, 0}},
	})
	// Movement ends exactly on the line
	if !bc.Check(1, Point{50, -10}, Point{50, 0}) {
		t.Error("expected crossing when endpoint is on the line")
	}
}
