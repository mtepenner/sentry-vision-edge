import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VideoStream } from './VideoStream';
import type { Track } from '../types';

const makeTrack = (id: number, label = 'person', confidence = 0.9): Track => ({
  id,
  bbox: { x1: 100, y1: 100, x2: 200, y2: 250 },
  label,
  confidence,
  lastSeen: new Date().toISOString(),
});

describe('VideoStream', () => {
  it('renders the container element', () => {
    render(<VideoStream tracks={[]} />);
    expect(screen.getByTestId('video-stream')).toBeInTheDocument();
  });

  it('renders the video element', () => {
    render(<VideoStream tracks={[]} />);
    expect(screen.getByTestId('video-element')).toBeInTheDocument();
  });

  it('renders the SVG overlay', () => {
    render(<VideoStream tracks={[]} />);
    expect(screen.getByTestId('bbox-overlay')).toBeInTheDocument();
  });

  it('renders no bounding boxes when tracks is empty', () => {
    render(<VideoStream tracks={[]} />);
    expect(screen.queryByTestId(/^track-/)).toBeNull();
  });

  it('renders one bounding box per track', () => {
    const tracks = [makeTrack(1), makeTrack(2), makeTrack(3)];
    render(<VideoStream tracks={tracks} />);
    expect(screen.getByTestId('track-1')).toBeInTheDocument();
    expect(screen.getByTestId('track-2')).toBeInTheDocument();
    expect(screen.getByTestId('track-3')).toBeInTheDocument();
  });

  it('displays track id and label in overlay text', () => {
    const tracks = [makeTrack(7, 'car', 0.82)];
    render(<VideoStream tracks={tracks} />);
    const overlay = screen.getByTestId('bbox-overlay');
    expect(overlay.textContent).toContain('#7');
    expect(overlay.textContent).toContain('car');
    expect(overlay.textContent).toContain('82%');
  });

  it('accepts custom width and height', () => {
    const { container } = render(<VideoStream tracks={[]} width={1280} height={720} />);
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('viewBox')).toBe('0 0 1280 720');
  });
});
