import { render, screen } from '@testing-library/react';
import { ChatMessagesView } from './ChatMessagesView';
import { vi, describe, it, expect } from 'vitest';
import React from 'react';

// Mock child components
vi.mock('@/components/InputForm', () => ({
  InputForm: () => <div data-testid="input-form">InputForm</div>
}));

// Mock ScrollArea to forward props (CRITICAL)
vi.mock('@/components/ui/scroll-area', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ScrollArea: ({ children, className, ...props }: any) => (
    <div data-testid="scroll-area" className={className} {...props}>
      {children}
    </div>
  )
}));

vi.mock('@/components/ActivityTimeline', () => ({
  ActivityTimeline: () => <div data-testid="activity-timeline">Timeline</div>
}));

describe('ChatMessagesView Accessibility', () => {
  const defaultProps = {
    messages: [],
    isLoading: false,
    scrollAreaRef: { current: null },
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    liveActivityEvents: [],
    historicalActivities: {},
  };

  it('main scroll area has accessible role and label', () => {
    render(<ChatMessagesView {...defaultProps} />);

    // The scroll area should be identified as a log of chat history
    const scrollArea = screen.getByRole('log');
    expect(scrollArea).toBeInTheDocument();
    expect(scrollArea).toHaveAttribute('aria-label', 'Chat history');
  });
});
