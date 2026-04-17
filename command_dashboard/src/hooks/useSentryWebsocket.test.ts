import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSentryWebsocket } from './useSentryWebsocket';

// ---------------------------------------------------------------------------
// WebSocket mock
// ---------------------------------------------------------------------------

type WSHandler = (event: { data?: string }) => void;

class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;
  readyState: number = MockWebSocket.OPEN;
  url: string;
  onopen: WSHandler | null = null;
  onmessage: WSHandler | null = null;
  onerror: WSHandler | null = null;
  onclose: WSHandler | null = null;

  static instances: MockWebSocket[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  simulateOpen() {
    this.onopen?.({});
  }

  simulateMessage(data: string) {
    this.onmessage?.({ data });
  }

  simulateError() {
    this.onerror?.({});
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({});
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
  }
}

beforeEach(() => {
  MockWebSocket.instances = [];
  vi.stubGlobal('WebSocket', MockWebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useSentryWebsocket', () => {
  it('starts disconnected', () => {
    const { result } = renderHook(() => useSentryWebsocket('ws://test'));
    expect(result.current.connected).toBe(false);
    expect(result.current.tracks).toEqual([]);
    expect(result.current.lastError).toBeNull();
  });

  it('becomes connected after onopen fires', () => {
    const { result } = renderHook(() => useSentryWebsocket('ws://test'));
    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });
    expect(result.current.connected).toBe(true);
  });

  it('parses incoming track payload', () => {
    const { result } = renderHook(() => useSentryWebsocket('ws://test'));
    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });

    const payload = {
      timestamp: 1700000000,
      tracks: [
        { id: 1, bbox: [10, 20, 100, 200], label: 'person', confidence: 0.92 },
      ],
    };

    act(() => {
      MockWebSocket.instances[0].simulateMessage(JSON.stringify(payload));
    });

    expect(result.current.tracks).toHaveLength(1);
    expect(result.current.tracks[0].id).toBe(1);
    expect(result.current.tracks[0].label).toBe('person');
    expect(result.current.tracks[0].confidence).toBe(0.92);
    expect(result.current.tracks[0].bbox).toEqual({ x1: 10, y1: 20, x2: 100, y2: 200 });
  });

  it('sets lastError on malformed message', () => {
    const { result } = renderHook(() => useSentryWebsocket('ws://test'));
    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });
    act(() => {
      MockWebSocket.instances[0].simulateMessage('not json {{{');
    });
    expect(result.current.lastError).not.toBeNull();
  });

  it('sets lastError on WebSocket error', () => {
    const { result } = renderHook(() => useSentryWebsocket('ws://test'));
    act(() => {
      MockWebSocket.instances[0].simulateError();
    });
    expect(result.current.lastError).not.toBeNull();
  });

  it('becomes disconnected after close', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useSentryWebsocket('ws://test'));
    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });
    expect(result.current.connected).toBe(true);
    act(() => {
      MockWebSocket.instances[0].simulateClose();
    });
    expect(result.current.connected).toBe(false);
    vi.useRealTimers();
  });

  it('handles payload with missing optional fields gracefully', () => {
    const { result } = renderHook(() => useSentryWebsocket('ws://test'));
    act(() => {
      MockWebSocket.instances[0].simulateOpen();
    });
    const payload = {
      timestamp: 0,
      tracks: [{ id: 42, bbox: [0, 0, 50, 50] }],
    };
    act(() => {
      MockWebSocket.instances[0].simulateMessage(JSON.stringify(payload));
    });
    expect(result.current.tracks[0].label).toBe('unknown');
    expect(result.current.tracks[0].confidence).toBe(0);
  });
});
