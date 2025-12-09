import { render, screen, fireEvent } from '@testing-library/react';
import { ChatMessagesView } from './ChatMessagesView';
import { vi, describe, it, expect } from 'vitest';
import React from 'react';

// Mock child components to avoid dependency issues
vi.mock('@/components/InputForm', () => ({
  InputForm: ({ onSubmit }: any) => <div data-testid="input-form">InputForm</div>
}));

vi.mock('@/components/ui/scroll-area', () => ({
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

  it('does not render planning card when planningContext is null', () => {
    render(<ChatMessagesView {...defaultProps} planningContext={null} />);
    expect(screen.queryByText('Planning Mode')).not.toBeInTheDocument();
  });

  it('renders planning card when planningContext is provided', () => {
    const planningContext = {
      steps: [
        { id: '1', title: 'Step 1', query: 'q1', suggested_tool: 'web_research', status: 'pending' }
      ],
      status: 'awaiting_confirmation',
      feedback: ['Feedback message']
    };

    render(<ChatMessagesView {...defaultProps} planningContext={planningContext} />);

    expect(screen.getByText('Planning Mode')).toBeInTheDocument();
    expect(screen.getByText('1 proposed step')).toBeInTheDocument();
    expect(screen.getByText('Feedback message')).toBeInTheDocument();
    expect(screen.getByText('Step 1')).toBeInTheDocument();
    expect(screen.getByText('awaiting_confirmation')).toBeInTheDocument();
  });

  it('renders confirm button when status is awaiting_confirmation', () => {
    const planningContext = {
      steps: [],
      status: 'awaiting_confirmation',
      feedback: []
    };

    render(<ChatMessagesView {...defaultProps} planningContext={planningContext} />);

    const confirmBtn = screen.getByText('Confirm Plan');
    expect(confirmBtn).toBeInTheDocument();

    fireEvent.click(confirmBtn);
    expect(defaultProps.onSendCommand).toHaveBeenCalledWith('/confirm_plan');
  });

  it('renders enter and skip buttons', () => {
    const planningContext = {
      steps: [],
      status: 'auto_approved',
      feedback: []
    };

    render(<ChatMessagesView {...defaultProps} planningContext={planningContext} />);

    const enterBtn = screen.getByText('Enter Planning');
    const skipBtn = screen.getByText('Skip Planning');

    expect(enterBtn).toBeInTheDocument();
    expect(skipBtn).toBeInTheDocument();

    fireEvent.click(enterBtn);
    expect(defaultProps.onSendCommand).toHaveBeenCalledWith('/plan');

    fireEvent.click(skipBtn);
    expect(defaultProps.onSendCommand).toHaveBeenCalledWith('/end_plan');
  });

  it('does not render confirm button when status is not awaiting_confirmation', () => {
    const planningContext = {
      steps: [],
      status: 'auto_approved',
      feedback: []
    };

    render(<ChatMessagesView {...defaultProps} planningContext={planningContext} />);

    expect(screen.queryByText('Confirm Plan')).not.toBeInTheDocument();
  });
});
