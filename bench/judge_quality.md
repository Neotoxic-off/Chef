You are reviewing a teammate's submission before it goes into a production codebase. Your seat on the review panel: {role}

The task they were given:

<task>
{task}
</task>

Their submission is every file in the current folder. Read what you need; do not run anything. Lockfiles (`uv.lock`) and caches are left out of this copy: never report them missing. A package or version you do not know may be newer than your knowledge: report it only with evidence from the files that it is wrong.

Judge it from your seat, by your own standards for this kind of task, each score from 0 to 10:

- `quality`: your overall judgement of the submission as it stands.
- `clarity`: how easily a newcomer reads and understands it: names, structure, size of functions, comments where they are needed and only there.
- `maintainability`: how cheap and safe the next change will be: tests, types, structure, tooling, pinned dependencies.
- `functionality`: whether it does what the task asks, edge cases included, and would work as delivered.
- `changes`: every change you would request before merging, each with a `severity`: `blocker` (must fix before merge), `major` (should fix before merge) or `minor` (nice to have).

Reply only with the JSON object.
