import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ArtifactView } from '../ArtifactView';
import '@testing-library/jest-dom';

// Mock SyntaxHighlighter because it's heavy and can cause issues in testing environments
vi.mock('react-syntax-highlighter', () => ({
    Prism: ({ children }: { children: React.ReactNode }) => <pre data-testid="syntax-highlighter">{children}</pre>,
}));

describe('ArtifactView', () => {
    const defaultProps = {
        isOpen: true,
        onClose: vi.fn(),
        title: 'Test Artifact',
    };

    it('renders nothing when isOpen is false', () => {
        render(<ArtifactView {...defaultProps} isOpen={false} content="Some content" type="text" />);
        expect(screen.queryByText('Test Artifact')).not.toBeInTheDocument();
    });

    it('renders markdown content', () => {
        const markdown = '# Hello World\nThis is **bold** text.';
        render(<ArtifactView {...defaultProps} content={markdown} type="markdown" />);

        expect(screen.getByText('Hello World').tagName).toBe('H1');
        expect(screen.getByText('bold').tagName).toBe('STRONG');
    });

    it('sanitizes dangerous HTML in markdown', () => {
        const malicious = 'Safe content <script>alert("xss")</script><img src="x" onerror="alert(1)">';
        render(<ArtifactView {...defaultProps} content={malicious} type="markdown" />);

        expect(screen.getByText(/Safe content/)).toBeInTheDocument();
        // script and img with onerror should be removed or sanitized by rehype-sanitize
        expect(screen.queryByText(/alert/)).not.toBeInTheDocument();
        const img = screen.queryByRole('img');
        if (img) {
            expect(img.getAttribute('onerror')).toBeNull();
        }
    });

    it('renders code content with syntax highlighter', () => {
        const code = 'const x = 10;';
        render(<ArtifactView {...defaultProps} content={code} type="code" />);

        expect(screen.getByTestId('syntax-highlighter')).toBeInTheDocument();
        expect(screen.getByText('const x = 10;')).toBeInTheDocument();
    });

    it('renders plain text content as a div', () => {
        const text = 'Just some plain text';
        render(<ArtifactView {...defaultProps} content={text} type="text" />);

        expect(screen.getByText(text)).toBeInTheDocument();
        expect(screen.getByText(text)).toHaveClass('whitespace-pre-wrap');
    });

    it('calls onClose when close button is clicked', async () => {
        const onClose = vi.fn();
        render(<ArtifactView {...defaultProps} onClose={onClose} content="Content" type="text" />);

        const closeButton = screen.getByTitle('Close');
        closeButton.click();

        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
