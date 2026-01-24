import { render, screen } from '@testing-library/react';
import { ChatMessagesView } from '@/components/ChatMessagesView';
import { describe, it, expect, vi } from 'vitest';
import type { Message } from '@langchain/langgraph-sdk';

// Mocks
vi.mock('@/components/ui/scroll-area', () => ({
    ScrollArea: ({ children, className, role, 'aria-label': ariaLabel }: any) => (
        <div className={className} role={role} aria-label={ariaLabel}>{children}</div>
    ),
}));

vi.mock('@/components/InputForm', () => ({
    InputForm: () => <div data-testid="input-form">InputForm</div>,
}));

vi.mock('@/components/ActivityTimeline', () => ({
    ActivityTimeline: () => <div data-testid="activity-timeline">ActivityTimeline</div>,
}));

vi.mock('@/components/ui/button', () => ({
    Button: ({ children, onClick, className }: any) => (
        <button onClick={onClick} className={className}>{children}</button>
    ),
}));

vi.mock('@/components/ui/badge', () => ({
    Badge: ({ children, className }: any) => (
        <span className={className}>{children}</span>
    ),
}));

vi.mock('lucide-react', () => ({
    Loader2: () => <span>Loader2</span>,
    Copy: () => <span>Copy</span>,
    CopyCheck: () => <span>CopyCheck</span>,
}));

describe('ChatMessagesView XSS Vulnerability', () => {
    const defaultProps = {
        messages: [],
        isLoading: false,
        scrollAreaRef: { current: null },
        onSubmit: vi.fn(),
        onCancel: vi.fn(),
        liveActivityEvents: [],
        historicalActivities: {},
    };

    it('renders javascript: links if not sanitized (or strips them if safe)', () => {
        const xssMessage: Message = {
            id: '1',
            type: 'ai',
            content: 'Click this: [Malicious Link](javascript:alert(1))',
            tool_calls: [],
            tool_call_chunks: [],
            additional_kwargs: {},
            response_metadata: {}
        };

        render(
            <ChatMessagesView
                {...defaultProps}
                messages={[xssMessage]}
            />
        );

        // Find the link
        const link = screen.getByText('Malicious Link');

        // Assert that the dangerous payload is NOT present in the href
        // React-markdown v9 strips javascript: by default, so this should pass.
        // Adding rehype-sanitize adds another layer of guarantee.
        expect(link).not.toHaveAttribute('href', 'javascript:alert(1)');

        // It likely renders without href or with a safe one
        const href = link.getAttribute('href');
        console.log('Rendered HREF:', href);

        // Ensure that if it has an href, it is not the malicious one
        if (href) {
             expect(href).not.toContain('javascript:');
        }
    });
});
