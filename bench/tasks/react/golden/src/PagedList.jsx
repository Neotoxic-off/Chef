import { useState } from "react";

export default function PagedList({ items, pageSize = 5 }) {
  const [page, setPage] = useState(1);
  if (items.length === 0) {
    return <p>No items</p>;
  }
  const pageCount = Math.ceil(items.length / pageSize);
  // Clamped at render time: when items shrinks, the last page that still exists is shown and navigated from.
  const current = Math.min(page, pageCount);
  const start = (current - 1) * pageSize;
  const pages = Array.from({ length: pageCount }, (_, index) => index + 1);
  return (
    <div>
      <ul>
        {items.slice(start, start + pageSize).map((item, index) => (
          <li key={start + index}>{item}</li>
        ))}
      </ul>
      <nav aria-label="Pagination">
        <button type="button" disabled={current === 1} onClick={() => setPage(current - 1)}>
          Previous
        </button>
        {pages.map((number) => (
          <button
            key={number}
            type="button"
            aria-current={number === current ? "page" : undefined}
            onClick={() => setPage(number)}
          >
            {number}
          </button>
        ))}
        <button type="button" disabled={current === pageCount} onClick={() => setPage(current + 1)}>
          Next
        </button>
      </nav>
      <p role="status">
        Page {current} of {pageCount}
      </p>
    </div>
  );
}
