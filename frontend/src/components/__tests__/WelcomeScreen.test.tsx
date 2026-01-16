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

  it("does not render with a main landmark (handled by parent App)", () => {
    render(<WelcomeScreen {...defaultProps} />);

    // WelcomeScreen should not have a main landmark to avoid nesting in App's main
    const mainLandmark = screen.queryByRole("main");
    expect(mainLandmark).not.toBeInTheDocument();
  });

  it("renders the welcome heading", () => {
    render(<WelcomeScreen {...defaultProps} />);
    expect(screen.getByRole("heading", { level: 1, name: /welcome/i })).toBeInTheDocument();
  });
});
