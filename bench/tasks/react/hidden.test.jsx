import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";

import PagedList from "./src/PagedList.jsx";

const ITEMS = Array.from({ length: 12 }, (_, index) => `Item ${index + 1}`);

afterEach(cleanup);

function shown() {
  return screen.getAllByRole("listitem").map((item) => item.textContent);
}

function status() {
  return screen.getByRole("status").textContent.replace(/\s+/g, " ").trim();
}

function navigation() {
  return within(screen.getByRole("navigation", { name: "Pagination" }));
}

function button(name) {
  return navigation().getByRole("button", { name });
}

test("the first page shows the first five items", () => {
  render(<PagedList items={ITEMS} />);

  expect(shown()).toEqual(["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"]);
  expect(status()).toBe("Page 1 of 3");
  expect(button("Previous").disabled).toBe(true);
  expect(button("Next").disabled).toBe(false);
  expect(button("1").getAttribute("aria-current")).toBe("page");
  expect(button("2").getAttribute("aria-current")).not.toBe("page");
});

test("Next moves to the last page, where it is disabled", () => {
  render(<PagedList items={ITEMS} />);

  fireEvent.click(button("Next"));
  fireEvent.click(button("Next"));

  expect(shown()).toEqual(["Item 11", "Item 12"]);
  expect(status()).toBe("Page 3 of 3");
  expect(button("Next").disabled).toBe(true);
  expect(button("Previous").disabled).toBe(false);
  expect(button("3").getAttribute("aria-current")).toBe("page");
  expect(button("1").getAttribute("aria-current")).not.toBe("page");
});

test("a page button jumps to its page and Previous goes back one", () => {
  render(<PagedList items={ITEMS} />);

  fireEvent.click(button("3"));
  fireEvent.click(button("Previous"));

  expect(shown()).toEqual(["Item 6", "Item 7", "Item 8", "Item 9", "Item 10"]);
  expect(status()).toBe("Page 2 of 3");
});

test("the page size sets the items per page and the page buttons", () => {
  render(<PagedList items={ITEMS.slice(0, 8)} pageSize={4} />);

  expect(shown()).toEqual(["Item 1", "Item 2", "Item 3", "Item 4"]);
  expect(navigation().getAllByRole("button").map((element) => element.textContent)).toEqual([
    "Previous",
    "1",
    "2",
    "Next",
  ]);
  expect(status()).toBe("Page 1 of 2");
});

test("one page disables both Previous and Next", () => {
  render(<PagedList items={ITEMS.slice(0, 5)} />);

  expect(status()).toBe("Page 1 of 1");
  expect(button("Previous").disabled).toBe(true);
  expect(button("Next").disabled).toBe(true);
});

test("no items shows No items, without a list or a nav", () => {
  render(<PagedList items={[]} />);

  expect(screen.getByText("No items")).toBeTruthy();
  expect(screen.queryByRole("list")).toBeNull();
  expect(screen.queryByRole("navigation")).toBeNull();
});

test("a shorter items list shows its last page and navigates from it", () => {
  const { rerender } = render(<PagedList items={ITEMS} />);
  fireEvent.click(button("3"));

  rerender(<PagedList items={ITEMS.slice(0, 6)} />);

  expect(shown()).toEqual(["Item 6"]);
  expect(status()).toBe("Page 2 of 2");
  expect(button("2").getAttribute("aria-current")).toBe("page");
  expect(button("Next").disabled).toBe(true);

  fireEvent.click(button("Previous"));

  expect(shown()).toEqual(["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"]);
  expect(status()).toBe("Page 1 of 2");
});
