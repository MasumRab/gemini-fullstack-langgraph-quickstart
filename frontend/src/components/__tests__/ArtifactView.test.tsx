import { render, screen, fireEvent } from '@testing-library/react';
import { ArtifactView } from '../ArtifactView';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// Mock clipboard API
const mockClipboard = {
  writeText: vi.fn(),
};
Object.defineProperty(navigator, 'clipboard', {
  value: mockClipboard,
  writable: true,
});

describe('ArtifactView Component', () => {
  const defaultProps = {
    content: '# Test Content',
    type: 'markdown' as const,
    title: 'Test Artifact',
    isOpen: true,
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when isOpen is false', () => {
    render(<ArtifactView {...defaultProps} isOpen={false} />);
    expect(screen.queryByText('Test Artifact')).toBeNull();
  });

  it('renders correctly when open', () => {
    render(<ArtifactView {...defaultProps} />);
    expect(screen.getByText('Test Artifact')).toBeDefined();
    expect(screen.getByText('markdown')).toBeDefined();
  });

  it('calls onClose when close button is clicked', () => {
    render(<ArtifactView {...defaultProps} />);
    // Find the close button by its icon wrapper or similar if no text/label
    const buttons = screen.getAllByRole('button');
    // The close button is the last one in the header
    const closeButton = buttons[buttons.length - 1];
    fireEvent.click(closeButton);
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('copies content to clipboard', async () => {
    render(<ArtifactView {...defaultProps} />);
    // Find copy button (first one)
    const buttons = screen.getAllByRole('button');
    const copyButton = buttons[0];

    fireEvent.click(copyButton);
    expect(mockClipboard.writeText).toHaveBeenCalledWith('# Test Content');
  });

  it('toggles maximize state', () => {
    const { container } = render(<ArtifactView {...defaultProps} />);
    // Find maximize button (middle one)
    const buttons = screen.getAllByRole('button');
    const maximizeButton = buttons[1];

    // Initial state width check (simplified)
    const rootDiv = container.firstChild as HTMLElement;
    expect(rootDiv.className).toContain('md:w-1/2');

    fireEvent.click(maximizeButton);
    expect(rootDiv.className).not.toContain('md:w-1/2');
    expect(rootDiv.className).toContain('left-0');
  });

  it('renders markdown content', () => {
    render(<ArtifactView {...defaultProps} />);
    // ReactMarkdown renders h1 for # Test Content
    expect(screen.getByRole('heading', { level: 1 })).toBeDefined();
  });

  it('has accessible buttons and hidden icons', () => {
    render(<ArtifactView {...defaultProps} />);

    // Check buttons have aria-labels
    const copyButton = screen.getByRole('button', { name: /copy content/i });
    expect(copyButton).toBeDefined();

    // Note: maximize button is hidden on small screens in the implementation (hidden md:flex),
    // but jsdom might render it. Let's check if we can find it by label.
    // The implementation: title={isMaximized ? "Restore size" : "Maximize"}
    // We expect aria-label to match title or be similar.
    const maximizeButton = screen.getByRole('button', { name: /maximize/i });
    expect(maximizeButton).toBeDefined();

    const closeButton = screen.getByRole('button', { name: /close/i });
    expect(closeButton).toBeDefined();

    // Check icons have aria-hidden="true"
    // Since we can't easily query by attribute value in testing-library without custom matchers or querying selector,
    // we can check if they are hidden from accessibility tree (which aria-hidden=true does).
    // However, they are inside buttons, so they might be implicitly present.
    // A better check is to query selector 'svg[aria-hidden="true"]'.
    const hiddenIcons = document.querySelectorAll('svg[aria-hidden="true"]');
    // We expect at least 3 icons (header icon, copy icon, maximize icon, close icon -> 4)
    // plus the ones inside the content maybe? No, just the UI ones.
    // Header icon: 1
    // Copy icon: 1
    // Maximize icon: 1
    // Close icon: 1
    // Total 4.
    expect(hiddenIcons.length).toBeGreaterThanOrEqual(4);
  });
});
