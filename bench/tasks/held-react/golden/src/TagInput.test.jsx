import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import TagInput from "./TagInput.jsx";

afterEach(cleanup);

function input() {
  return screen.getByRole("textbox", { name: "Add tag" });
}

function type(text) {
  fireEvent.change(input(), { target: { value: text } });
}

function pressEnter() {
  return fireEvent.keyDown(input(), { key: "Enter" });
}

test("Enter adds the trimmed tag, clears the input and calls onChange", () => {
  const onChange = vi.fn();
  render(<TagInput onChange={onChange} />);
  type(" react ");

  const notPrevented = pressEnter();

  expect(notPrevented).toBe(false);
  expect(screen.getByRole("button", { name: "Remove react" })).toBeTruthy();
  expect(input().value).toBe("");
  expect(onChange).toHaveBeenCalledWith(["react"]);
});

test("a blank entry adds nothing", () => {
  const onChange = vi.fn();
  render(<TagInput onChange={onChange} />);
  type("  ");

  pressEnter();

  expect(screen.queryByRole("list")).toBeNull();
  expect(onChange).not.toHaveBeenCalled();
});

test("a duplicate in another case shows an alert until the text changes", () => {
  const onChange = vi.fn();
  render(<TagInput initialTags={["React"]} onChange={onChange} />);
  type("REACT");

  pressEnter();
  expect(screen.getByRole("alert").textContent).toBe("Tag already added");
  expect(input().value).toBe("REACT");
  expect(onChange).not.toHaveBeenCalled();

  type("REAC");
  expect(screen.queryByRole("alert")).toBeNull();
});

test("20 characters is accepted and 21 rejected", () => {
  render(<TagInput />);
  type("b".repeat(20));
  pressEnter();
  type("c".repeat(21));

  pressEnter();

  expect(screen.getByRole("button", { name: `Remove ${"b".repeat(20)}` })).toBeTruthy();
  expect(screen.getByRole("alert").textContent).toBe("Tags are at most 20 characters");
});

test("Backspace in an empty input removes the last tag", () => {
  render(<TagInput initialTags={["a", "b"]} />);

  fireEvent.keyDown(input(), { key: "Backspace" });

  expect(screen.getAllByRole("listitem")).toHaveLength(1);
  expect(screen.getByRole("button", { name: "Remove a" })).toBeTruthy();
});

test("Backspace with text keeps the tags", () => {
  render(<TagInput initialTags={["a"]} />);
  type("x");

  fireEvent.keyDown(input(), { key: "Backspace" });

  expect(screen.getAllByRole("listitem")).toHaveLength(1);
});

test("the input is disabled at maxTags and enabled after a removal", () => {
  render(<TagInput initialTags={["a"]} maxTags={2} />);
  type("b");
  pressEnter();
  expect(input().disabled).toBe(true);

  fireEvent.click(screen.getByRole("button", { name: "Remove a" }));

  expect(input().disabled).toBe(false);
  expect(screen.queryByRole("button", { name: "Remove a" })).toBeNull();
});
