# Config files (YAML, JSON, TOML)

## Lint and validate

- YAML: `yamllint --strict .` in CI (warnings fail).
- Every config with a schema gets validated against it: `check-jsonschema --schemafile schema.json config.yaml`. Known formats have built-ins: `check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/*.yml`.
- Your own schemas: `check-jsonschema --check-metaschema schema.json`.
- TOML: Taplo (`taplo fmt --check`, `taplo check`, `taplo check --schema <url>`) or Tombi (`tombi format`, `tombi lint`; check-mode flags unverified). Pick one per repo.
- Format JSON and YAML with one formatter (Prettier, or the language's own) and run it in check mode in CI.
- Versions checked Nov 2026: yamllint 1.38, check-jsonschema 0.39, Taplo 0.10 (last release May 2025), Tombi 1.11. Check PyPI and the GitHub releases pages.

`.yamllint.yaml`:

```yaml
extends: default
rules:
  line-length:
    max: 120
  truthy:
    allowed-values: ["true", "false"]
    check-keys: true
  document-start: disable
```

## Practices

- Declare the schema in the file so editors validate too: `# yaml-language-server: $schema=<url>` (YAML), `"$schema": "<url>"` (JSON), `#:schema <url>` (TOML, Taplo and Tombi).
- Use SchemaStore (`schemastore.org`) schemas for common tools; write your own for app config.
- Write schemas in JSON Schema 2020-12: `"$schema": "https://json-schema.org/draft/2020-12/schema"`, `required` for mandatory keys, `additionalProperties: false` so typos fail.
- Validate app config at startup against the same schema or typed model; fail fast with a clear message.
- YAML: quote strings that look like other types (`"no"`, `"on"`, `"1.10"`, `"0755"`). Use `true`/`false` only for booleans.
- YAML: avoid anchors and merge keys (`<<:`) across large files; they hide where a value comes from.
- JSON has no comments: use JSONC or JSON5 only where the consuming tool says it supports them.
- Keep one source of truth: generate derived files, do not hand-copy values between them.
- Stable key order and 2-space indent for JSON/YAML; the formatter decides, not people.

## Security

- No secrets in config files under Git. Reference env vars or a secret manager; scan commits with `gitleaks` or `trufflehog`.
- Parse YAML with a safe loader only (`yaml.safe_load`, not `yaml.load` with a full loader): unsafe loaders can build arbitrary objects.
- Limit the size and depth of untrusted JSON/YAML before parsing; YAML alias bombs can exhaust memory.
- Fetch remote schemas over HTTPS, or vendor and pin them in the repo so CI does not depend on the network.

## Tests

- CI runs lint, format check and schema validation on every changed config file (pre-commit hooks: `yamllint`, `check-jsonschema`).
- Test your schemas: one valid fixture passes, each invalid fixture (missing key, wrong type, unknown key) fails.
- Test that the app refuses an invalid config at startup with a clear error.
