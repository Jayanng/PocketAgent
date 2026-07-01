import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "./button";

describe("Button", () => {
  it("renders with default props", () => {
    render(<Button>Click me</Button>);
    const btn = screen.getByRole("button", { name: /click me/i });
    expect(btn).toBeInTheDocument();
    expect(btn).not.toBeDisabled();
    expect(btn).toHaveAttribute("type", "button");
  });

  it("renders children text", () => {
    render(<Button>Submit</Button>);
    expect(screen.getByText("Submit")).toBeInTheDocument();
  });

  it("renders as type submit when specified", () => {
    render(<Button type="submit">Send</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "submit");
  });

  it("fires onClick handler", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Press</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it("is disabled when the disabled prop is set", () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("does not fire onClick when disabled", () => {
    const handleClick = vi.fn();
    render(<Button disabled onClick={handleClick}>Disabled</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(handleClick).not.toHaveBeenCalled();
  });

  it("applies custom className alongside defaults", () => {
    render(<Button className="my-custom-class">Styled</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("my-custom-class");
    expect(btn.className).toContain("inline-flex"); // default class from cn
  });

  describe("variants", () => {
    it("renders primary variant by default", () => {
      render(<Button>Primary</Button>);
      const btn = screen.getByRole("button");
      expect(btn.className).toContain("bg-primary");
    });

    it("renders secondary variant", () => {
      render(<Button variant="secondary">Secondary</Button>);
      const btn = screen.getByRole("button");
      expect(btn.className).toContain("bg-card");
    });

    it("renders ghost variant", () => {
      render(<Button variant="ghost">Ghost</Button>);
      const btn = screen.getByRole("button");
      expect(btn.className).toContain("bg-transparent");
    });
  });

  describe("sizes", () => {
    it("renders md size by default", () => {
      render(<Button>Medium</Button>);
      expect(screen.getByRole("button").className).toContain("h-10");
    });

    it("renders sm size", () => {
      render(<Button size="sm">Small</Button>);
      expect(screen.getByRole("button").className).toContain("h-8");
    });

    it("renders icon size", () => {
      render(
        <Button size="icon" aria-label="Icon only">
          ★
        </Button>,
      );
      const btn = screen.getByRole("button");
      expect(btn.className).toContain("w-9");
      expect(btn.className).toContain("h-9");
    });
  });

  it("forwards additional HTML button props", () => {
    render(
      <Button data-testid="my-btn" aria-label="Custom label">
        Test
      </Button>,
    );
    expect(screen.getByTestId("my-btn")).toHaveAttribute(
      "aria-label",
      "Custom label",
    );
  });
});
