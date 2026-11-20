# C# / .NET / WPF / WinUI

Verified against .NET 10 (`net10.0`) and xUnit v3 (Nov 2026).

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
- `.editorconfig` must enforce the house rules and turn off the analyzer rule that contradicts them:
  ```ini
  [*.cs]
  csharp_style_var_for_built_in_types = false:warning
  csharp_style_var_when_type_is_apparent = true:warning
  csharp_style_var_elsewhere = false:warning

  [{*Tests,**/*Tests}/**.cs]
  # test names are Method_Condition_Result, which CA1707 rejects
  dotnet_diagnostic.CA1707.severity = none
  # xUnit v3 test projects are Exe, so CA1515 wants internal types, but test classes and fixtures must be public
  dotnet_diagnostic.CA1515.severity = none
  ```
  Underscore test names build in `X.Tests` projects (verified with .NET 10).
- Central package versions: `Directory.Packages.props`.

## Code

- `var` when the type is apparent on the right side (`var users = new List<User>();`), explicit types otherwise: `decimal subtotal = 0m;` (built-in type), `Order order = repository.Find(id);` (elsewhere). `var` there fails the build with IDE0008.
- Nullable reference types on. No `!` null-forgiving operator: it hides a warning. Narrow with a null check or fix the type.
- `async` all the way: `Task`/`ValueTask`, pass `CancellationToken`, never `.Result` or `.Wait()`. Async method names end in `Async`.
- `sealed` classes by default, `record` for immutable data, `readonly` fields.
- Dependency injection through `Microsoft.Extensions.DependencyInjection` constructors. Wrap time in `TimeProvider`.
- Throw specific exceptions. Use guard helpers: `ArgumentNullException.ThrowIfNull(x)`.

## WPF / WinUI / MAUI / Avalonia: CommunityToolkit, always

`CommunityToolkit.Mvvm` in every such project (plus `CommunityToolkit.Maui` in MAUI). Pre-approved: add it without asking.

- ViewModels inherit `ObservableObject` (or `ObservableValidator` / `ObservableRecipient`) and are `partial`.
- Properties: `[ObservableProperty]`. Commands: `[RelayCommand]` (async gives `IAsyncRelayCommand`). Never hand-write `INotifyPropertyChanged`, `SetProperty` boilerplate or a custom `ICommand`.
- Dependent updates: `[NotifyPropertyChangedFor]`, `[NotifyCanExecuteChangedFor]`. Messaging: `WeakReferenceMessenger`. Validation: `ObservableValidator` with data annotations.
- WinUI: `CommunityToolkit.WinUI.*` controls and helpers before writing your own.
- Code-behind holds only view logic. ViewModels have no reference to UI types, so they are unit-testable without a window.

```csharp
public partial class MainViewModel : ObservableObject
{
    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(SaveCommand))]
    private string _name = string.Empty;

    [RelayCommand(CanExecute = nameof(CanSave))]
    private async Task SaveAsync(CancellationToken token) { /* ... */ }

    private bool CanSave() => !string.IsNullOrWhiteSpace(Name);
}
```

## Tests

- Framework: xUnit v3. One test project per production project: `X.Tests` (unit), `X.IntegrationTests`.
- .NET 10+: use Microsoft.Testing.Platform. Set it in `global.json`:
  ```json
  { "test": { "runner": "Microsoft.Testing.Platform" } }
  ```
- Test project (the version goes in `Directory.Packages.props`; without `<Using Include="Xunit" />`, `[Fact]` fails with `CS0246`):
  ```xml
  <Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
      <TargetFramework>net10.0</TargetFramework>
      <OutputType>Exe</OutputType>
    </PropertyGroup>
    <ItemGroup>
      <PackageReference Include="xunit.v3.mtp-v2" />
      <Using Include="Xunit" />
    </ItemGroup>
    <ItemGroup>
      <ProjectReference Include="..\..\src\X\X.csproj" />
    </ItemGroup>
  </Project>
  ```
  Test classes and their fixtures are `public sealed`: an internal test class trips CA1812, since xUnit creates it by reflection.
- Add a package with `dotnet add tests/X.Tests package xunit.v3.mtp-v2` (there is no `-q` flag); with central versions it writes the version to `Directory.Packages.props`.
- Coverage: Microsoft's MTP code coverage extension (`dotnet test --coverage --coverage-output-format cobertura`), or `coverlet.MTP`. `coverlet.collector` does not work with MTP.
- xUnit v3 on MTP does not accept the VSTest `--filter` syntax; use xUnit's own filter options.
- Assertions: AwesomeAssertions or Shouldly. Do not add FluentAssertions 8+: it needs a paid license for commercial use.
- Mocks: NSubstitute. Integration: `Testcontainers` for databases, `WebApplicationFactory<T>` for ASP.NET Core.
- Mutation testing: Stryker.NET.
