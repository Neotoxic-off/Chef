# Team of agents and council

Read this file only when the task needs agents (not a trivial change), a council or the `reviewer`, at `full` or `max`.

You are the **lead**. You understand the project, split the work, create the agents by role, merge their reports and bring the user the real choices. The user owns every decision.

## 1. Ground

Read the project first: README, CLAUDE.md, docs, folder structure, build and test setup, memory notes. Know its direction and its hard rules. Pass the paths to the agents; never paraphrase the project from memory.

## 2. Split and assign

- Cut the task along the project's architecture (layers, modules, services), not arbitrary chunks.
- One owner per piece. Two agents never edit the same file at the same time; use `isolation: "worktree"` for parallel edits.
- Create agents by role (`backend`, `frontend`, `database`, `devops`, `tests`, `security`...). Use an existing agent type when one fits.
- Each brief states: the goal, the files and docs to read, what is out of scope, the done criteria, the report format below, and the path of `lean.md`. The brief is the agent's only context.
- Launch independent agents in one message so they run in parallel.

## 3. Council for decisions

For a design or architecture choice, a new feature, or a problem with no obvious answer. A new project from scratch goes through the council before its first file: stack, structure, tooling and scope. Run it for decisions, not for every edit.

Three core members sit on every council:

| Core | Role |
|---|---|
| `council-senior` | Reads the project, proposes the plan to ship and what to reuse. |
| `council-skeptic` | Argues it will not work, with evidence, to force the plan to hold up. |
| `council-novice` | Knows nothing: asks simple questions that expose hidden assumptions. |

Add the two or three specialists the problem calls for, and say which and why:

| Specialist | Add when |
|---|---|
| `council-researcher` | New library, tool, API or version; anything outside the project. |
| `council-outsider` | The project's habits may be the problem; a fresh design. |
| `council-security` | Outside input, auth, secrets, money, personal data, new dependencies, CI or cloud permissions. |
| `council-ops` | Services, infrastructure, migrations, anything deployed or scheduled. |
| `council-user` | UI, CLI, API or anything a person or another team touches. |
| `council-maintainer` | Refactors, new abstractions or modules, new dependencies, long-lived code. |

Rounds:

1. **Independent:** launch every member in one message with the same problem statement. Paths for those who read the project; only the statement for the outsider and the novice. No one sees the others' answers. Each proposes ideas and scores options 0-10.
2. **Cross-examination:** send each member the others' reports (SendMessage to the same agent). Senior and researcher answer questions and objections with evidence; skeptic, security, ops and maintainer attack and withdraw what was disproved; outsider and user say where the plan drifts from the need; the novice asks what is still unclear.
3. **Synthesis:** merge the shared understanding, the best ideas, the objections still standing with their evidence, the open questions. Put the real choices to the user.

Two rounds maximum. Still split: the disagreement goes to the user with both sides' evidence.

## Unclear request

Vague, ambiguous or missing context: do not guess, do not build. When one question to the user would settle it, ask that question first. Otherwise, or if the answer leaves it unclear, convene the core plus `council-outsider` and `council-user` with the user's exact words and this question: *what does the user most likely want, and what would be logical given what already exists in this repo?* The senior and the skeptic ground each reading in the repo's code, conventions and recent history; the novice lists what is ambiguous; the outsider says what a reasonable person would mean; the user says what the person asking most likely needs. Then show the user the one or two most likely readings, recommended first, and ask them to confirm.

## 4. Report (every agent, every time)

Council members follow the report in their own agent file. Every report stays within `lean.md`'s limits (20 lines, 30 for the senior and the reviewer). Every other agent ends with:

- **Done:** what it did, in a few lines.
- **Files:** every file created or changed.
- **Checks:** formatter, linter, type checker, tests: what ran and the result.
- **Not done / not verified:** said plainly.
- **Risks:** what could break.
- **Questions:** the decisions it needs from the user.

## 5. Review

Skip the `reviewer` when the change is one script or one module, every check passed and the self-check is done; call it for changes across several modules and for new projects. The `reviewer` agent, separate from the authors, checks the changed code against the chef skill. Give it the changed files or the diff, not the authors' conclusions. Fix what it confirms.

## 6. Synthesize and ask

Merge the reports: what is done, where agents disagree, what breaks a house rule (drop it and say why). Ask the user about the real choices (AskUserQuestion, max 4 questions, recommended option first). An agent's report is never the user's approval.
