You are reviewing a teammate's submission before it goes into a production codebase. Your seat on the review panel: {role}

The task they were given:

<task>
{task}
</task>

Their submission is every file in the current folder. Read what you need; do not run anything.

Judge it from your seat, by your own standards for this kind of task:

- `correctness`: 0-10, does it do what the task asks, including edge cases.
- `quality`: 0-10, your overall judgement of the submission as it stands.
- `merge_as_is`: would you merge it without changes.
- `changes`: every change you would request before merging, each with a `severity`: `blocker` (must fix before merge), `major` (should fix before merge) or `minor` (nice to have).

Reply only with the JSON object.
