Write a React 19 component in plain JavaScript (JSX, no TypeScript) for our admin pages: a paged list. Put it in `src/PagedList.jsx`, default-exporting `PagedList({ items, pageSize = 5 })` where `items` is an array of strings, and list `react` and `react-dom` in `package.json`.

It shows the current page's items as `<li>` elements in a `<ul>`, then a `<nav aria-label="Pagination">` holding a Previous button, one button per page labelled with its number and a Next button, then `<p role="status">Page 2 of 3</p>`. The current page's button has `aria-current="page"`; Previous has the `disabled` attribute on the first page, Next on the last. With no items it shows only the text `No items`: no list, no nav. When the parent passes a shorter `items` and the current page no longer exists, it shows the last page that does, and Previous and Next move from the page shown.

Work autonomously: nobody will answer questions.
