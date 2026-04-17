import { useEffect, useRef, useState, useCallback } from 'react';
import type { Track, TrackPayload } from '../types';

export interface SentryState {
  tracks: Track[];
  connected: boolean;
  lastError: string | null;
}

const DEFAULT_WS_URL = 'ws://localhost:8080/ws';

/**
 * useSentryWebsocket connects to the Go Behavioral Brain WebSocket endpoint,
 * receives TrackPayload messages, and exposes the current track state.
 */
export function useSentryWebsocket(url: string = DEFAULT_WS_URL): SentryState {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [connected, setConnected] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setLastError(null);
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const payload: TrackPayload = JSON.parse(event.data as string);
        const now = new Date().toISOString();
        const parsed: Track[] = (payload.tracks ?? []).map((t) => ({
          id: t.id,
          bbox: { x1: t.bbox[0], y1: t.bbox[1], x2: t.bbox[2], y2: t.bbox[3] },
          label: t.label ?? 'unknown',
          confidence: t.confidence ?? 0,
          lastSeen: now,
        }));
        setTracks(parsed);
      } catch {
        setLastError('Failed to parse track payload');
      }
    };

    ws.onerror = () => {
      setLastError('WebSocket error');
    };

    ws.onclose = () => {
      setConnected(false);
      // Reconnect after 3 s
      reconnectTimer.current = setTimeout(connect, 3000);
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { tracks, connected, lastError };
}
