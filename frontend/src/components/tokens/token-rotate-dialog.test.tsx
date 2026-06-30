import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TokenRotateDialog } from "./token-rotate-dialog";
import { tokenStore } from "@/lib/token-store";

describe("TokenRotateDialog", () => {
  beforeEach(() => {
    localStorage.clear();
    tokenStore.forget("a1");
  });

  it("renders the confirmation prompt", () => {
    render(
      <TokenRotateDialog
        open={true}
        agentId="a1"
        onClose={vi.fn()}
        onRotated={vi.fn()}
        apiBase=""
      />,
    );
    expect(screen.getByText(/rotate access token/i)).toBeInTheDocument();
    expect(screen.getByText(/invalidate/i)).toBeInTheDocument();
  });

  it("calls onClose when Cancel clicked", () => {
    const onClose = vi.fn();
    render(
      <TokenRotateDialog
        open={true}
        agentId="a1"
        onClose={onClose}
        onRotated={vi.fn()}
        apiBase=""
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it("rotates successfully when token exists and server returns new token", async () => {
    tokenStore.set("a1", "old-tok");
    (globalThis.fetch as unknown) = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ access_token: "new-tok" }),
    });
    const onRotated = vi.fn();
    const onClose = vi.fn();
    render(
      <TokenRotateDialog
        open={true}
        agentId="a1"
        onClose={onClose}
        onRotated={onRotated}
        apiBase=""
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /^rotate$/i }));
    await waitFor(() => {
      expect(onRotated).toHaveBeenCalledWith("new-tok");
    });
    expect(onClose).toHaveBeenCalled();
    expect(tokenStore.get("a1")).toBe("new-tok");
  });
});
