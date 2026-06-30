import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TokenDisplayModal } from "./token-display-modal";

describe("TokenDisplayModal", () => {
  const defaultProps = {
    open: true,
    agentName: "Test Agent",
    token: "secret-token-value-1234567890",
    onAcknowledged: vi.fn(),
  };

  it("renders masked token by default", () => {
    render(<TokenDisplayModal {...defaultProps} />);
    expect(screen.queryByText("secret-token-value-1234567890")).not.toBeInTheDocument();
    expect(screen.getByTestId("token-display").textContent).toMatch(/•+/);
  });

  it("reveals token when eye icon clicked", async () => {
    const user = userEvent.setup();
    render(<TokenDisplayModal {...defaultProps} />);
    await user.click(screen.getByRole("button", { name: /show token/i }));
    expect(screen.getByTestId("token-display").textContent).toContain(
      "secret-token-value-1234567890",
    );
  });

  it("Continue button is disabled until checkbox ticked", () => {
    render(<TokenDisplayModal {...defaultProps} />);
    const continueBtn = screen.getByRole("button", { name: /continue/i });
    expect(continueBtn).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    expect(continueBtn).toBeEnabled();
  });

  it("calls onAcknowledged when Continue is clicked after ticking checkbox", async () => {
    const user = userEvent.setup();
    const onAck = vi.fn();
    render(<TokenDisplayModal {...defaultProps} onAcknowledged={onAck} />);
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /continue/i }));
    expect(onAck).toHaveBeenCalledOnce();
  });

  it("calls navigator.clipboard.writeText on Copy click", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
      writable: true,
    });
    render(<TokenDisplayModal {...defaultProps} />);
    await user.click(screen.getByRole("button", { name: /copy/i }));
    expect(writeText).toHaveBeenCalledWith("secret-token-value-1234567890");
  });
});
