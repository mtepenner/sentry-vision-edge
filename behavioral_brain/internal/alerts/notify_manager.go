// Package alerts manages outbound notifications (Slack, Telegram, local log).
package alerts

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"
)

// AlertEvent carries information about a detected security event.
type AlertEvent struct {
	TrackID    int       `json:"track_id"`
	EventType  string    `json:"event_type"`  // e.g. "loitering", "boundary_cross"
	Zone       string    `json:"zone"`
	Confidence float64   `json:"confidence"`
	Timestamp  time.Time `json:"timestamp"`
	Message    string    `json:"message"`
}

// NotifyManager sends alert events to all configured channels.
type NotifyManager struct {
	slackWebhookURL string
	telegramBotToken string
	telegramChatID   string
	logWriter        io.Writer
	httpClient       *http.Client
}

// Config holds optional channel credentials.
type Config struct {
	SlackWebhookURL  string
	TelegramBotToken string
	TelegramChatID   string
	LogWriter        io.Writer // defaults to os.Stdout
	HTTPClient       *http.Client
}

// NewNotifyManager creates a NotifyManager from the provided config.
func NewNotifyManager(cfg Config) *NotifyManager {
	w := cfg.LogWriter
	if w == nil {
		w = os.Stdout
	}
	client := cfg.HTTPClient
	if client == nil {
		client = &http.Client{Timeout: 5 * time.Second}
	}
	return &NotifyManager{
		slackWebhookURL:  cfg.SlackWebhookURL,
		telegramBotToken: cfg.TelegramBotToken,
		telegramChatID:   cfg.TelegramChatID,
		logWriter:        w,
		httpClient:       client,
	}
}

// Send dispatches the event to all configured channels.
// Returns the first error encountered, but continues sending to remaining channels.
func (nm *NotifyManager) Send(event AlertEvent) error {
	var firstErr error

	// Always write to local log
	nm.logAlert(event)

	if nm.slackWebhookURL != "" {
		if err := nm.sendSlack(event); err != nil {
			log.Printf("[alerts] slack error: %v", err)
			if firstErr == nil {
				firstErr = err
			}
		}
	}

	if nm.telegramBotToken != "" && nm.telegramChatID != "" {
		if err := nm.sendTelegram(event); err != nil {
			log.Printf("[alerts] telegram error: %v", err)
			if firstErr == nil {
				firstErr = err
			}
		}
	}

	return firstErr
}

// ---------------------------------------------------------------------------
// Internal senders
// ---------------------------------------------------------------------------

func (nm *NotifyManager) logAlert(event AlertEvent) {
	msg := fmt.Sprintf(
		"[ALERT] type=%s track=%d zone=%s conf=%.2f ts=%s msg=%s\n",
		event.EventType, event.TrackID, event.Zone,
		event.Confidence, event.Timestamp.Format(time.RFC3339), event.Message,
	)
	fmt.Fprint(nm.logWriter, msg)
}

func (nm *NotifyManager) sendSlack(event AlertEvent) error {
	payload := map[string]string{
		"text": fmt.Sprintf(
			":rotating_light: *%s* | Track %d | Zone: %s | Conf: %.0f%% | %s",
			event.EventType, event.TrackID, event.Zone,
			event.Confidence*100, event.Message,
		),
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	resp, err := nm.httpClient.Post(nm.slackWebhookURL, "application/json", bytes.NewReader(body))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("slack webhook returned %d", resp.StatusCode)
	}
	return nil
}

func (nm *NotifyManager) sendTelegram(event AlertEvent) error {
	text := fmt.Sprintf(
		"🚨 *%s*\nTrack: %d | Zone: %s\nConf: %.0f%%\n%s",
		event.EventType, event.TrackID, event.Zone,
		event.Confidence*100, event.Message,
	)
	apiURL := fmt.Sprintf(
		"https://api.telegram.org/bot%s/sendMessage", nm.telegramBotToken,
	)
	payload := map[string]string{
		"chat_id":    nm.telegramChatID,
		"text":       text,
		"parse_mode": "Markdown",
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	resp, err := nm.httpClient.Post(apiURL, "application/json", bytes.NewReader(body))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("telegram API returned %d", resp.StatusCode)
	}
	return nil
}
