import { render, screen, fireEvent } from '@testing-library/react';
import { InputForm } from '@/components/InputForm';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock UI components to simplify testing
vi.mock('@/components/ui/button', () => ({
    Button: ({ children, onClick, disabled, type }: any) => (
        <button onClick={onClick} disabled={disabled} type={type}>
            {children}
        </button>
    ),
}));

vi.mock('@/components/ui/textarea', () => ({
    Textarea: ({ value, onChange, onKeyDown, placeholder }: any) => (
        <textarea
            value={value}
            onChange={onChange}
            onKeyDown={onKeyDown}
            placeholder={placeholder}
            role="textbox"
        />
    ),
}));

vi.mock('@/components/ui/select', () => ({
    Select: ({ children, onValueChange, value }: any) => (
        <div data-testid="select" data-value={value} onClick={() => onValueChange && onValueChange('new-value')}>
            {children}
        </div>
    ),
    SelectTrigger: ({ children }: any) => <div>{children}</div>,
    SelectValue: () => <span>Value</span>,
    SelectContent: ({ children }: any) => <div>{children}</div>,
    SelectItem: ({ children, value, onClick }: any) => (
        <div data-testid={`select-item-${value}`} onClick={onClick}>
            {children}
        </div>
    ),
}));

describe('InputForm', () => {
    const defaultProps = {
        onSubmit: vi.fn(),
        onCancel: vi.fn(),
        isLoading: false,
        hasHistory: false,
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders input field', () => {
        render(<InputForm {...defaultProps} />);
        expect(screen.getByRole('textbox')).toBeInTheDocument();
    });

    it('calls onSubmit when form is submitted with text', () => {
        render(<InputForm {...defaultProps} />);

        const input = screen.getByRole('textbox');
        fireEvent.change(input, { target: { value: 'test query' } });

        // Find the submit button (it has "Search" text)
        const submitButton = screen.getByText(/Search/i);
        fireEvent.click(submitButton);

        expect(defaultProps.onSubmit).toHaveBeenCalledWith('test query', 'medium', 'gemini-2.5-flash-preview-04-17');
    });

    it('does not call onSubmit when input is empty', () => {
        render(<InputForm {...defaultProps} />);

        const submitButton = screen.getByText(/Search/i);
        fireEvent.click(submitButton);

        expect(defaultProps.onSubmit).not.toHaveBeenCalled();
    });

    it('calls onCancel when stop button is clicked while loading', () => {
        render(<InputForm {...defaultProps} isLoading={true} />);

        // Stop button icon is StopCircle, but we mocked Button. 
        // In the real component, the button renders StopCircle icon.
        // Since we mocked Button to just render children, and StopCircle is an icon...
        // We can look for the button by role 'button'
        const buttons = screen.getAllByRole('button');
        // The stop button is the first one rendered in the loading state logic
        fireEvent.click(buttons[0]);

        expect(defaultProps.onCancel).toHaveBeenCalled();
    });

    it('submits on Ctrl+Enter', () => {
        render(<InputForm {...defaultProps} />);

        const input = screen.getByRole('textbox');
        fireEvent.change(input, { target: { value: 'test query' } });
        fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true });

        expect(defaultProps.onSubmit).toHaveBeenCalledWith('test query', 'medium', 'gemini-2.5-flash-preview-04-17');
    });

    it('shows New Search button when history exists', () => {
        render(<InputForm {...defaultProps} hasHistory={true} />);
        expect(screen.getByText(/New Search/i)).toBeInTheDocument();
    });
});
