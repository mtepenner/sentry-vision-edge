// boundary_cross.go – Virtual tripwire detection via line-segment intersection.
package heuristics

import "math"

// Point represents a 2D pixel coordinate.
type Point struct {
	X, Y float64
}

// Line represents a directed line segment (tripwire) in pixel space.
type Line struct {
	A, B Point
}

// BoundaryCrosser checks whether a moving object crosses any registered tripwire.
type BoundaryCrosser struct {
	Lines []Line
}

// NewBoundaryCrosser creates a BoundaryCrosser with the given tripwires.
func NewBoundaryCrosser(lines []Line) *BoundaryCrosser {
	return &BoundaryCrosser{Lines: lines}
}

// Check returns true if the movement vector (prevPos → currPos) crosses any
// registered boundary line.  trackID is reserved for future per-track state.
func (bc *BoundaryCrosser) Check(_ int, prevPos, currPos Point) bool {
	for _, line := range bc.Lines {
		if segmentsIntersect(prevPos, currPos, line.A, line.B) {
			return true
		}
	}
	return false
}

// AddLine appends a new tripwire line.
func (bc *BoundaryCrosser) AddLine(line Line) {
	bc.Lines = append(bc.Lines, line)
}

// ---------------------------------------------------------------------------
// Geometry helpers
// ---------------------------------------------------------------------------

// cross2D returns the 2-D cross product of vectors (O→A) and (O→B).
func cross2D(o, a, b Point) float64 {
	return (a.X-o.X)*(b.Y-o.Y) - (a.Y-o.Y)*(b.X-o.X)
}

// onSegment returns true if point p lies on segment [a,b], assuming p is
// known to be collinear with a and b.
func onSegment(a, b, p Point) bool {
	minX := math.Min(a.X, b.X)
	maxX := math.Max(a.X, b.X)
	minY := math.Min(a.Y, b.Y)
	maxY := math.Max(a.Y, b.Y)
	return p.X >= minX && p.X <= maxX && p.Y >= minY && p.Y <= maxY
}

// segmentsIntersect returns true if segment (p1→p2) intersects segment (p3→p4).
// Uses the standard orientation-based test.
func segmentsIntersect(p1, p2, p3, p4 Point) bool {
	d1 := cross2D(p3, p4, p1)
	d2 := cross2D(p3, p4, p2)
	d3 := cross2D(p1, p2, p3)
	d4 := cross2D(p1, p2, p4)

	if ((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) &&
		((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0)) {
		return true
	}

	// Collinear cases
	if d1 == 0 && onSegment(p3, p4, p1) {
		return true
	}
	if d2 == 0 && onSegment(p3, p4, p2) {
		return true
	}
	if d3 == 0 && onSegment(p1, p2, p3) {
		return true
	}
	if d4 == 0 && onSegment(p1, p2, p4) {
		return true
	}
	return false
}
