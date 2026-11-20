import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";

import PagedList from "./PagedList.jsx";

const ITEMS = ["a", "b", "c", "d", "e", "f", "g"];

afterEach(cleanup);

function shown() {
  return screen.getAllByRole("listitem").map((item) => item.textContent);
}

test("shows one page at a time and moves with Next and Previous", () => {
  render(<PagedList items={ITEMS} pageSize={3} />);
  expect(shown()).toEqual(["a", "b", "c"]);
  expect(screen.getByRole("button", { name: "Previous" }).disabled).toBe(true);

  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(shown()).toEqual(["d", "e", "f"]);
  expect(screen.getByRole("button", { name: "2" }).getAttribute("aria-current")).toBe("page");

  fireEvent.click(screen.getByRole("button", { name: "Previous" }));
  expect(shown()).toEqual(["a", "b", "c"]);
});

test("the last page disables Next", () => {
  render(<PagedList items={ITEMS} pageSize={3} />);
  fireEvent.click(screen.getByRole("button", { name: "3" }));

  expect(shown()).toEqual(["g"]);
  expect(screen.getByRole("status").textContent).toBe("Page 3 of 3");
  expect(screen.getByRole("button", { name: "Next" }).disabled).toBe(true);
});

test("an empty list shows No items and no navigation", () => {
  render(<PagedList items={[]} />);

  expect(screen.getByText("No items")).toBeTruthy();
  expect(screen.queryByRole("navigation")).toBeNull();
});

test("shrinking items shows the last page that still exists", () => {
  const { rerender } = render(<PagedList items={ITEMS} pageSize={3} />);
  fireEvent.click(screen.getByRole("button", { name: "3" }));

  rerender(<PagedList items={ITEMS.slice(0, 4)} pageSize={3} />);
  expect(shown()).toEqual(["d"]);

  fireEvent.click(screen.getByRole("button", { name: "Previous" }));
  expect(shown()).toEqual(["a", "b", "c"]);
});
