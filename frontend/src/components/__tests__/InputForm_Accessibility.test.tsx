import { render, screen, fireEvent } from '@testing-library/react';
import { InputForm } from '../InputForm';
import { vi, describe, it, expect } from 'vitest';
import userEvent from '@testing-library/user-event';
import React from 'react';

// Mock components to simplify testing
vi.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
}));

vi.mock('@/components/ui/textarea', () => ({
  Textarea: (props: any) => <textarea {...props} />,
}));

vi.mock('@/components/ui/select', () => ({
  Select: ({ children, onValueChange, value }: any) => (
    <div data-testid="select" data-value={value} onClick={() => onValueChange && onValueChange('new-value')}>
      {children}
    </div>
  ),
  SelectTrigger: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => <div data-value={value}>{children}</div>,
  SelectValue: () => <span>Value</span>,
}));

describe('InputForm Accessibility', () => {
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  const defaultProps = {
    onSubmit: mockOnSubmit,
    onCancel: mockOnCancel,
    isLoading: false,
    hasHistory: true,
  };

  it('renders "New Search" button with correct accessibility attributes', () => {
    render(<InputForm {...defaultProps} />);

    // Find "New Search" button by its visible text first to confirm it exists
    const newSearchButton = screen.getByText('New Search').closest('button');
    expect(newSearchButton).toBeInTheDocument();

    // Check for type="button" to prevent form submission
    expect(newSearchButton).toHaveAttribute('type', 'button');

    // Check for aria-label
    expect(newSearchButton).toHaveAttribute('aria-label', 'Start new search');

    // Check for title
    expect(newSearchButton).toHaveAttribute('title', 'Start new search');
  });

  it('renders Submit button with correct accessibility attributes', () => {
    render(<InputForm {...defaultProps} />);

    const submitButton = screen.getByText('Search').closest('button');
    expect(submitButton).toBeInTheDocument();

    // Check for aria-label
    expect(submitButton).toHaveAttribute('aria-label', 'Send search query');
  });

  it('renders Stop generating button with correct accessibility attributes when loading', () => {
    render(<InputForm {...defaultProps} isLoading={true} />);

    const stopButton = screen.getByLabelText('Stop generating');
    expect(stopButton).toBeInTheDocument();
    expect(stopButton).toHaveAttribute('type', 'button');
  });
});
