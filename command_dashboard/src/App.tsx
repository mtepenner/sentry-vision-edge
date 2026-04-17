import React, { useState } from 'react';
import { VideoStream } from './components/VideoStream';
import { ThreatList } from './components/ThreatList';
import { PerimeterEditor } from './components/PerimeterEditor';
import { useSentryWebsocket } from './hooks/useSentryWebsocket';
import type { TripwireLine } from './types';

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8080/ws';

type View = 'monitor' | 'editor';

export default function App() {
  const { tracks, connected, lastError } = useSentryWebsocket(WS_URL);
  const [activeView, setActiveView] = useState<View>('monitor');
  const [tripwires, setTripwires] = useState<TripwireLine[]>([]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#0d0d1a', color: '#e0e0e0' }}>
      {/* Header */}
      <header style={{ padding: '8px 16px', background: '#111827', display: 'flex', alignItems: 'center', gap: 16 }}>
        <h1 style={{ margin: 0, fontSize: 18, fontFamily: 'monospace', color: '#90cdf4' }}>
          🛡️ Sentry Vision Edge
        </h1>
        <span
          style={{
            fontSize: 11,
            padding: '2px 8px',
            borderRadius: 3,
            background: connected ? '#22543d' : '#742a2a',
            color: connected ? '#9ae6b4' : '#feb2b2',
          }}
          data-testid="connection-status"
        >
          {connected ? 'LIVE' : 'OFFLINE'}
        </span>
        {lastError && (
          <span style={{ fontSize: 11, color: '#fc8181' }}>{lastError}</span>
        )}
        <nav style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          {(['monitor', 'editor'] as View[]).map((v) => (
            <button
              key={v}
              onClick={() => setActiveView(v)}
              style={{
                fontSize: 12,
                padding: '4px 12px',
                cursor: 'pointer',
                background: activeView === v ? '#2b6cb0' : '#2d3748',
                color: '#e2e8f0',
                border: 'none',
                borderRadius: 4,
              }}
            >
              {v === 'monitor' ? 'Monitor' : 'Perimeter Editor'}
            </button>
          ))}
        </nav>
      </header>

      {/* Main content */}
      <main style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {activeView === 'monitor' ? (
          <>
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
              <VideoStream tracks={tracks} width={640} height={480} />
            </div>
            <ThreatList tracks={tracks} />
          </>
        ) : (
          <div style={{ flex: 1, padding: 16 }}>
            <PerimeterEditor
              width={640}
              height={480}
              initialLines={tripwires}
              onLinesChanged={setTripwires}
            />
            <p style={{ fontSize: 12, color: '#718096', marginTop: 8, fontFamily: 'monospace' }}>
              {tripwires.length} tripwire(s) active. Lines are sent to the Behavioral Brain on save.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
