import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TokenImportDialog } from "./token-import-dialog";

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
    // Reset fetch mocks
    (globalThis.fetch as unknown) = vi.fn();
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

  it("imports paste token on successful validation", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      status: 200,
      ok: true,
      json: async () => ({ id: "a1" }),
    });
    render(<TokenImportDialog {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText(/agent id/i), {
      target: { value: "a1" },
    });
    fireEvent.change(screen.getByPlaceholderText(/access token/i), {
      target: { value: "tok-xyz" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^import$/i }));
    await waitFor(() => {
      expect(defaultProps.onImported).toHaveBeenCalledWith("a1", "tok-xyz");
    });
  });

  it("shows error on paste validation failure", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      status: 401,
      ok: false,
      json: async () => ({ detail: "Invalid token" }),
    });
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
