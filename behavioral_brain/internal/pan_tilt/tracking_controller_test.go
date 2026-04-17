// tracking_controller_test.go
package pan_tilt

import (
	"math"
	"testing"
)

func TestTrack_CenteredBox(t *testing.T) {
	ctrl := NewPanTiltController(1.0, 1.0, 0.0)
	// Box perfectly centred in a 640×480 frame
	bbox := BoundingBox{X1: 270, Y1: 190, X2: 370, Y2: 290}
	pan, tilt := ctrl.Track(bbox, 640, 480)
	if math.Abs(pan) > 1e-9 {
		t.Errorf("expected pan ≈ 0, got %v", pan)
	}
	if math.Abs(tilt) > 1e-9 {
		t.Errorf("expected tilt ≈ 0, got %v", tilt)
	}
}

func TestTrack_ObjectOnLeft(t *testing.T) {
	ctrl := NewPanTiltController(1.0, 1.0, 0.0)
	// Centre of box at (100, 240) – left of frame centre
	bbox := BoundingBox{X1: 50, Y1: 190, X2: 150, Y2: 290}
	pan, _ := ctrl.Track(bbox, 640, 480)
	if pan >= 0 {
		t.Errorf("expected negative pan for object on left, got %v", pan)
	}
}

func TestTrack_ObjectOnRight(t *testing.T) {
	ctrl := NewPanTiltController(1.0, 1.0, 0.0)
	// Centre at (540, 240) – right of frame centre
	bbox := BoundingBox{X1: 490, Y1: 190, X2: 590, Y2: 290}
	pan, _ := ctrl.Track(bbox, 640, 480)
	if pan <= 0 {
		t.Errorf("expected positive pan for object on right, got %v", pan)
	}
}

func TestTrack_ObjectAboveCenter(t *testing.T) {
	ctrl := NewPanTiltController(1.0, 1.0, 0.0)
	// Centre at (320, 50) – above frame centre
	bbox := BoundingBox{X1: 270, Y1: 0, X2: 370, Y2: 100}
	_, tilt := ctrl.Track(bbox, 640, 480)
	if tilt >= 0 {
		t.Errorf("expected negative tilt for object above centre, got %v", tilt)
	}
}

func TestTrack_ObjectBelowCenter(t *testing.T) {
	ctrl := NewPanTiltController(1.0, 1.0, 0.0)
	// Centre at (320, 430) – below frame centre
	bbox := BoundingBox{X1: 270, Y1: 380, X2: 370, Y2: 480}
	_, tilt := ctrl.Track(bbox, 640, 480)
	if tilt <= 0 {
		t.Errorf("expected positive tilt for object below centre, got %v", tilt)
	}
}

func TestTrack_DeadZoneSuppressesSmallOffset(t *testing.T) {
	ctrl := NewPanTiltController(1.0, 1.0, 0.5)
	// Object slightly off-centre (normX ≈ 0.06) – within dead zone
	bbox := BoundingBox{X1: 300, Y1: 190, X2: 340, Y2: 290}
	pan, tilt := ctrl.Track(bbox, 640, 480)
	if pan != 0 || tilt != 0 {
		t.Errorf("expected zero deltas within dead zone, got pan=%v tilt=%v", pan, tilt)
	}
}

func TestTrack_GainScalesOutput(t *testing.T) {
	ctrl1 := NewPanTiltController(1.0, 1.0, 0.0)
	ctrl2 := NewPanTiltController(2.0, 2.0, 0.0)
	bbox := BoundingBox{X1: 0, Y1: 0, X2: 100, Y2: 100}
	pan1, _ := ctrl1.Track(bbox, 640, 480)
	pan2, _ := ctrl2.Track(bbox, 640, 480)
	if math.Abs(pan2-2*pan1) > 1e-9 {
		t.Errorf("expected gain to double pan delta: pan1=%v pan2=%v", pan1, pan2)
	}
}

func TestTrack_ZeroFrameSizeReturnsZero(t *testing.T) {
	ctrl := NewPanTiltController(1.0, 1.0, 0.0)
	pan, tilt := ctrl.Track(BoundingBox{0, 0, 100, 100}, 0, 0)
	if pan != 0 || tilt != 0 {
		t.Errorf("expected (0,0) for invalid frame size, got (%v,%v)", pan, tilt)
	}
}
