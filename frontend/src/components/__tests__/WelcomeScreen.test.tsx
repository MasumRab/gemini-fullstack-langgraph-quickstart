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

  it("renders with a main landmark for accessibility", () => {
    render(<WelcomeScreen {...defaultProps} />);

    // This should fail initially as there is no main role
    const mainLandmark = screen.getByRole("main");
    expect(mainLandmark).toBeInTheDocument();
  });

  it("renders the welcome heading", () => {
    render(<WelcomeScreen {...defaultProps} />);
    expect(screen.getByRole("heading", { level: 1, name: /welcome/i })).toBeInTheDocument();
  });
});
