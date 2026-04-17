import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PerimeterEditor } from './PerimeterEditor';
import type { TripwireLine } from '../types';

// Helper: simulate a drag on the SVG canvas
function drag(
  canvas: Element,
  from: { clientX: number; clientY: number },
  to: { clientX: number; clientY: number }
) {
  // Mock getBoundingClientRect to return a fixed rect
  vi.spyOn(canvas, 'getBoundingClientRect').mockReturnValue({
    left: 0, top: 0, right: 640, bottom: 480,
    width: 640, height: 480, x: 0, y: 0,
    toJSON: () => ({}),
  } as DOMRect);

  fireEvent.mouseDown(canvas, from);
  fireEvent.mouseMove(canvas, to);
  fireEvent.mouseUp(canvas, to);
}

describe('PerimeterEditor', () => {
  it('renders the editor container', () => {
    render(<PerimeterEditor />);
    expect(screen.getByTestId('perimeter-editor')).toBeInTheDocument();
  });

  it('renders the SVG canvas', () => {
    render(<PerimeterEditor />);
    expect(screen.getByTestId('editor-canvas')).toBeInTheDocument();
  });

  it('starts with no tripwires', () => {
    render(<PerimeterEditor />);
    expect(screen.queryByTestId(/^tripwire-/)).toBeNull();
  });

  it('renders initialLines as tripwires', () => {
    const lines: TripwireLine[] = [
      { id: 'line-init-1', x1: 0, y1: 100, x2: 640, y2: 100 },
    ];
    render(<PerimeterEditor initialLines={lines} />);
    expect(screen.getByTestId('tripwire-line-init-1')).toBeInTheDocument();
  });

  it('draws a new line on drag', () => {
    const onChange = vi.fn();
    render(<PerimeterEditor onLinesChanged={onChange} />);
    const canvas = screen.getByTestId('editor-canvas');

    drag(canvas, { clientX: 50, clientY: 50 }, { clientX: 300, clientY: 300 });

    expect(onChange).toHaveBeenCalledOnce();
    const [lines] = onChange.mock.calls[0];
    expect(lines).toHaveLength(1);
  });

  it('does not draw a line for very short drags (< 10px)', () => {
    const onChange = vi.fn();
    render(<PerimeterEditor onLinesChanged={onChange} />);
    const canvas = screen.getByTestId('editor-canvas');

    drag(canvas, { clientX: 100, clientY: 100 }, { clientX: 104, clientY: 104 });
    expect(onChange).not.toHaveBeenCalled();
  });

  it('shows clear button when lines exist', () => {
    const lines: TripwireLine[] = [
      { id: 'line-a', x1: 0, y1: 0, x2: 200, y2: 200 },
    ];
    render(<PerimeterEditor initialLines={lines} />);
    expect(screen.getByTestId('clear-button')).toBeInTheDocument();
  });

  it('clears all lines when clear button clicked', () => {
    const onChange = vi.fn();
    const lines: TripwireLine[] = [
      { id: 'line-a', x1: 0, y1: 0, x2: 200, y2: 200 },
    ];
    render(<PerimeterEditor initialLines={lines} onLinesChanged={onChange} />);
    fireEvent.click(screen.getByTestId('clear-button'));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it('removes a line when its remove target is clicked', () => {
    const onChange = vi.fn();
    const lines: TripwireLine[] = [
      { id: 'line-rm', x1: 10, y1: 10, x2: 200, y2: 200 },
    ];
    render(<PerimeterEditor initialLines={lines} onLinesChanged={onChange} />);
    fireEvent.click(screen.getByTestId('remove-line-rm'));
    expect(onChange).toHaveBeenCalledWith([]);
  });
});
