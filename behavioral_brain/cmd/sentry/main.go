// main.go – Behavioral Brain HTTP server.
//
// Listens for track metadata POSTed by the Python Vision Engine,
// runs loitering and boundary-cross heuristics, commands the pan-tilt
// controller, and fires alerts when rules are triggered.
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/mtepenner/sentry-vision-edge/behavioral_brain/internal/alerts"
	"github.com/mtepenner/sentry-vision-edge/behavioral_brain/internal/heuristics"
	pan_tilt "github.com/mtepenner/sentry-vision-edge/behavioral_brain/internal/pan_tilt"
)

// ---------------------------------------------------------------------------
// Wire protocol – mirrors what vision_engine/app/main.py posts
// ---------------------------------------------------------------------------

type TrackEntry struct {
	ID   int       `json:"id"`
	BBox []float64 `json:"bbox"` // [x1, y1, x2, y2]
}

type TrackPayload struct {
	Timestamp float64      `json:"timestamp"`
	Tracks    []TrackEntry `json:"tracks"`
}

// ---------------------------------------------------------------------------
// WebSocket / SSE broadcast state (simple last-message store for demo)
// ---------------------------------------------------------------------------

type Server struct {
	loitering  *heuristics.LoiteringDetector
	boundary   *heuristics.BoundaryCrosser
	panTilt    *pan_tilt.PanTiltController
	notifier   *alerts.NotifyManager

	mu          sync.RWMutex
	lastPayload *TrackPayload

	frameWidth  int
	frameHeight int
	loiterZone  string
	loiterThreshold time.Duration
}

func newServer() *Server {
	loiterSec, _ := strconv.Atoi(getEnv("LOITER_THRESHOLD_SEC", "30"))
	frameW, _ := strconv.Atoi(getEnv("FRAME_WIDTH", "640"))
	frameH, _ := strconv.Atoi(getEnv("FRAME_HEIGHT", "480"))

	bc := heuristics.NewBoundaryCrosser([]heuristics.Line{
		// Default horizontal tripwire at mid-frame
		{A: heuristics.Point{X: 0, Y: float64(frameH) / 2},
			B: heuristics.Point{X: float64(frameW), Y: float64(frameH) / 2}},
	})

	notifier := alerts.NewNotifyManager(alerts.Config{
		SlackWebhookURL:  getEnv("SLACK_WEBHOOK_URL", ""),
		TelegramBotToken: getEnv("TELEGRAM_BOT_TOKEN", ""),
		TelegramChatID:   getEnv("TELEGRAM_CHAT_ID", ""),
	})

	ctrl := pan_tilt.NewPanTiltController(
		mustFloat(getEnv("PAN_GAIN", "1.0")),
		mustFloat(getEnv("TILT_GAIN", "1.0")),
		mustFloat(getEnv("DEAD_ZONE", "0.05")),
	)

	return &Server{
		loitering:       heuristics.NewLoiteringDetector(),
		boundary:        bc,
		panTilt:         ctrl,
		notifier:        notifier,
		frameWidth:      frameW,
		frameHeight:     frameH,
		loiterZone:      getEnv("LOITER_ZONE", "perimeter"),
		loiterThreshold: time.Duration(loiterSec) * time.Second,
	}
}

// ---------------------------------------------------------------------------
// HTTP handlers
// ---------------------------------------------------------------------------

func (s *Server) handleTracks(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var payload TrackPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}

	s.mu.Lock()
	s.lastPayload = &payload
	s.mu.Unlock()

	ts := time.Unix(int64(payload.Timestamp), 0)
	for _, track := range payload.Tracks {
		s.evaluateTrack(track, ts)
	}

	w.WriteHeader(http.StatusOK)
}

func (s *Server) handleLatest(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	p := s.lastPayload
	s.mu.RUnlock()

	w.Header().Set("Content-Type", "application/json")
	if p == nil {
		w.Write([]byte(`{"tracks":[]}`))
		return
	}
	json.NewEncoder(w).Encode(p)
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status":"ok"}`))
}

// ---------------------------------------------------------------------------
// Core logic
// ---------------------------------------------------------------------------

func (s *Server) evaluateTrack(track TrackEntry, ts time.Time) {
	if len(track.BBox) != 4 {
		return
	}
	bbox := pan_tilt.BoundingBox{
		X1: track.BBox[0], Y1: track.BBox[1],
		X2: track.BBox[2], Y2: track.BBox[3],
	}

	// Pan-tilt control
	pan, tilt := s.panTilt.Track(bbox, s.frameWidth, s.frameHeight)
	if pan != 0 || tilt != 0 {
		log.Printf("pan-tilt cmd: pan=%.3f tilt=%.3f (track %d)", pan, tilt, track.ID)
	}

	// Loitering check
	if s.loitering.Check(track.ID, s.loiterZone, ts, s.loiterThreshold) {
		event := alerts.AlertEvent{
			TrackID:   track.ID,
			EventType: "loitering",
			Zone:      s.loiterZone,
			Timestamp: ts,
			Message:   "Object loitering in zone",
		}
		if err := s.notifier.Send(event); err != nil {
			log.Printf("alert send error: %v", err)
		}
	}
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

func main() {
	s := newServer()

	addr := getEnv("LISTEN_ADDR", ":8080")
	mux := http.NewServeMux()
	mux.HandleFunc("/tracks", s.handleTracks)
	mux.HandleFunc("/latest", s.handleLatest)
	mux.HandleFunc("/health", s.handleHealth)

	log.Printf("Behavioral Brain listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func mustFloat(s string) float64 {
	v, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0
	}
	return v
}
