# .NET MAUI

Builds on `csharp.md` (project settings, `.editorconfig`, tests). Written for the .NET MAUI 10 docs on compiled bindings, Microsoft.Maui.Controls 11.0.10 and CommunityToolkit.Mvvm 8.4.2 on NuGet (Nov 2026), not benchmarked. Current versions: `dotnet workload list`, `dotnet package search Microsoft.Maui.Controls --exact-match`.

## Project settings

```xml
<PropertyGroup>
  <MauiStrictXamlCompilation>true</MauiStrictXamlCompilation>
  <MauiEnableXamlCBindingWithSourceCompilation>true</MauiEnableXamlCBindingWithSourceCompilation>
  <WarningsAsErrors>$(WarningsAsErrors);XC0022;XC0023;XC0025</WarningsAsErrors>
</PropertyGroup>
```

- XC0022 and XC0023 stay silent unless `MauiStrictXamlCompilation` is `true`; it is `false` by default except for full-trim and NativeAOT publishes.
- Never fix a binding warning with `x:DataType="x:Object"` or `NoWarn`: both turn compiled bindings off and hide the bug.

## MVVM: CommunityToolkit.Mvvm (house rule)

- Same rules as WPF/WinUI in `csharp.md`: `partial` ViewModels on `ObservableObject`, `[ObservableProperty]`, `[RelayCommand]`, `WeakReferenceMessenger`. No hand-written `INotifyPropertyChanged` or `ICommand`.
- ViewModels never reference `Microsoft.Maui.*` UI types; inject platform services (`IConnectivity`, `IPreferences`, `ISecureStorage`) as interfaces so tests replace them.
- Every page and every `DataTemplate` declares `x:DataType`:
  ```xml
  <ContentPage xmlns:vm="clr-namespace:Shop.ViewModels" x:DataType="vm:ProfileViewModel">
      <VerticalStackLayout>
          <Entry Text="{Binding Name}" />
          <Button Text="Save" Command="{Binding SaveCommand}" />
      </VerticalStackLayout>
  </ContentPage>
  ```
- Pages get their ViewModel through the constructor; register both in `MauiProgram`:
  ```csharp
  builder.Services.AddTransient<ProfileViewModel>();
  builder.Services.AddTransient<ProfilePage>();
  ```
- `CommunityToolkit.Maui` (behaviors, converters, popups) is pre-approved like `CommunityToolkit.Mvvm`: add it without asking.

## UI and platform

- Navigation with Shell routes. Receive parameters through `IQueryAttributable`; `[QueryProperty]` relies on reflection and is not trim-safe.
- `CollectionView` for lists, `Border` instead of `Frame`, `Grid` instead of nested stack layouts. Do not add new uses of APIs the build marks obsolete.
- Platform code in `Platforms/<OS>/` or partial classes per platform, not `#if` blocks scattered through shared code.
- Secrets and tokens: `SecureStorage`. `Preferences` holds only non-sensitive settings.
- Sizes, spacing and colors in `Resources/Styles` as named resources, never literals in pages.
- Accessibility: `SemanticProperties.Description` on images and icon buttons; `SemanticProperties.HeadingLevel` on headings.

## Tests

- Put ViewModels and services in a class library that targets plain `net10.0` (no platform TFM), so the xUnit v3 test project from `csharp.md` can reference and run it on any CI agent.
- Test names: `Save_WithBlankName_CannotExecute` (CA1707 already off for test projects).
- Assert commands through the generated members: `viewModel.SaveCommand.CanExecute(null)`, `await viewModel.SaveCommand.ExecuteAsync(null)`.
- UI flows: Appium-driven tests per platform, locating elements by `AutomationId`. Keep them few; logic coverage comes from ViewModel tests.

Order before done: `dotnet format --verify-no-changes` then `dotnet build -warnaserror` for each target framework you ship, then `dotnet test`.
