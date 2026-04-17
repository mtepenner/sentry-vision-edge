import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThreatList } from './ThreatList';
import type { Track } from '../types';

const makeTrack = (id: number, label = 'person', confidence = 0.9): Track => ({
  id,
  bbox: { x1: 10, y1: 10, x2: 100, y2: 200 },
  label,
  confidence,
  lastSeen: new Date().toISOString(),
});

describe('ThreatList', () => {
  it('renders the sidebar', () => {
    render(<ThreatList tracks={[]} />);
    expect(screen.getByTestId('threat-list')).toBeInTheDocument();
  });

  it('shows "no threats" message when empty', () => {
    render(<ThreatList tracks={[]} />);
    expect(screen.getByTestId('no-threats')).toBeInTheDocument();
  });

  it('renders one item per track', () => {
    const tracks = [makeTrack(1), makeTrack(2)];
    render(<ThreatList tracks={tracks} />);
    expect(screen.getByTestId('threat-item-1')).toBeInTheDocument();
    expect(screen.getByTestId('threat-item-2')).toBeInTheDocument();
  });

  it('displays track id and label', () => {
    render(<ThreatList tracks={[makeTrack(5, 'truck', 0.78)]} />);
    expect(screen.getByTestId('threat-item-5').textContent).toContain('#5');
    expect(screen.getByTestId('threat-item-5').textContent).toContain('truck');
  });

  it('displays confidence as percentage', () => {
    render(<ThreatList tracks={[makeTrack(3, 'person', 0.65)]} />);
    expect(screen.getByTestId('confidence-3').textContent).toBe('65%');
  });

  it('sorts tracks by confidence descending', () => {
    const tracks = [makeTrack(1, 'person', 0.5), makeTrack(2, 'car', 0.9), makeTrack(3, 'truck', 0.7)];
    render(<ThreatList tracks={tracks} />);
    const items = screen.getAllByTestId(/^threat-item-/);
    // Highest confidence first
    expect(items[0].getAttribute('data-testid')).toBe('threat-item-2');
    expect(items[1].getAttribute('data-testid')).toBe('threat-item-3');
    expect(items[2].getAttribute('data-testid')).toBe('threat-item-1');
  });

  it('calls onSelectTrack when an item is clicked', () => {
    const handler = vi.fn();
    render(<ThreatList tracks={[makeTrack(9, 'person', 0.9)]} onSelectTrack={handler} />);
    fireEvent.click(screen.getByTestId('threat-item-9'));
    expect(handler).toHaveBeenCalledWith(9);
  });

  it('shows count in heading', () => {
    const tracks = [makeTrack(1), makeTrack(2), makeTrack(3)];
    render(<ThreatList tracks={tracks} />);
    expect(screen.getByRole('heading').textContent).toContain('3');
  });
});
