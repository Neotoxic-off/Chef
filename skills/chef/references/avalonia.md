# Avalonia

Builds on `csharp.md` (project settings, `.editorconfig`, tests). Written for the Avalonia 12 docs (compiled bindings, headless testing) and NuGet: Avalonia 12.1.6, Avalonia.Headless.XUnit 12.1.6 (depends on `xunit.v3.extensibility.core`), CommunityToolkit.Mvvm 8.4.2 (Nov 2026), not benchmarked. Current version: `dotnet package search Avalonia --exact-match`. Keep every `Avalonia.*` package on the same version (central `Directory.Packages.props`).

## Compiled bindings

- Avalonia 12 compiles bindings by default (`AvaloniaUseCompiledBindingsByDefault` is `true` when unset). Never set it to `false`, and never add `x:CompileBindings="False"`.
- Every view and every `DataTemplate` declares `x:DataType`; a wrong path then fails the build:
  ```xml
  <UserControl xmlns:vm="using:Shop.ViewModels" x:DataType="vm:ProfileViewModel">
      <StackPanel>
          <TextBox Text="{Binding Name}" />
          <Button Content="Save" Command="{Binding SaveCommand}" />
      </StackPanel>
  </UserControl>
  ```
- Upgrading from 11: read the "Breaking changes in Avalonia 12" page first.

## MVVM: CommunityToolkit.Mvvm

- Same rules as WPF/WinUI in `csharp.md`: `partial` ViewModels on `ObservableObject`, `[ObservableProperty]`, `[RelayCommand]`, `WeakReferenceMessenger`. Do not mix in ReactiveUI unless the project already uses it.
- ViewModels never reference `Avalonia.*` types, so they test without a UI thread. File and folder pickers, clipboard and dialogs go behind an interface the view layer implements (`IStorageProvider` lives on `TopLevel`).
- Wire ViewModels with `Microsoft.Extensions.DependencyInjection`; map ViewModels to views in one `ViewLocator` or in `DataTemplates`, not by reflection on names scattered across the code.
- Code-behind holds only view logic (focus, animation, pointer handling).

## Styling and platform

- Spacing, sizes and colors are named resources (`StaticResource` / `DynamicResource` for theme-aware values), never literals in views.
- Theme variants through `ThemeVariant` and `DynamicResource`, not separate copies of a style.
- Platform-specific code behind interfaces registered per head project (Desktop, Android, iOS, Browser).
- Accessibility: `AutomationProperties.Name` on icon-only buttons and images; every control reachable by keyboard.

## Tests

- ViewModels: plain xUnit v3 tests from `csharp.md`, names like `Save_WithBlankName_CannotExecute`.
- Views: `Avalonia.Headless.XUnit` with `[AvaloniaFact]` / `[AvaloniaTheory]`, which run the test on the Avalonia UI thread. Add the theme the app uses (`Avalonia.Themes.Fluent`): headless controls still need one.
  ```csharp
  [AvaloniaFact]
  public void SaveButton_WithBlankName_IsDisabled()
  {
      ProfileView view = new ProfileView { DataContext = new ProfileViewModel(new FakeProfileService()) };
      Window window = new Window { Content = view };
      window.Show();

      Button save = view.GetVisualDescendants().OfType<Button>().Single();
      Assert.False(save.IsEffectivelyEnabled);
  }
  ```
- Install only one headless adapter per test project.
- Coverage and mutation testing as in `csharp.md`; exclude only `*.axaml.cs` files that hold pure view wiring, with the reason in the coverage config.

Order before done: `dotnet format --verify-no-changes` then `dotnet build -warnaserror` then `dotnet test`.
