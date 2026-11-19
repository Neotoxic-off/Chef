# Linux servers (systemd, users, packages, logs, firewall, SSH)

Verified against systemd 262, OpenSSH 10.6p2 (Nov 2026).

## Lint and validate

- Units: `systemd-analyze verify app.service`; hardening score: `systemd-analyze security app.service` (`--offline=yes` on a unit file in CI).
- SSH: `sshd -t` before every reload. Sudo: `visudo -c`. nftables: `nft -c -f /etc/nftables.conf`.
- Shell scripts: ShellCheck (see `bash.md`).
- Use what the distro ships; check with `systemctl --version`, `ssh -V`.

## Practices

- Every long-running process is a systemd unit. No `nohup`, no `screen`, no cron `@reboot`.
- Edit vendor units with drop-ins (`systemctl edit app`), never in `/usr/lib/systemd`.
- `Restart=on-failure`, `Type=notify` or `exec` when the app supports it; timers instead of cron for new jobs.
- Config in `/etc/<app>`, state in `/var/lib/<app>` (`StateDirectory=`), logs to stdout/stderr.
- Packages: install from the distro repo first. Third-party repos get a key in `/etc/apt/keyrings` with `signed-by=`; `apt-key` is deprecated. `--no-install-recommends`.
- Enable automatic security updates (`unattended-upgrades`, `dnf-automatic`) and plan reboots for kernel updates.
- Logs go to journald: `journalctl -u app -b -p warning`. Set `SystemMaxUse=` in `journald.conf`; ship logs off the host.

```ini
[Service]
ExecStart=/usr/local/bin/app
DynamicUser=yes
StateDirectory=app
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
SystemCallFilter=@system-service
CapabilityBoundingSet=
LockPersonality=yes
MemoryDenyWriteExecute=yes
```

## Security

- Least privilege: one system user per service (`DynamicUser=yes`, or `useradd --system --shell /usr/sbin/nologin app`). Never run a service as root.
- Grant only the capability needed (`AmbientCapabilities=CAP_NET_BIND_SERVICE`), not root.
- Files: config `0640 root:app`, secrets `0600`, never world-readable. Use `LoadCredential=` for secrets, not `Environment=`.
- Sudo: named rules for named commands in `/etc/sudoers.d/`; no `NOPASSWD: ALL`.
- Firewall default deny inbound (nftables, `ufw`, or `firewalld`); open only the ports you serve. Restrict SSH to admin networks.
- SSH in a drop-in (`/etc/ssh/sshd_config.d/`): `PermitRootLogin no`, `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `AllowGroups ssh-users`. Ed25519 keys only. Audit with `ssh-audit`.
- Keep an open session while you change SSH or firewall rules; test a new login before you close it.

## Tests

- CI: `systemd-analyze verify` and `systemd-analyze security --offline=yes` on every unit; fail when the exposure score goes up.
- Provisioning code (Ansible, cloud-init) runs against a throwaway VM or container in CI; assert the service is `active` and answers its health check.
- After a change: `systemctl is-active app`, `journalctl -u app -b -p err` is empty, `ss -tlnp` shows only expected listeners.
