import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { InputForm } from '@/components/InputForm';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock UI components
vi.mock('@/components/ui/button', () => ({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Button: ({ children, onClick, disabled, type, 'aria-label': ariaLabel, title }: any) => (
        <button onClick={onClick} disabled={disabled} type={type} aria-label={ariaLabel} title={title}>
            {children}
        </button>
    ),
}));

vi.mock('@/components/ui/textarea', () => ({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Textarea: ({ value, onChange, onKeyDown, placeholder, 'aria-label': ariaLabel, 'aria-required': ariaRequired, ref, autoFocus, className }: any) => (
        <textarea
            ref={ref}
            value={value}
            onChange={onChange}
            onKeyDown={onKeyDown}
            placeholder={placeholder}
            role="textbox"
            aria-label={ariaLabel}
            aria-required={ariaRequired}
            autoFocus={autoFocus}
            className={className}
        />
    ),
}));

// Robust mock for Select that allows simulation of value changes
vi.mock('@/components/ui/select', () => ({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Select: ({ children, onValueChange, value }: any) => (
        <div data-testid="select-root" data-value={value}>
             {/*
                We expose hidden buttons to simulate selecting specific values.
                These buttons call the onValueChange handler passed by the parent (InputForm).
                IMPORTANT: Must use type="button" to prevent accidental form submission!
             */}
             <button
                type="button"
                data-testid="mock-select-option-gemini-2.5-flash"
                onClick={() => onValueChange('gemini-2.5-flash')}
             >
                Select Gemini Flash
             </button>
             <button
                type="button"
                data-testid="mock-select-option-high"
                onClick={() => onValueChange('high')}
             >
                Select High Effort
             </button>
            {children}
        </div>
    ),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    SelectTrigger: ({ children, id, 'aria-label': ariaLabel }: any) => (
        <button type="button" role="combobox" id={id} aria-label={ariaLabel}>
            {children}
        </button>
    ),
    SelectValue: () => <span data-testid="select-value">Value</span>,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    SelectContent: ({ children }: any) => <div>{children}</div>,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    SelectItem: ({ children, value }: any) => (
        <div data-value={value} role="option">
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
        const input = screen.getByRole('textbox', { name: /chat input/i });
        expect(input).toBeInTheDocument();
        expect(input).toHaveAttribute('aria-required', 'true');
    });

    it('passes autoFocus to textarea', () => {
        render(<InputForm {...defaultProps} autoFocus={true} />);
        const input = screen.getByRole('textbox', { name: /chat input/i });
        expect(input).toHaveFocus();
    });

    it('calls onSubmit when form is submitted with text', async () => {
        const user = userEvent.setup();
        render(<InputForm {...defaultProps} />);

        const input = screen.getByRole('textbox', { name: /chat input/i });
        await user.type(input, 'test query');

        const submitButton = screen.getByRole('button', { name: /search/i });
        await user.click(submitButton);

        expect(defaultProps.onSubmit).toHaveBeenCalledWith('test query', 'medium', 'gemma-3-27b-it');
    });

    it('does not call onSubmit when input is empty', async () => {
        const user = userEvent.setup();
        render(<InputForm {...defaultProps} />);

        const submitButton = screen.getByRole('button', { name: /search/i });
        expect(submitButton).toBeDisabled();

        await user.click(submitButton);

        expect(defaultProps.onSubmit).not.toHaveBeenCalled();
    });

    it('calls onCancel when stop button is clicked while loading', async () => {
        const user = userEvent.setup();
        render(<InputForm {...defaultProps} isLoading={true} />);

        const stopButton = screen.getByRole('button', { name: /stop generating/i });
        await user.click(stopButton);

        expect(defaultProps.onCancel).toHaveBeenCalled();
    });

    it('submits on Ctrl+Enter', async () => {
        const user = userEvent.setup();
        render(<InputForm {...defaultProps} />);

        const input = screen.getByRole('textbox', { name: /chat input/i });
        await user.type(input, 'test query');
        await user.keyboard('{Control>}{Enter}{/Control}');

        expect(defaultProps.onSubmit).toHaveBeenCalledWith('test query', 'medium', 'gemma-3-27b-it');
    });

    it('allows changing the model and submits with new model', async () => {
        const user = userEvent.setup();
        render(<InputForm {...defaultProps} />);

        const input = screen.getByRole('textbox', { name: /chat input/i });
        await user.type(input, 'test query');

        // Locate the Model selection area trigger
        const modelTrigger = screen.getByRole('combobox', { name: /model selection/i });
        const modelSelectRoot = modelTrigger.closest('div[data-testid="select-root"]');
        expect(modelSelectRoot).not.toBeNull();

        // Find the hidden button specifically inside the Model Select

        const changeModelButton = modelSelectRoot!.querySelector('button[data-testid="mock-select-option-gemini-2.5-flash"]');
        expect(changeModelButton).not.toBeNull();

        // Click to change model
        await user.click(changeModelButton as HTMLElement);

        // Verify state update via the data-value attribute on the root
        await waitFor(() => {
            expect(modelSelectRoot).toHaveAttribute('data-value', 'gemini-2.5-flash');
        });

        // Submit
        const submitButton = screen.getByRole('button', { name: /search/i });
        await user.click(submitButton);

        expect(defaultProps.onSubmit).toHaveBeenCalledWith('test query', 'medium', 'gemini-2.5-flash');
    });

    it('allows changing the effort and submits with new effort', async () => {
        const user = userEvent.setup();
        render(<InputForm {...defaultProps} />);

        const input = screen.getByRole('textbox', { name: /chat input/i });
        await user.type(input, 'test query');

        const effortTrigger = screen.getByRole('combobox', { name: /effort selection/i });
        const effortSelectRoot = effortTrigger.closest('div[data-testid="select-root"]');
        expect(effortSelectRoot).not.toBeNull();


        const changeEffortButton = effortSelectRoot!.querySelector('button[data-testid="mock-select-option-high"]');
        expect(changeEffortButton).not.toBeNull();

        await user.click(changeEffortButton as HTMLElement);

        // Verify state update
        await waitFor(() => {
            expect(effortSelectRoot).toHaveAttribute('data-value', 'high');
        });

        const submitButton = screen.getByRole('button', { name: /search/i });
        await user.click(submitButton);

        expect(defaultProps.onSubmit).toHaveBeenCalledWith('test query', 'high', 'gemma-3-27b-it');
    });

    it('shows New Search button with correct attributes when history exists', () => {
        render(<InputForm {...defaultProps} hasHistory={true} />);
        const newSearchButton = screen.getByRole('button', { name: /start a new search session/i });
        expect(newSearchButton).toBeInTheDocument();
        expect(newSearchButton).toHaveAttribute('type', 'button');
        expect(newSearchButton).toHaveAttribute('title', 'Start a new search session');
    });

    it('clears input and sets focus back to textarea when Clear button is clicked', async () => {
        const user = userEvent.setup();
        render(<InputForm {...defaultProps} />);

        const input = screen.getByRole('textbox', { name: /chat input/i });
        await user.type(input, 'test query');

        const clearButton = screen.getByRole('button', { name: /clear input/i });
        expect(clearButton).toBeInTheDocument();

        // Spy on focus method
        // Since we are mocking Textarea, the focus method on the element might be different
        // We need to ensure our mock forwards ref or we access the DOM element directly
        // However, in JSDOM, focus() works on elements.

        // Wait, since we are mocking Textarea, we need to make sure the mock renders a textarea element that can receive focus.
        // Our mock does render a <textarea>, so it should work.

        await user.click(clearButton);

        expect(input).toHaveValue('');
        expect(input).toHaveFocus();
    });
});
