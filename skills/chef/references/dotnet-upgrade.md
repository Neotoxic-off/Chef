# .NET upgrade: .NET Framework to .NET, and .NET majors

Builds on `csharp.md`. Verified against the .NET release index (10.0.15 LTS, 11.0.0 STS; 8.0 and 9.0 out of support since 10 Nov 2026), the `dotnet package list` docs and the Microsoft Learn porting pages (Nov 2026).

## When it applies

- A `.csproj` targets `net4x` (`<TargetFrameworkVersion>` or a non-SDK-style project), or `netcoreapp*` / `net5.0`-`net9.0`.
- Target: .NET 10 (LTS, supported to Nov 2028). Pick .NET 11 (STS) only if the user asks.

## Tools: what is current

- **Current:** GitHub Copilot upgrade agent (Visual Studio 2026, Visual Studio 2022 17.14.16+, VS Code, GitHub Copilot CLI) and the `modernize` CLI (`modernize upgrade ".NET 10"`). Paths: .NET Framework, .NET Core 1.x-3.x and .NET 5+ to .NET 8 or later. It is an AI agent, not a deterministic tool: it needs a Copilot license and sends code to an LLM. Ask the user before using it.
- **Deprecated:** .NET Upgrade Assistant ("officially deprecated", Learn: `dotnet/core/porting/upgrade-assistant-overview`). The .NET Portability Analyzer (API Port) is deprecated and its service shut down.
- **Archived:** `try-convert` (GitHub repo archived 17 May 2024). Do not use.
- No tool named `dotnet-upgrade` exists in Microsoft's docs.

Deterministic tools to run first:

```sh
dotnet package list --outdated
dotnet package list --deprecated
dotnet package list --vulnerable --include-transitive
```

(`dotnet package list` is the .NET 10 form; older SDKs use `dotnet list package`.)

## Steps, one batch per commit

1. Baseline on the old target: `dotnet build` and `dotnet test` run, failures and coverage recorded. Fix nothing else.
2. .NET Framework only: convert each project to SDK-style, still targeting `net4x`, leaves first (libraries before apps). Build and test after each project.
3. Upgrade or replace packages with no .NET support, one package per batch, still on the old target.
4. Libraries: multi-target (`<TargetFrameworks>net48;net10.0</TargetFrameworks>`) when apps still on .NET Framework consume them. Apps: switch `<TargetFramework>` to `net10.0`.
5. Set the SDK in `global.json`. Read "Breaking changes in .NET N" (`learn.microsoft.com/dotnet/core/compatibility/<N>`) for every major crossed, and fix each hit.
6. .NET majors (e.g. 8 to 10): one project or one layer per batch, same order.

Validation per batch: `dotnet build` (warnings stay errors), `dotnet test`, `dotnet format --verify-no-changes`.

## Pitfalls

- Not available on .NET (Learn: "technologies unavailable"): creating AppDomains, .NET Remoting, code access security, `System.EnterpriseServices` (COM+), Workflow Foundation (see CoreWF), WCF server (see CoreWCF). ASP.NET MVC, Web API and Web Forms (`System.Web`) move to ASP.NET Core; Learn recommends an incremental migration for production apps.
- Windows-only APIs (registry, WMI, performance counters, Windows services): the `Microsoft.Windows.Compatibility` package (new dependency: ask the user first), or replace them.
- `packages.config` to `PackageReference`; `app.config` / `web.config` settings move to `appsettings.json` and the options pattern.
- New analyzers in a new SDK raise new warnings: fix their cause, never lower `AnalysisLevel`.
- Diff holds only the migration: no `var` to explicit-type sweeps, no reformatting of files the batch did not touch.

## Leave for the user

- ASP.NET (MVC / Web Forms) to ASP.NET Core, WCF to CoreWCF or gRPC, WF to CoreWF: rewrites, not upgrades. Present options, do not start them.
- Choosing .NET 10 vs 11, and replacing packages that have no .NET version.
- Using the Copilot agent or `modernize` CLI (license, code leaves the machine).
