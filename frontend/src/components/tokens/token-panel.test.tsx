import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TokenPanel } from "./token-panel";
import { tokenStore } from "@/lib/token-store";

describe("TokenPanel", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("shows 'Access token required' banner when token is missing", () => {
    tokenStore.forget("a1");
    render(
      <TokenPanel
        agentId="a1"
        agentName="Test"
        onRotate={vi.fn()}
        onImport={vi.fn()}
        onSignToReissue={vi.fn()}
      />,
    );
    expect(screen.getByText(/access token required/i)).toBeInTheDocument();
  });

  it("shows active state when token exists", () => {
    tokenStore.set("a1", "tok-1");
    render(
      <TokenPanel
        agentId="a1"
        agentName="Test"
        onRotate={vi.fn()}
        onImport={vi.fn()}
        onSignToReissue={vi.fn()}
      />,
    );
    expect(screen.getByTestId("active-panel")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /rotate/i })).toBeInTheDocument();
  });

  it("calls onRotate when Rotate button clicked", () => {
    tokenStore.set("a1", "tok-1");
    const onRotate = vi.fn();
    render(
      <TokenPanel
        agentId="a1"
        agentName="Test"
        onRotate={onRotate}
        onImport={vi.fn()}
        onSignToReissue={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /rotate/i }));
    expect(onRotate).toHaveBeenCalledOnce();
  });

  it("calls onImport when Import button clicked in missing state", () => {
    tokenStore.forget("a1");
    const onImport = vi.fn();
    render(
      <TokenPanel
        agentId="a1"
        agentName="Test"
        onRotate={vi.fn()}
        onImport={onImport}
        onSignToReissue={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /import token/i }));
    expect(onImport).toHaveBeenCalledOnce();
  });
});
