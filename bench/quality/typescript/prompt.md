Write a TypeScript library `src/semver.ts` exporting `compare(a: string, b: string): -1 | 0 | 1` for semantic versions `MAJOR.MINOR.PATCH` with an optional pre-release (`1.2.3-beta.1`), ordered as the SemVer 2.0 spec says (pre-release below release, numeric identifiers compared as numbers). A malformed version throws `RangeError` naming it. Node 24, ES modules.

Work autonomously: nobody will answer questions.
