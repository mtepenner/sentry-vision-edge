/** Shared types for the Sentry dashboard. */

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface Track {
  id: number;
  bbox: BoundingBox;
  label: string;
  confidence: number;
  /** ISO timestamp of last update */
  lastSeen: string;
}

export interface TrackPayload {
  timestamp: number;
  tracks: Array<{
    id: number;
    bbox: [number, number, number, number];
    label?: string;
    confidence?: number;
  }>;
}

export interface TripwireLine {
  id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}
