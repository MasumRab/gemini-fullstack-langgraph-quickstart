import { render, screen } from '@testing-library/react';
import { ChatMessagesView } from './ChatMessagesView';
import { vi, describe, it, expect } from 'vitest';
import React from 'react';

// Mock child components to avoid dependency issues
vi.mock('@/components/InputForm', () => ({
  InputForm: () => <div data-testid="input-form">InputForm</div>
}));

vi.mock('@/components/ui/scroll-area', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ScrollArea: ({ children }: any) => <div data-testid="scroll-area">{children}</div>
}));

vi.mock('@/components/ActivityTimeline', () => ({
  ActivityTimeline: () => <div data-testid="activity-timeline">Timeline</div>
}));

describe('ChatMessagesView Planning Mode', () => {
  const defaultProps = {
    messages: [],
    isLoading: false,
    scrollAreaRef: { current: null },
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    liveActivityEvents: [],
    historicalActivities: {},
    onSendCommand: vi.fn(),
  };

  it('renders planning card with correct accessibility attributes', () => {
    const planningContext = {
      steps: [
        { id: '1', title: 'Step 1', query: 'q1', suggested_tool: 'web_research', status: 'pending' }
      ],
      status: 'awaiting_confirmation',
      feedback: ['Feedback message']
    };

    render(<ChatMessagesView {...defaultProps} planningContext={planningContext} />);

    // Check for region role and label
    const region = screen.getByRole('region', { name: /planning status/i });
    expect(region).toBeInTheDocument();

    // Check for aria-live on the region (or specific status part, depending on implementation)
    // We will implement it on the region for simplicity and robustness
    expect(region).toHaveAttribute('aria-live', 'polite');
  });
});
