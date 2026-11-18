# C# / .NET / WPF / WinUI

## Project settings (`Directory.Build.props` at the repo root)

```xml
<Project>
  <PropertyGroup>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <AnalysisLevel>latest-all</AnalysisLevel>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
  </PropertyGroup>
</Project>
```

- Keep style rules in `.editorconfig`. Format with `dotnet format`; CI runs `dotnet format --verify-no-changes`.
- Central package versions: `Directory.Packages.props`.

## Code

- Explicit types, never `var` (see SKILL.md).
- Nullable reference types on. No `!` null-forgiving operator unless you prove it in a comment.
- `async` all the way: `Task`/`ValueTask`, pass `CancellationToken`, never `.Result` or `.Wait()`. Async method names end in `Async`.
- `sealed` classes by default, `record` for immutable data, `readonly` fields.
- Dependency injection through `Microsoft.Extensions.DependencyInjection` constructors. Wrap time in `TimeProvider`.
- Throw specific exceptions. Use guard helpers: `ArgumentNullException.ThrowIfNull(x)`.

## WPF / WinUI

- MVVM with CommunityToolkit (see SKILL.md). Code-behind holds only view logic.
- ViewModels have no reference to UI types, so they are unit-testable without a window.

## Tests

- Framework: xUnit v3. One test project per production project: `X.Tests` (unit), `X.IntegrationTests`.
- .NET 10+: use Microsoft.Testing.Platform. Set it in `global.json`:
  ```json
  { "test": { "runner": "Microsoft.Testing.Platform" } }
  ```
- Coverage: Microsoft's MTP code coverage extension (`dotnet test --coverage --coverage-output-format cobertura`), or `coverlet.MTP`. `coverlet.collector` does not work with MTP.
- xUnit v3 on MTP does not accept the VSTest `--filter` syntax; use xUnit's own filter options.
- Assertions: AwesomeAssertions or Shouldly. Do not add FluentAssertions 8+: it needs a paid license for commercial use.
- Mocks: NSubstitute. Integration: `Testcontainers` for databases, `WebApplicationFactory<T>` for ASP.NET Core.
- Mutation testing: Stryker.NET.
