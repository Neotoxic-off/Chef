# Ansible

Verified against ansible-core 2.22, ansible-lint 26.11, Molecule 26.11 (Nov 2026).

## Lint and validate

- ansible-lint in CI with the `production` profile; warnings fail the build.
- yamllint runs as part of ansible-lint; keep its config in the repo.
- `ansible-playbook --syntax-check site.yml` for every playbook.
- `ansible-playbook --check --diff` against staging before a real run.

`.ansible-lint`:

```yaml
profile: production
strict: true
exclude_paths:
  - .cache/
  - collections/
```

## Practices

- Every task is idempotent: a second run reports `changed=0`. Prefer modules over `command`/`shell`.
- When you must use `command`/`shell`, add `creates:`/`removes:` or `changed_when:`/`failed_when:`.
- Use fully qualified collection names: `ansible.builtin.copy`, `community.general.ufw`, never bare `copy`.
- Name every task and play in the imperative ("Install nginx"); names show in logs.
- Roles with one job each; defaults in `defaults/main.yml`, an `meta/argument_specs.yml` for every role input.
- Pin collections and roles with versions in `requirements.yml`; install with `ansible-galaxy install -r requirements.yml`.
- Use handlers for restarts, not `when: result.changed` chains.
- Use `ansible.builtin.template` with Jinja2 for config files; no `lineinfile` edits of whole files.
- Variables are prefixed with the role name (`nginx_port`) to avoid collisions.

## Security

- Secrets live in Ansible Vault (`ansible-vault encrypt_string`) or an external store (HashiCorp Vault, cloud secret manager lookups). Never plain text in the repo.
- Keep the vault password out of the repo: `--vault-password-file` pointing to a script that reads a secret manager.
- `no_log: true` on tasks that handle secrets.
- `become` only on the tasks that need it, not the whole play.
- Pin SSH host keys (`known_hosts`); do not disable host key checking in production.

## Tests

- Test every role with Molecule: `molecule test` runs create, converge, idempotence, verify and destroy.
- The idempotence step must pass: a second converge with any `changed` task fails the test.
- Write `verify.yml` (Ansible asserts) or testinfra checks for the real outcome: package installed, service running, port open.
- Run Molecule with the Docker or Podman driver in CI, on every OS/version the role supports.
