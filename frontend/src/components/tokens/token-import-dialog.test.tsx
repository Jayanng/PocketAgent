import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TokenImportDialog } from "./token-import-dialog";

vi.mock("@/lib/api", () => ({
  api: {
    agents: {
      reissue: vi.fn(),
      get: vi.fn(),
    },
  },
}));
import { api } from "@/lib/api";
const mockedReissue = vi.mocked(api.agents.reissue);
const mockedGet = vi.mocked(api.agents.get);

describe("TokenImportDialog", () => {
  const defaultProps = {
    open: true,
    onClose: vi.fn(),
    onImported: vi.fn(),
    onRequestChallenge: vi
      .fn()
      .mockResolvedValue({ message: "pocketagent:reissue:a1:123", timestamp: 123 }),
    onSignMessage: vi
      .fn()
      .mockResolvedValue({ signature: "0xsig", publicKey: "0xpub" }),
    agentChains: ["ethereum"],
    apiBase: "",
  };

  beforeEach(() => {
    mockedReissue.mockReset();
    mockedGet.mockReset();
  });

  it("renders two tabs (paste and wallet)", () => {
    render(<TokenImportDialog {...defaultProps} />);
    expect(screen.getByRole("tab", { name: /paste token/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /sign with wallet/i })).toBeInTheDocument();
  });

  it("closes when Cancel clicked", () => {
    render(<TokenImportDialog {...defaultProps} />);
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  // ─── Regression: must go through api.agents.get, not raw fetch ──────────
  it("imports paste token via api.agents.get on successful validation", async () => {
    mockedGet.mockResolvedValueOnce({ id: "a1" } as never);
    render(<TokenImportDialog {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText(/agent id/i), {
      target: { value: "a1" },
    });
    fireEvent.change(screen.getByPlaceholderText(/access token/i), {
      target: { value: "tok-xyz" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^import$/i }));
    await waitFor(() => {
      expect(mockedGet).toHaveBeenCalledWith("a1", "tok-xyz");
    });
    expect(defaultProps.onImported).toHaveBeenCalledWith("a1", "tok-xyz");
  });

  // ─── Regression: must go through api.agents.reissue, not raw fetch ─────
  it("imports via wallet signature using api.agents.reissue", async () => {
    mockedReissue.mockResolvedValueOnce({
      access_token: "new-tok",
      access_token_created_at: "2025-01-01T00:00:00Z",
      agent: null,
    } as never);
    render(<TokenImportDialog {...defaultProps} />);
    fireEvent.click(screen.getByRole("tab", { name: /sign with wallet/i }));
    fireEvent.change(screen.getByPlaceholderText(/agent id/i), {
      target: { value: "a1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign and reissue/i }));
    await waitFor(() => {
      expect(mockedReissue).toHaveBeenCalledWith("a1", {
        proof: {
          type: "wallet_signature",
          chain: "ethereum",
          message: "pocketagent:reissue:a1:123",
          signature: "0xsig",
          public_key: "0xpub",
        },
      });
    });
    expect(defaultProps.onImported).toHaveBeenCalledWith("a1", "new-tok");
  });

  it("surfaces api error detail to the user on paste failure", async () => {
    mockedGet.mockRejectedValueOnce(new Error("Invalid token or wrong agent ID"));
    render(<TokenImportDialog {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText(/agent id/i), {
      target: { value: "a1" },
    });
    fireEvent.change(screen.getByPlaceholderText(/access token/i), {
      target: { value: "wrong-tok" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^import$/i }));
    await waitFor(() => {
      expect(screen.getByText(/invalid token or wrong agent id/i)).toBeInTheDocument();
    });
  });
});
