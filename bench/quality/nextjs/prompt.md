In a Next.js 16 App Router project, write the route handler `app/api/shorten/route.ts`: `POST` with JSON `{ "url": string }` returns 201 and `{ "code": string }`, a 7-character code stored in an in-memory map; `GET /api/shorten?code=...` returns 302 to the stored URL or 404. Only `http` and `https` URLs up to 2048 characters are accepted, otherwise 400 with `{ "error": string }`.

Work autonomously: nobody will answer questions.
