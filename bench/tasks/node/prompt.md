Create a small Express HTTP API in this folder, in plain JavaScript (ES modules, Node 24, no TypeScript), that takes table reservations for our restaurant.

`app.js` default-exports the Express app without listening; `server.js` starts it on `PORT` (default 3000). The one endpoint is `POST /reservations` with a JSON object body: `name` (a string, at most 100 characters once trimmed, not blank), `email` (a string shaped `local@domain.tld`: exactly one `@`, no whitespace, a dot in the domain), `partySize` (a JSON integer from 1 to 12; the string `"4"` is invalid) and `date` (`YYYY-MM-DD`, a day that exists on the calendar: `2026-02-29` is invalid).

A valid body gets `201` and the reservation as JSON with exactly these fields: a unique positive integer `id`, the trimmed `name`, `email`, `partySize` and `date`. An invalid one gets `400` and `{"errors": {...}}` with one message per invalid field, keyed by the field name, every invalid field at once. A body that is not a JSON object, malformed JSON included, gets `400` and `{"errors": {"body": "..."}}` as JSON too, never an HTML error page.

Work autonomously: nobody will answer questions.
