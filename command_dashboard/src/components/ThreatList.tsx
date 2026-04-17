import React from 'react';
import type { Track } from '../types';

interface ThreatListProps {
  tracks: Track[];
  onSelectTrack?: (trackId: number) => void;
}

function confidenceBadgeColor(conf: number): string {
  if (conf >= 0.75) return '#e53e3e';
  if (conf >= 0.5) return '#dd6b20';
  return '#d69e2e';
}

/**
 * ThreatList displays active tracks in a sidebar.
 * Tracks are sorted by confidence (descending).
 */
export const ThreatList: React.FC<ThreatListProps> = ({ tracks, onSelectTrack }) => {
  const sorted = [...tracks].sort((a, b) => b.confidence - a.confidence);

  return (
    <aside
      className="threat-list"
      style={{
        width: 260,
        background: '#1a1a2e',
        color: '#e0e0e0',
        padding: 12,
        overflowY: 'auto',
        fontFamily: 'monospace',
      }}
      data-testid="threat-list"
    >
      <h2 style={{ margin: '0 0 12px', fontSize: 14, color: '#90cdf4', textTransform: 'uppercase' }}>
        Active Threats ({tracks.length})
      </h2>

      {sorted.length === 0 ? (
        <p style={{ color: '#718096', fontSize: 12 }} data-testid="no-threats">
          No active threats
        </p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {sorted.map((track) => (
            <li
              key={track.id}
              data-testid={`threat-item-${track.id}`}
              onClick={() => onSelectTrack?.(track.id)}
              style={{
                padding: '8px 10px',
                marginBottom: 6,
                borderRadius: 4,
                background: '#16213e',
                cursor: onSelectTrack ? 'pointer' : 'default',
                borderLeft: `4px solid ${confidenceBadgeColor(track.confidence)}`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 'bold', fontSize: 13 }}>
                  #{track.id} {track.label}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    background: confidenceBadgeColor(track.confidence),
                    color: '#fff',
                    padding: '1px 6px',
                    borderRadius: 3,
                  }}
                  data-testid={`confidence-${track.id}`}
                >
                  {(track.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div style={{ fontSize: 10, color: '#718096', marginTop: 3 }}>
                Last seen: {new Date(track.lastSeen).toLocaleTimeString()}
              </div>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
};

export default ThreatList;
