# Unity

Builds on `csharp.md` for style and naming, with Unity's limits. Written for the Unity 6.6 manual (C# compiler page, Roslyn analyzers and rulesets) and the Code Coverage package docs (Nov 2026), not benchmarked. Current version: Unity Hub or the "Unity 6 releases" page; pin it in `ProjectSettings/ProjectVersion.txt`.

## What differs from `csharp.md`

- Unity compiles C# 9 against .NET Standard 2.1 / .NET Framework profiles: no file-scoped namespaces, no `required`, no `ArgumentNullException.ThrowIfNull`. Write guard checks by hand.
- Unity's compiler does not run the IDE rules (IDE0007, IDE0008): the `var` rule from `csharp.md` is checked by the IDE (Rider, Visual Studio) and review. Commit the `.editorconfig` from `csharp.md` anyway.
- Rulesets and `.editorconfig` severities do apply to Roslyn analyzers: `Assets/Default.ruleset` for all assemblies, or one ruleset per assembly next to its `.asmdef`.
- Warnings as errors: `-warnaserror+` in a `csc.rsp` (or Player Settings > Additional Compiler Arguments). Nullable: `-nullable:enable` in the `csc.rsp` next to an `.asmdef`. Both come from community sources: verify in your Unity version before relying on them.
- Records: never in serialized types (Unity serialization does not support them).

## Structure

- One `.asmdef` per feature (`Shop.Gameplay`, `Shop.UI`) plus `Editor` and `Tests` assemblies. It speeds compiles and makes dependencies explicit.
- Game rules in plain C# classes with no `UnityEngine` dependency, injected into thin `MonoBehaviour`s. They test in EditMode without a scene.
- Tuning values in `ScriptableObject` assets or named constants, never literals in code.
  ```csharp
  public sealed class Health : MonoBehaviour
  {
      private const float DefaultMaxHealth = 100f;

      [SerializeField] private float _maxHealth = DefaultMaxHealth;
      private HealthPool _pool;

      private void Awake() => _pool = new HealthPool(_maxHealth);
  }
  ```
- `[SerializeField] private` fields, never public fields for the Inspector.

## Unity-specific code rules

- `UnityEngine.Object` overrides `==`: never use `?.`, `??` or `is null` on components or GameObjects; a destroyed object passes those checks. Use `if (target != null)` or `TryGetComponent`.
- Use `Microsoft.Unity.Analyzers` (Microsoft's Unity analyzer set; how your IDE package bundles it is not verified here): it flags the case above and suppresses false "unused" warnings on Unity messages (`Update`, `Awake`).
- Cache `GetComponent` results in `Awake`; no `Find*`, `GetComponent` or allocations in `Update`.
- Async: `Awaitable` with `destroyCancellationToken`, not `async void` or coroutines in new code.
- Input: the Input System package, not the legacy `Input` class, in new code.

## Tests

- Unity Test Framework (NUnit). EditMode tests for logic, PlayMode tests only for behavior that needs the engine loop. Names: `ApplyDamage_MoreThanCurrent_ClampsToZero`.
  ```csharp
  [Test]
  public void ApplyDamage_MoreThanCurrent_ClampsToZero()
  {
      HealthPool pool = new HealthPool(FullHealth);

      pool.ApplyDamage(Overkill);

      Assert.That(pool.Current, Is.Zero);
  }
  ```
- Coverage with the Code Coverage package (`com.unity.testtools.codecoverage`, OpenCover output):
  ```sh
  Unity -batchmode -projectPath . -runTests -testPlatform EditMode -enableCodeCoverage \
    -coverageOptions "generateHtmlReport;assemblyFilters:+Shop.*" -testResults editmode.xml
  ```
  The package reports; it does not fail the run. CI must parse the report and fail under 90%; tell the user if no such gate exists.
- Mutation testing: no Unity-integrated tool verified. If the user wants it, build the engine-free logic as a normal .NET project and run Stryker.NET there.
