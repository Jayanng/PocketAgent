import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TokenRotateDialog } from "./token-rotate-dialog";
import { tokenStore } from "@/lib/token-store";

vi.mock("@/lib/api", () => ({
  api: {
    agents: {
      reissue: vi.fn(),
    },
  },
}));
import { api } from "@/lib/api";
const mockedReissue = vi.mocked(api.agents.reissue);

describe("TokenRotateDialog", () => {
  beforeEach(() => {
    localStorage.clear();
    tokenStore.forget("a1");
    mockedReissue.mockReset();
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

  // ─── Regression: must go through api.agents.reissue, not raw fetch ─────
  it("rotates via api.agents.reissue with current_token proof", async () => {
    tokenStore.set("a1", "old-tok");
    mockedReissue.mockResolvedValueOnce({
      access_token: "new-tok",
      access_token_created_at: "2025-01-01T00:00:00Z",
      agent: null,
    } as never);
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
      expect(mockedReissue).toHaveBeenCalledWith("a1", {
        proof: { type: "current_token", token: "old-tok" },
      });
    });
    expect(onRotated).toHaveBeenCalledWith("new-tok");
    expect(onClose).toHaveBeenCalled();
    expect(tokenStore.get("a1")).toBe("new-tok");
  });

  it("surfaces api error detail to the user", async () => {
    tokenStore.set("a1", "old-tok");
    mockedReissue.mockRejectedValueOnce(new Error("Invalid token"));
    render(
      <TokenRotateDialog
        open={true}
        agentId="a1"
        onClose={vi.fn()}
        onRotated={vi.fn()}
        apiBase=""
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /^rotate$/i }));
    await waitFor(() => {
      expect(screen.getByText(/invalid token/i)).toBeInTheDocument();
    });
  });
});
