# Git

Verified against Git 2.56, pre-commit 4.7, pre-commit-hooks 6.0.0, gitleaks 8.30.1, lefthook 2.2 (Nov 2026).

## Lint and validate

- Run hooks with pre-commit (`.pre-commit-config.yaml`) or lefthook (`lefthook.yml`). Pick one per repo.
- Run the same hooks in CI (`pre-commit run --all-files` or `lefthook run pre-commit --all-files`); local hooks can be skipped.
- Lint commit messages with commitlint (`@commitlint/config-conventional`) in a `commit-msg` hook and in CI on PR titles.
- Pin every hook to a tag or SHA; update with `pre-commit autoupdate`.

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-merge-conflict
      - id: check-added-large-files
      - id: detect-private-key
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks
```

## Practices

- Conventional Commits: `type(scope): summary`, imperative, under 72 chars. Types: `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`, `perf`. Breaking change: `feat!:` or a `BREAKING CHANGE:` footer.
- Small commits, one logical change each, that build and pass tests. Body says why, not what.
- Branch names: `type/short-description` (`feat/login-rate-limit`, `fix/123-null-order`).
- Short-lived branches; rebase on the main branch before merge. Squash or rebase-merge, no merge commits in feature branches.
- Protect the main branch: PR required, required status checks, no force-push, linear history.
- Normalize line endings with `.gitattributes`; do not rely on each machine's `core.autocrlf`.

```gitattributes
* text=auto eol=lf
*.{cmd,bat,ps1} text eol=crlf
*.{png,jpg,gif,ico,pdf,zip} binary
```

- Keep `.gitignore` tight: build output, dependencies, IDE files, `.env*`.
- Large binaries go in Git LFS, not the history.

## Security

- Never commit secrets, keys, tokens or `.env` files. Commit `.env.example` with placeholders.
- Scan for secrets in the pre-commit hook and in CI over the full history: `gitleaks git --redact -v`. Enable GitHub push protection where available.
- A leaked secret is compromised: rotate it first, then rewrite history (`git filter-repo`) if needed. Removing the file is not enough.
- Sign commits and tags (SSH or GPG signing); require signed commits on protected branches if the team agrees.

## Tests

- Hooks run fast checks only (format, lint staged files, secrets). Full tests run in CI.
- Every commit on the main branch passes CI; `git bisect` depends on it.
- Check `.gitattributes` with `git ls-files --eol` after adding it, then `git add --renormalize .`.
