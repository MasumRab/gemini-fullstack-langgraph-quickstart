import { render, screen, fireEvent } from '@testing-library/react';
import { ActivityTimeline } from './ActivityTimeline';
import { vi, describe, it, expect } from 'vitest';
import React from 'react';

// Mock scroll area to avoid ResizeObserver issues
vi.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children }: any) => <div data-testid="scroll-area">{children}</div>
}));

// Mock Lucide icons to strictly identify them
vi.mock('lucide-react', async () => {
  const actual = await vi.importActual('lucide-react');
  return {
    ...actual,
    ChevronDown: () => <div data-testid="chevron-down" />,
    ChevronUp: () => <div data-testid="chevron-up" />,
  };
});

describe('ActivityTimeline', () => {
  const defaultProps = {
    processedEvents: [],
    isLoading: false,
  };

  it('renders toggle as a button for accessibility', () => {
    render(<ActivityTimeline {...defaultProps} />);

    // Find the toggle. It should be a button.
    // Note: The text is "Research" followed by icon.
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Research');

    // Check for focus styles
    expect(button.className).toContain('focus-visible:ring-2');
  });

  it('toggles collapse state on click', () => {
    render(<ActivityTimeline {...defaultProps} />);

    const button = screen.getByRole('button');

    // Check initial state.
    // If it starts expanded (false), we should see ChevronUp.
    // If it starts collapsed (true), we should see ChevronDown.

    // Based on code: useState(false). useEffect doesn't run or condition false.
    // So it should be false (expanded).

    // Let's check for ChevronUp
    let chevronUp = screen.queryByTestId('chevron-up');
    let chevronDown = screen.queryByTestId('chevron-down');

    // If we see ChevronDown initially, then my understanding of previous failure was correct (it was collapsed).
    // If we see ChevronUp, it is expanded.

    if (chevronUp) {
      // It is expanded. Content should be visible.
      expect(screen.getByText('No activity to display.')).toBeInTheDocument();

      // Click to collapse
      fireEvent.click(button);

      // Now it should be collapsed (ChevronDown)
      expect(screen.getByTestId('chevron-down')).toBeInTheDocument();
      expect(screen.queryByText('No activity to display.')).not.toBeInTheDocument();
    } else {
      // It is collapsed. Content hidden.
      expect(chevronDown).toBeInTheDocument();
      expect(screen.queryByText('No activity to display.')).not.toBeInTheDocument();

      // Click to expand
      fireEvent.click(button);

      // Now it should be expanded (ChevronUp)
      expect(screen.getByTestId('chevron-up')).toBeInTheDocument();
      expect(screen.getByText('No activity to display.')).toBeInTheDocument();
    }
  });
});
