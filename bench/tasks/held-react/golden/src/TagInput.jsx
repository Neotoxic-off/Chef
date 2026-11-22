import { useState } from "react";

const MAX_TAG_LENGTH = 20;

function rejection(tag, tags) {
  if (tag.length > MAX_TAG_LENGTH) {
    return `Tags are at most ${MAX_TAG_LENGTH} characters`;
  }
  const lowerTag = tag.toLowerCase();
  if (tags.some((existing) => existing.toLowerCase() === lowerTag)) {
    return "Tag already added";
  }
  return null;
}

export default function TagInput({ initialTags = [], maxTags = 5, onChange }) {
  const [tags, setTags] = useState(initialTags);
  const [text, setText] = useState("");
  const [error, setError] = useState(null);

  function update(next) {
    setTags(next);
    setError(null);
    onChange?.(next);
  }

  function add() {
    const tag = text.trim();
    if (tag === "") {
      return;
    }
    const problem = rejection(tag, tags);
    if (problem !== null) {
      setError(problem);
      return;
    }
    update([...tags, tag]);
    setText("");
  }

  function handleKeyDown(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      add();
      return;
    }
    if (event.key === "Backspace" && text === "" && tags.length > 0) {
      update(tags.slice(0, -1));
    }
  }

  function handleChange(event) {
    setText(event.target.value);
    setError(null);
  }

  return (
    <div>
      {tags.length > 0 && (
        <ul aria-label="Tags">
          {tags.map((tag) => (
            <li key={tag}>
              {tag}
              <button
                type="button"
                aria-label={`Remove ${tag}`}
                onClick={() => update(tags.filter((kept) => kept !== tag))}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <input
        aria-label="Add tag"
        value={text}
        disabled={tags.length >= maxTags}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
      />
      {error !== null && <p role="alert">{error}</p>}
    </div>
  );
}
