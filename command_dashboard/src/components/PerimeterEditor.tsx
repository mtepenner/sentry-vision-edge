import React, { useRef, useState, useCallback } from 'react';
import type { TripwireLine } from '../types';

interface PerimeterEditorProps {
  width?: number;
  height?: number;
  onLinesChanged?: (lines: TripwireLine[]) => void;
  initialLines?: TripwireLine[];
}

interface DrawState {
  active: boolean;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
}

let _lineCounter = 0;

function nextId(): string {
  return `line-${++_lineCounter}`;
}

/**
 * PerimeterEditor lets operators draw virtual tripwire lines on an SVG canvas.
 * Click-drag to draw a line. Click a line to remove it.
 */
export const PerimeterEditor: React.FC<PerimeterEditorProps> = ({
  width = 640,
  height = 480,
  onLinesChanged,
  initialLines = [],
}) => {
  const [lines, setLines] = useState<TripwireLine[]>(initialLines);
  const [draw, setDraw] = useState<DrawState>({
    active: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
  });
  const svgRef = useRef<SVGSVGElement>(null);

  const getSVGCoords = useCallback(
    (e: React.MouseEvent<SVGSVGElement>): { x: number; y: number } => {
      const rect = svgRef.current?.getBoundingClientRect();
      if (!rect) return { x: e.clientX, y: e.clientY };
      const scaleX = width / rect.width;
      const scaleY = height / rect.height;
      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY,
      };
    },
    [width, height]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const { x, y } = getSVGCoords(e);
      setDraw({ active: true, startX: x, startY: y, currentX: x, currentY: y });
    },
    [getSVGCoords]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!draw.active) return;
      const { x, y } = getSVGCoords(e);
      setDraw((d) => ({ ...d, currentX: x, currentY: y }));
    },
    [draw.active, getSVGCoords]
  );

  const handleMouseUp = useCallback(() => {
    if (!draw.active) return;
    const dx = draw.currentX - draw.startX;
    const dy = draw.currentY - draw.startY;
    const len = Math.sqrt(dx * dx + dy * dy);

    if (len > 10) {
      const newLine: TripwireLine = {
        id: nextId(),
        x1: draw.startX,
        y1: draw.startY,
        x2: draw.currentX,
        y2: draw.currentY,
      };
      const updated = [...lines, newLine];
      setLines(updated);
      onLinesChanged?.(updated);
    }
    setDraw((d) => ({ ...d, active: false }));
  }, [draw, lines, onLinesChanged]);

  const removeLine = useCallback(
    (id: string) => {
      const updated = lines.filter((l) => l.id !== id);
      setLines(updated);
      onLinesChanged?.(updated);
    },
    [lines, onLinesChanged]
  );

  const clearAll = useCallback(() => {
    setLines([]);
    onLinesChanged?.([]);
  }, [onLinesChanged]);

  return (
    <div className="perimeter-editor" data-testid="perimeter-editor">
      <div style={{ marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{ fontSize: 13, color: '#90cdf4', fontFamily: 'monospace' }}>
          Tripwires ({lines.length}) — click-drag to draw
        </span>
        {lines.length > 0 && (
          <button
            onClick={clearAll}
            data-testid="clear-button"
            style={{ fontSize: 11, padding: '2px 8px', cursor: 'pointer' }}
          >
            Clear All
          </button>
        )}
      </div>

      <svg
        ref={svgRef}
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{
          background: '#0d0d1a',
          border: '1px solid #2d3748',
          cursor: 'crosshair',
          display: 'block',
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        data-testid="editor-canvas"
      >
        {/* Background grid */}
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1a1a2e" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width={width} height={height} fill="url(#grid)" />

        {/* Committed lines */}
        {lines.map((line) => (
          <g key={line.id} data-testid={`tripwire-${line.id}`}>
            <line
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke="#f6ad55"
              strokeWidth={2}
              strokeDasharray="8 4"
            />
            {/* Hit-target for removal */}
            <line
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke="transparent"
              strokeWidth={12}
              style={{ cursor: 'pointer' }}
              onClick={(e) => {
                e.stopPropagation();
                removeLine(line.id);
              }}
              data-testid={`remove-${line.id}`}
            />
          </g>
        ))}

        {/* In-progress line */}
        {draw.active && (
          <line
            x1={draw.startX}
            y1={draw.startY}
            x2={draw.currentX}
            y2={draw.currentY}
            stroke="#68d391"
            strokeWidth={2}
            strokeDasharray="4 4"
            data-testid="preview-line"
          />
        )}
      </svg>
    </div>
  );
};

export default PerimeterEditor;
