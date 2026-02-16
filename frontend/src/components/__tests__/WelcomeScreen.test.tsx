import { render, screen } from "@testing-library/react";
import { WelcomeScreen } from "../WelcomeScreen";
import { describe, it, expect, vi } from "vitest";

// Mock InputForm since we don't need to test its internals here
vi.mock("../InputForm", () => ({
  InputForm: () => <div data-testid="input-form">Input Form</div>,
}));

describe("WelcomeScreen", () => {
  const defaultProps = {
    handleSubmit: vi.fn(),
    onCancel: vi.fn(),
    isLoading: false,
  };

  it("renders as a generic container to avoid nested main landmarks", () => {
    render(<WelcomeScreen {...defaultProps} />);

    // Should not have a main role because App.tsx already provides one
    const mainLandmark = screen.queryByRole("main");
    expect(mainLandmark).not.toBeInTheDocument();
  });

  it("renders the welcome heading", () => {
    render(<WelcomeScreen {...defaultProps} />);
    expect(screen.getByRole("heading", { level: 1, name: /welcome/i })).toBeInTheDocument();
  });

  it("renders the semantic footer", () => {
    render(<WelcomeScreen {...defaultProps} />);
    const footer = screen.getByRole("contentinfo");
    expect(footer).toBeInTheDocument();
    expect(footer).toHaveTextContent(/Powered by Google Gemini and LangChain LangGraph/);
    expect(footer).toHaveClass("text-sm");
    expect(footer).toHaveClass("text-neutral-300");
  });
});
