# Nix (flakes, devShells, NixOS modules)

## Lint and validate

- `nix flake check` in CI: it evaluates every output and runs `checks`.
- Format with `nixfmt` (the official formatter, RFC 166): `nixfmt --check <files>` in CI; set `formatter` in the flake so `nix fmt` works locally (`pkgs.nixfmt-tree` wraps it for a whole tree; unverified on older nixpkgs).
- Lint with `statix check .` and `deadnix --fail .`. Fix findings; no `# statix:skip`-style suppressions.
- Before a switch: `nixos-rebuild build --flake .#host`, then `nixos-rebuild test` (no boot entry) before `switch`.

## Practices

- Versions checked Nov 2026: Nix 2.35, NixOS 26.05 (supported to 2026-12-31; 26.11 due next). Look up the current one at nixos.org/manual and `nix --version`.
- Flakes are still an experimental feature in upstream Nix: enable `experimental-features = nix-command flakes` in `nix.conf`. Determinate Nix ships them stable.
- Commit `flake.lock`. Update inputs on a schedule in a PR (`nix flake update`, or the `update-flake-lock` action), never silently.
- Pin `nixpkgs` to a release branch (`nixos-26.05`) for servers; `nixos-unstable` only for dev machines.
- Make inputs share one nixpkgs: `inputs.foo.inputs.nixpkgs.follows = "nixpkgs";`.
- Dev environments are `devShells`; load them with direnv (`use flake`). Put every tool the project needs there, with versions from the lock.
- Do not change `system.stateVersion` on an existing machine; it is not the NixOS version.

```nix
{ config, lib, pkgs, ... }:
let cfg = config.services.myapp;
in {
  options.services.myapp = {
    enable = lib.mkEnableOption "myapp";
    port = lib.mkOption { type = lib.types.port; default = 8080; };
  };
  config = lib.mkIf cfg.enable {
    systemd.services.myapp = {
      wantedBy = [ "multi-user.target" ];
      serviceConfig = {
        ExecStart = "${pkgs.myapp}/bin/myapp --port ${toString cfg.port}";
        DynamicUser = true;
        NoNewPrivileges = true;
        ProtectSystem = "strict";
      };
    };
  };
}
```

- Modules: typed options (`lib.types.*`), `mkEnableOption`, all config under `lib.mkIf cfg.enable`. Use `mkDefault` and `mkForce` sparingly.
- Prefer packages and modules from nixpkgs over custom derivations; upstream fixes you need.

## Security

- The Nix store is world-readable. Never put a secret in a derivation, a module option string or `builtins.readFile` of a secret. Use sops-nix or agenix, which decrypt at activation to a `0400` file.
- Harden services in `serviceConfig` like any systemd unit (see `linux.md`); keep `networking.firewall.enable = true` (default) and open only needed ports.
- Use only trusted binary caches with their public keys in `trusted-public-keys`; do not add users to `trusted-users` unless needed.
- `nix flake update` brings in new code: review the lock diff like a dependency bump.

## Tests

- Put builds, formatters and linters in `checks` so `nix flake check` runs them all.
- NixOS VM tests for modules: `pkgs.testers.runNixOSTest` boots machines and runs a Python test script (`machine.wait_for_unit("myapp.service")`, `machine.succeed("curl -f localhost:8080/health")`).
- CI builds every `nixosConfigurations.<host>.config.system.build.toplevel` before deploy.
