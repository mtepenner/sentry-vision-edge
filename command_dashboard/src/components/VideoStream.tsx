import React, { useRef, useEffect } from 'react';
import type { Track } from '../types';

interface VideoStreamProps {
  tracks: Track[];
  rtcPeerConnectionConfig?: RTCConfiguration;
  width?: number;
  height?: number;
}

const COLORS: Record<string, string> = {
  person: '#FF4444',
  car: '#44AAFF',
  truck: '#FFaa00',
  default: '#00FF88',
};

function labelColor(label: string): string {
  return COLORS[label] ?? COLORS.default;
}

/**
 * VideoStream renders a WebRTC video element with an SVG bounding-box overlay.
 * When no RTCPeerConnection config is provided the video element is still rendered
 * so the SVG overlay can be tested in isolation.
 */
export const VideoStream: React.FC<VideoStreamProps> = ({
  tracks,
  rtcPeerConnectionConfig,
  width = 640,
  height = 480,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);

  useEffect(() => {
    if (!rtcPeerConnectionConfig) return;

    const pc = new RTCPeerConnection(rtcPeerConnectionConfig);
    pcRef.current = pc;

    pc.ontrack = (event) => {
      if (videoRef.current && event.streams[0]) {
        videoRef.current.srcObject = event.streams[0];
      }
    };

    return () => {
      pc.close();
      pcRef.current = null;
    };
  }, [rtcPeerConnectionConfig]);

  return (
    <div
      className="video-stream"
      style={{ position: 'relative', width, height, background: '#111' }}
      data-testid="video-stream"
    >
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ width: '100%', height: '100%', display: 'block' }}
        data-testid="video-element"
      />

      <svg
        style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
        viewBox={`0 0 ${width} ${height}`}
        data-testid="bbox-overlay"
      >
        {tracks.map((track) => {
          const { x1, y1, x2, y2 } = track.bbox;
          const color = labelColor(track.label);
          const bw = x2 - x1;
          const bh = y2 - y1;
          return (
            <g key={track.id} data-testid={`track-${track.id}`}>
              <rect
                x={x1}
                y={y1}
                width={bw}
                height={bh}
                fill="none"
                stroke={color}
                strokeWidth={2}
              />
              <rect x={x1} y={y1 - 18} width={bw} height={18} fill={color} opacity={0.8} />
              <text x={x1 + 4} y={y1 - 4} fontSize={12} fill="#fff" fontFamily="monospace">
                {`#${track.id} ${track.label} ${(track.confidence * 100).toFixed(0)}%`}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export default VideoStream;
