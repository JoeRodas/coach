import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PgnInput from "./PgnInput";

describe("PgnInput", () => {
  it("blocks submit on empty PGN with an inline error", () => {
    const onSubmit = vi.fn();
    render(<PgnInput onSubmit={onSubmit} isSubmitting={false} />);
    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText(/paste a game/i)).toBeInTheDocument();
  });

  it("submits with a valid PGN and the chosen color", () => {
    const onSubmit = vi.fn();
    render(<PgnInput onSubmit={onSubmit} isSubmitting={false} />);
    fireEvent.change(screen.getByLabelText(/^pgn$/i), {
      target: { value: "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6" },
    });
    fireEvent.click(screen.getByLabelText(/black/i));
    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));
    expect(onSubmit).toHaveBeenCalledWith({
      pgn: "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6",
      playerColor: "black",
      question: undefined,
    });
  });

  it('seeds the form when "Try a sample game" is clicked', () => {
    const onSubmit = vi.fn();
    render(<PgnInput onSubmit={onSubmit} isSubmitting={false} />);
    const textarea = screen.getByLabelText(/^pgn$/i) as HTMLTextAreaElement;
    expect(textarea.value).toBe("");
    fireEvent.click(screen.getByRole("button", { name: /try a sample game/i }));
    expect(textarea.value).toContain("Morphy");
  });

  it("disables the submit button while a request is in flight", () => {
    render(<PgnInput onSubmit={vi.fn()} isSubmitting={true} />);
    const btn = screen.getByRole("button", { name: /analyzing/i });
    expect(btn).toBeDisabled();
  });
});
