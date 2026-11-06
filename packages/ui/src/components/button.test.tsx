import { afterEach, expect, test } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { Button } from "./button";

afterEach(cleanup);

test("Button renders a native button with the default variant styling", () => {
  render(<Button>Save layout</Button>);

  const button = screen.getByRole("button", { name: "Save layout" });
  expect(button.className).toContain("bg-primary");
  expect(button.className).not.toContain("bg-secondary");
});

test("Button applies the requested variant and size classes", () => {
  render(
    <Button variant="outline" size="lg">
      Import labs
    </Button>,
  );

  const button = screen.getByRole("button", { name: "Import labs" });
  expect(button.className).toContain("border-input");
  expect(button.className).toContain("h-11");
});

test("Button forwards click events to the consumer", () => {
  let clicks = 0;

  render(<Button onClick={() => (clicks += 1)}>Ping endpoint</Button>);
  fireEvent.click(screen.getByRole("button", { name: "Ping endpoint" }));

  expect(clicks).toBe(1);
});
