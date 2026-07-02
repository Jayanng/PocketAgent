import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ThemeProvider } from "./theme-provider";
import { ThemeToggle } from "./theme-toggle";

// localStorage is provided by jsdom, clear before each test
beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.removeAttribute("data-landing-theme");
  document.documentElement.className = "";
});

function renderWithProvider(ui: React.ReactElement) {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
}

describe("ThemeToggle", () => {
  it("renders a button with an accessible label", () => {
    renderWithProvider(<ThemeToggle />);
    const btn = screen.getByRole("button");
    expect(btn).toBeInTheDocument();
    // Default theme is "light", so label should say "Switch to dark mode"
    expect(btn).toHaveAttribute("aria-label", "Switch to dark mode");
  });

  it("sets data-theme on the document in light mode (default)", () => {
    renderWithProvider(<ThemeToggle />);
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("toggles to dark mode on click and updates label + data-theme", () => {
    renderWithProvider(<ThemeToggle />);
    const btn = screen.getByRole("button");

    fireEvent.click(btn);

    // After clicking, theme should be "dark"
    expect(btn).toHaveAttribute("aria-label", "Switch to light mode");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("persists theme preference in localStorage", () => {
    renderWithProvider(<ThemeToggle />);
    const btn = screen.getByRole("button");

    fireEvent.click(btn);

    expect(localStorage.getItem("pocketagent-theme")).toBe("dark");
  });

  it("toggles back and forth", () => {
    renderWithProvider(<ThemeToggle />);
    const btn = screen.getByRole("button");

    // Start: light -> dark
    fireEvent.click(btn);
    expect(btn).toHaveAttribute("aria-label", "Switch to light mode");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

    // dark -> light
    fireEvent.click(btn);
    expect(btn).toHaveAttribute("aria-label", "Switch to dark mode");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("accepts a custom className", () => {
    renderWithProvider(<ThemeToggle className="my-theme-btn" />);
    expect(screen.getByRole("button").className).toContain("my-theme-btn");
  });
});
