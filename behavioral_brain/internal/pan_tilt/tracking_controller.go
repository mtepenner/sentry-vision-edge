// Package pan_tilt implements motor control logic for pan-tilt platforms.
package pan_tilt

// BoundingBox represents a detected object's bounding rectangle in pixel space.
type BoundingBox struct {
	X1, Y1, X2, Y2 float64
}

// Centre returns the centre point of the bounding box.
func (b BoundingBox) Centre() (cx, cy float64) {
	cx = (b.X1 + b.X2) / 2.0
	cy = (b.Y1 + b.Y2) / 2.0
	return
}

// PanTiltController converts object-centre offsets into motor command deltas.
// A positive panDelta means "rotate right"; a positive tiltDelta means "tilt down".
type PanTiltController struct {
	// PanGain and TiltGain convert normalised offset [−1, 1] to motor steps/degrees.
	PanGain  float64
	TiltGain float64

	// DeadZone is the normalised offset magnitude below which no movement is commanded.
	DeadZone float64
}

// NewPanTiltController creates a controller with sensible defaults.
func NewPanTiltController(panGain, tiltGain, deadZone float64) *PanTiltController {
	return &PanTiltController{
		PanGain:  panGain,
		TiltGain: tiltGain,
		DeadZone: deadZone,
	}
}

// Track computes the pan and tilt motor deltas needed to centre the bounding box
// within the frame.  frameWidth and frameHeight must be > 0.
//
// Returns (panDelta, tiltDelta):
//   - panDelta  > 0 → rotate right; < 0 → rotate left
//   - tiltDelta > 0 → tilt down;    < 0 → tilt up
func (c *PanTiltController) Track(bbox BoundingBox, frameWidth, frameHeight int) (panDelta, tiltDelta float64) {
	if frameWidth <= 0 || frameHeight <= 0 {
		return 0, 0
	}

	cx, cy := bbox.Centre()

	// Normalised offset: −1 (left/top) … +1 (right/bottom)
	normX := (cx - float64(frameWidth)/2.0) / (float64(frameWidth) / 2.0)
	normY := (cy - float64(frameHeight)/2.0) / (float64(frameHeight) / 2.0)

	if abs64(normX) > c.DeadZone {
		panDelta = normX * c.PanGain
	}
	if abs64(normY) > c.DeadZone {
		tiltDelta = normY * c.TiltGain
	}
	return
}

func abs64(x float64) float64 {
	if x < 0 {
		return -x
	}
	return x
}
