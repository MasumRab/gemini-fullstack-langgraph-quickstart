import { render, screen } from '@testing-library/react';
import { ChatMessagesView } from './ChatMessagesView';
import { vi, describe, it, expect } from 'vitest';
import React from 'react';
import { Message } from "@langchain/langgraph-sdk";

// Mock child components
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

// We don't mock Badge because we want to test its asChild behavior
// But we might need to mock other UI components if they cause issues.
// For this test, Badge is crucial.

describe('ChatMessagesView Markdown Links', () => {
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

  it('renders links using Badge with asChild behavior', () => {
    const message: Message = {
      type: "ai",
      content: "Here is a [link](https://example.com)",
      id: "msg-1"
    };

    render(<ChatMessagesView {...defaultProps} messages={[message]} />);

    // Find the link
    const link = screen.getByText('link');

    // Check if it's an anchor tag
    expect(link.tagName).toBe('A');
    expect(link).toHaveAttribute('href', 'https://example.com');

    // Check if it has Badge classes (which indicates it's being rendered by Badge with asChild)
    // Badge default classes: inline-flex items-center ...
    expect(link.className).toContain('inline-flex');
    expect(link.className).toContain('items-center');
    expect(link.className).toContain('border'); // from Badge
    expect(link.className).toContain('text-blue-400'); // from our custom className passed to a tag
  });

  it('sanitizes javascript: links', () => {
    const message: Message = {
      type: "ai",
      content: "Here is a [bad link](javascript:alert(1))",
      id: "msg-2"
    };

    render(<ChatMessagesView {...defaultProps} messages={[message]} />);

    const link = screen.getByText('bad link');

    // It should render the text, but the href should be sanitized (removed or empty)
    // ReactMarkdown default urlTransform might remove it or make it javascript:void(0) or similar?
    // rehype-sanitize typically removes unsafe attributes.
    // Let's check if href is missing or safe.
    // If it was raw html, it would be stripped.
    // For markdown links, if protocol is bad, it might just be <a>text</a>

    // Check if href is NOT javascript:alert(1)
    expect(link).not.toHaveAttribute('href', 'javascript:alert(1)');

    // It probably has no href, or a safe one.
    // Let's print it if verification fails, but for now assert safe.
    const href = link.getAttribute('href');
    if (href) {
        expect(href).not.toMatch(/^javascript:/i);
    }
  });
});
