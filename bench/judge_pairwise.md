Two teammates were given the same task and each submitted a solution. You decide which one goes into a production codebase.

The task they were given:

<task>
{task}
</task>

The two submissions are the folders `first/` and `second/` in the current folder. Read what you need; do not run anything.

Review both as a panel would, by your own standards for this kind of task: a senior engineer (design and correctness), a security reviewer, an SRE who will run it, and the engineer who will maintain it for two years.

- `winner`: `first`, `second`, or `tie` if neither is clearly better.
- `first_merge_as_is`, `second_merge_as_is`: would you merge that submission without changes.
- `first_major_changes`, `second_major_changes`: how many changes you would require before merging each one.
- `reason`: two sentences at most.

Reply only with the JSON object.
