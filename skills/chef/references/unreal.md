# Unreal Engine (C++)

Verified against Epic's C++ Coding Standard, the object pointer and Automation Spec pages, and the build configuration page on dev.epicgames.com (Nov 2026). Current engine: the Epic Games Launcher or the version selector on dev.epicgames.com; pin it in the `.uproject` (`EngineAssociation`). `cpp.md` applies only to engine-free code: its clang-tidy set does not fit UE macros and naming.

## House rules vs Epic's standard

- Epic's standard already bans `auto` except for lambdas, verbose iterators and template code, and bans structured bindings. That matches the house rule: write the type.
- Epic's naming wins inside UE code: `U`/`A`/`F`/`E`/`T`/`I` prefixes, `b` for bools, PascalCase everywhere.
- Comments: house rule wins. Comments on Blueprint- or editor-exposed `UPROPERTY`/`UFUNCTION` become editor tooltips, so they are user-facing text; nothing else gets doc comments.
- UE builds without C++ exceptions: no `try`/`catch`. Return `TOptional`, `TValueOrError` or a `bool` with an out-parameter; `check` only for programmer errors, `ensure` for recoverable ones.

## Build

- Warnings as errors in the project's `Target.cs`: `bWarningsAsErrors = true;`. A 5.6 forum report says it did not apply with Clang: verify on every platform you ship.
- Raise individual warning levels through `TargetRules` / `ModuleRules` settings (e.g. `ShadowVariableWarningLevel`), never `#pragma warning` or `PRAGMA_DISABLE_*` macros in our code.
- One module per feature; `PrivateDependencyModuleNames` unless a dependency is part of the module's public headers.
- Run UBT's static analyzer on CI builds (`-StaticAnalyzer=Default`; flag name not verified for every platform, check the build configuration page).

## Code

```cpp
UCLASS()
class SHOP_API AEnemy : public ACharacter
{
	GENERATED_BODY()

public:
	void ApplyDamage(float Amount);

private:
	static constexpr float DefaultMaxHealth = 100.0f;

	UPROPERTY(EditDefaultsOnly, Category = "Combat")
	float MaxHealth = DefaultMaxHealth;

	UPROPERTY()
	TObjectPtr<UHealthComponent> Health;
};
```

- Every `UObject*` member is a `UPROPERTY` `TObjectPtr<T>` so the garbage collector sees it. Outside `UPROPERTY` members use raw pointers or `TWeakObjectPtr`, as Epic advises.
- Non-`UObject` ownership: `TUniquePtr` / `TSharedPtr`. No naked `new`/`delete`.
- Engine containers and strings (`TArray`, `TMap`, `FString`, `FName`, `FText` for user-visible text) in UE code.
- Tuning values in `UPROPERTY(EditDefaultsOnly)` fields or Data Assets, never literals in logic.
- `const` correctness on methods and parameters; pass `const FString&`, not `FString`.
- Gameplay logic that needs no world in plain `F` structs or `UObject`s, so it tests without a map.

## Tests

- Automation Spec in `*.spec.cpp`. `Describe` names the unit, `It` states the behavior:
  ```cpp
  BEGIN_DEFINE_SPEC(FHealthSpec, "Shop.Health", EAutomationTestFlags::ProductFilter | EAutomationTestFlags_ApplicationContextMask)
  END_DEFINE_SPEC(FHealthSpec)

  void FHealthSpec::Define()
  {
  	Describe("ApplyDamage", [this]()
  	{
  		It("never drops health below zero", [this]()
  		{
  			const float Health = FHealthRules::ApplyDamage(FullHealth, Overkill);
  			TestEqual(TEXT("Health"), Health, 0.0f);
  		});
  	});
  }
  ```
  The flag names changed across 5.x releases: copy them from the Automation Spec page of your engine version.
- Functional tests (`AFunctionalTest` in a test map) only for behavior that needs a world.
- CI runs the editor headless with `-ExecCmds="Automation RunTests Shop;Quit" -unattended -nullrhi`; check the exact flags for your version.
- No built-in coverage tool was verified: tell the user the 90% gate is not enforced unless the project adds one (e.g. OpenCppCoverage on Windows, unverified with UE).
