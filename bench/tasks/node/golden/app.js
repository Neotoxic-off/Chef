import express from "express";

const MAX_NAME_LENGTH = 100;
const MAX_PARTY_SIZE = 12;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

export function isCalendarDate(text) {
  const match = DATE_PATTERN.exec(text);
  if (match === null) {
    return false;
  }
  const [year, month, day] = match.slice(1).map(Number);
  const date = new Date(0);
  // setUTCFullYear, unlike Date.UTC, does not map years 0-99 to 1900-1999.
  date.setUTCFullYear(year, month - 1, day);
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

export function validateReservation(body) {
  const errors = {};
  const name = typeof body.name === "string" ? body.name.trim() : "";
  if (name === "" || name.length > MAX_NAME_LENGTH) {
    errors.name = `must be 1 to ${MAX_NAME_LENGTH} characters`;
  }
  if (typeof body.email !== "string" || !EMAIL_PATTERN.test(body.email)) {
    errors.email = "must be an email address";
  }
  if (!Number.isInteger(body.partySize) || body.partySize < 1 || body.partySize > MAX_PARTY_SIZE) {
    errors.partySize = `must be an integer from 1 to ${MAX_PARTY_SIZE}`;
  }
  if (typeof body.date !== "string" || !isCalendarDate(body.date)) {
    errors.date = "must be a calendar date as YYYY-MM-DD";
  }
  return errors;
}

const app = express();
let nextId = 1;

app.use(express.json());

app.post("/reservations", (req, res) => {
  const body = req.body;
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    res.status(400).json({ errors: { body: "must be a JSON object" } });
    return;
  }
  const errors = validateReservation(body);
  if (Object.keys(errors).length > 0) {
    res.status(400).json({ errors });
    return;
  }
  const { email, partySize, date } = body;
  res.status(201).json({ id: nextId++, name: body.name.trim(), email, partySize, date });
});

// Four parameters: Express only treats a four-argument function as an error handler.
app.use((error, req, res, next) => {
  if (error.type === "entity.parse.failed") {
    res.status(400).json({ errors: { body: "must be valid JSON" } });
    return;
  }
  next(error);
});

export default app;
