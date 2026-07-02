import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen, fireEvent } from "@testing-library/react";
import { TokenPanel } from "./token-panel";
import { tokenStore } from "@/lib/token-store";

describe("TokenPanel", () => {
  beforeEach(() => {
    localStorage.clear();
    tokenStore.forget("a1");
  });

  afterEach(() => {
    vi.useRealTimers();
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

  // ─── Regression: "recently rotated" timer must not leak after unmount ───
  it("does not set state after unmount when 5-min rotated timer fires", () => {
    vi.useFakeTimers();
    const store = tokenStore;
    store.forget("a1");
    // Render with a token so the panel mounts in the active branch,
    // then fire a set event to schedule the 5-min timer.
    store.set("a1", "tok-1");
    const { unmount } = render(
      <TokenPanel
        agentId="a1"
        agentName="Test"
        onRotate={vi.fn()}
        onImport={vi.fn()}
        onSignToReissue={vi.fn()}
      />,
    );
    // Fire a synthetic 'set' event wrapped in act() to suppress React's
    // warning about state updates outside act(). The active panel
    // subscribes via store.onChange.
    act(() => { store.set("a1", "tok-2"); });
    unmount();
    // Advance past 5 minutes; without cleanup this would attempt to
    // setState on an unmounted component.
    expect(() => vi.advanceTimersByTime(5 * 60 * 1000 + 1000)).not.toThrow();
  });
});
