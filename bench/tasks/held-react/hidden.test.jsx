import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import TagInput from "./src/TagInput.jsx";

afterEach(cleanup);

function input() {
  return screen.getByRole("textbox", { name: "Add tag" });
}

function tags() {
  const list = screen.queryByRole("list", { name: "Tags" });
  if (list === null) {
    return [];
  }
  return within(list)
    .getAllByRole("listitem")
    .map((item) => within(item).getByRole("button").getAttribute("aria-label").slice("Remove ".length));
}

function alertText() {
  // An always-mounted live region with no text counts as no alert.
  return screen.queryByRole("alert")?.textContent.trim() || null;
}

// Fires both events, so an answer may listen to onChange or onInput.
function type(text) {
  fireEvent.input(input(), { target: { value: text } });
  fireEvent.change(input(), { target: { value: text } });
}

function enter(text) {
  type(text);
  return fireEvent.keyDown(input(), { key: "Enter" });
}

test("the initial tags are listed with their remove buttons", () => {
  render(<TagInput initialTags={["react", "css"]} />);

  expect(tags()).toEqual(["react", "css"]);
  expect(screen.getAllByRole("listitem")).toHaveLength(2);
  expect(screen.getByRole("button", { name: "Remove css" })).toBeTruthy();
  expect(alertText()).toBeNull();
});

test("no tags renders no list", () => {
  render(<TagInput />);

  expect(screen.queryByRole("list")).toBeNull();
  expect(input().disabled).toBe(false);
});

test("Enter adds the trimmed text as the last tag, clears the input and prevents the default", () => {
  const onChange = vi.fn();
  render(<TagInput initialTags={["react"]} onChange={onChange} />);

  const notPrevented = enter("  hooks  ");

  expect(notPrevented).toBe(false);
  expect(tags()).toEqual(["react", "hooks"]);
  expect(input().value).toBe("");
  expect(onChange).toHaveBeenCalledTimes(1);
  expect(onChange).toHaveBeenCalledWith(["react", "hooks"]);
});

test("the initial tags array is never mutated", () => {
  const initialTags = Object.freeze(["react"]);
  render(<TagInput initialTags={initialTags} />);

  enter("hooks");
  fireEvent.click(screen.getByRole("button", { name: "Remove react" }));

  expect(initialTags).toEqual(["react"]);
  expect(tags()).toEqual(["hooks"]);
});

test("a whitespace-only entry is ignored and its Enter is prevented", () => {
  const onChange = vi.fn();
  render(<TagInput onChange={onChange} />);

  const notPrevented = enter("   ");

  expect(notPrevented).toBe(false);
  expect(tags()).toEqual([]);
  expect(alertText()).toBeNull();
  expect(onChange).not.toHaveBeenCalled();
});

test("a duplicate in another letter case is rejected and stays in the input", () => {
  const onChange = vi.fn();
  render(<TagInput initialTags={["React"]} onChange={onChange} />);

  const notPrevented = enter(" react ");

  expect(notPrevented).toBe(false);
  expect(alertText()).toBe("Tag already added");
  expect(tags()).toEqual(["React"]);
  expect(input().value).toBe(" react ");
  expect(onChange).not.toHaveBeenCalled();
});

test("changing the input text hides the alert", () => {
  render(<TagInput initialTags={["react"]} />);
  enter("react");

  type("reac");

  expect(alertText()).toBeNull();
});

test("a tag of exactly 20 characters is accepted", () => {
  render(<TagInput />);

  enter("a".repeat(20));

  expect(tags()).toEqual(["a".repeat(20)]);
  expect(alertText()).toBeNull();
});

test("the length is measured after trimming", () => {
  render(<TagInput />);

  enter(`  ${"a".repeat(20)}  `);

  expect(tags()).toEqual(["a".repeat(20)]);
  expect(alertText()).toBeNull();
});

test("initialTags is read on the first render only", () => {
  const { rerender } = render(<TagInput initialTags={["react"]} />);

  rerender(<TagInput initialTags={["css", "html"]} />);

  expect(tags()).toEqual(["react"]);
});

test("a tag of 21 characters is rejected", () => {
  render(<TagInput />);

  enter(`  ${"a".repeat(21)}  `);

  expect(alertText()).toBe("Tags are at most 20 characters");
  expect(tags()).toEqual([]);
});

test("a remove button removes its tag, calls onChange and hides the alert", () => {
  const onChange = vi.fn();
  render(<TagInput initialTags={["react", "css", "html"]} onChange={onChange} />);
  enter("css");

  fireEvent.click(screen.getByRole("button", { name: "Remove css" }));

  expect(tags()).toEqual(["react", "html"]);
  expect(onChange).toHaveBeenCalledWith(["react", "html"]);
  expect(alertText()).toBeNull();
});

test("removing the last tag removes the list", () => {
  render(<TagInput initialTags={["react"]} />);

  fireEvent.click(screen.getByRole("button", { name: "Remove react" }));

  expect(screen.queryByRole("list")).toBeNull();
});

test("Backspace in an empty input removes the last tag", () => {
  const onChange = vi.fn();
  render(<TagInput initialTags={["react", "css"]} onChange={onChange} />);

  fireEvent.keyDown(input(), { key: "Backspace" });

  expect(tags()).toEqual(["react"]);
  expect(onChange).toHaveBeenCalledWith(["react"]);
});

test("Backspace with text in the input keeps the tags", () => {
  render(<TagInput initialTags={["react", "css"]} />);
  type("x");

  fireEvent.keyDown(input(), { key: "Backspace" });

  expect(tags()).toEqual(["react", "css"]);
});

test("the fifth tag disables the input by default and a removal enables it", () => {
  render(<TagInput initialTags={["a", "b", "c", "d"]} />);
  expect(input().disabled).toBe(false);

  enter("e");
  expect(input().disabled).toBe(true);

  fireEvent.click(screen.getByRole("button", { name: "Remove a" }));
  expect(input().disabled).toBe(false);
});

test("maxTags sets the limit", () => {
  render(<TagInput initialTags={["a"]} maxTags={2} />);

  enter("b");

  expect(tags()).toEqual(["a", "b"]);
  expect(input().disabled).toBe(true);
});

test("more initial tags than maxTags disables the input", () => {
  render(<TagInput initialTags={["a", "b", "c"]} maxTags={2} />);

  expect(tags()).toEqual(["a", "b", "c"]);
  expect(input().disabled).toBe(true);
});
