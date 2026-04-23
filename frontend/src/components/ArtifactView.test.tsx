import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ArtifactView } from './ArtifactView';

describe('ArtifactView', () => {
  const defaultProps = {
    content: '# Test Content',
    type: 'markdown' as const,
    isOpen: true,
    onClose: vi.fn(),
  };

  it('renders buttons with accessible labels', () => {
    render(<ArtifactView {...defaultProps} />);

    // Check for Copy button
    expect(screen.getByLabelText('Copy content')).toBeInTheDocument();

    // Check for Maximize button (initially "Maximize")
    expect(screen.getByLabelText('Maximize')).toBeInTheDocument();

    // Check for Close button
    expect(screen.getByLabelText('Close')).toBeInTheDocument();
  });

  it('updates label when maximized', () => {
    render(<ArtifactView {...defaultProps} />);

    const maximizeButton = screen.getByLabelText('Maximize');
    fireEvent.click(maximizeButton);

    expect(screen.getByLabelText('Restore size')).toBeInTheDocument();
  });

  it('hides decorative icons from screen readers', () => {
    render(<ArtifactView {...defaultProps} />);

    // Helper to check if an icon has aria-hidden="true"
    const checkIconHidden = (container: HTMLElement) => {
      const svg = container.querySelector('svg');
      expect(svg).toHaveAttribute('aria-hidden', 'true');
    };

    // Check Close button icon
    const closeBtn = screen.getByLabelText('Close');
    checkIconHidden(closeBtn);

    // Check Copy button icon
    const copyBtn = screen.getByLabelText('Copy content');
    checkIconHidden(copyBtn);

    // Check Maximize button icon
    const maxBtn = screen.getByLabelText('Maximize');
    checkIconHidden(maxBtn);
  });
});
