const MS_PER_SECOND = 1000;
const MS_PER_MINUTE = 60 * MS_PER_SECOND;
const MS_PER_HOUR = 60 * MS_PER_MINUTE;
const MS_PER_DAY = 24 * MS_PER_HOUR;
const MAX_DURATION_MS = 30 * MS_PER_DAY;

// Each unit is optional and appears once, largest to smallest, so the
// pattern itself rejects repeated or misordered units.
const DURATION_PATTERN = /^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?(?:(\d+)ms)?$/;
const UNIT_MS: readonly number[] = [MS_PER_DAY, MS_PER_HOUR, MS_PER_MINUTE, MS_PER_SECOND, 1];

export function parseDuration(text: string): number {
  const trimmed = text.trim();
  if (trimmed === "") {
    throw new Error("Invalid duration: input is empty");
  }
  const match = DURATION_PATTERN.exec(trimmed);
  if (match === null) {
    throw new Error(
      `Invalid duration "${trimmed}": expected whole-number parts such as 1h30m, ` +
        "with units d, h, m, s, ms, each used once, largest to smallest, no separators or signs",
    );
  }
  const total = UNIT_MS.reduce((sum, unitMs, index) => sum + Number(match[index + 1] ?? 0) * unitMs, 0);
  if (total <= 0) {
    throw new Error(`Invalid duration "${trimmed}": total must be greater than 0`);
  }
  if (total > MAX_DURATION_MS) {
    throw new Error(`Invalid duration "${trimmed}": total must be at most 30 days`);
  }
  return total;
}
