# Godot (GDScript, C#)

Verified against the Godot stable docs (ProjectSettings class reference, GDScript static typing and warning system; 4.6/4.7 era) and PyPI gdtoolkit 4.5.0 (Nov 2026). Current engine: the godotengine.org download page; pin it in `project.godot` (`config/features`) and in CI. C# builds on `csharp.md`.

## GDScript: static typing as errors

In `project.godot` (0 = ignore, 1 = warn, 2 = error):

```ini
[debug]
gdscript/warnings/untyped_declaration=2
gdscript/warnings/inferred_declaration=2
gdscript/warnings/unsafe_property_access=2
gdscript/warnings/unsafe_method_access=2
gdscript/warnings/unsafe_cast=2
gdscript/warnings/unsafe_call_argument=2
```

- `untyped_declaration` rejects variables, parameters and functions without a type; `inferred_declaration` rejects `:=`, so every declaration writes its type (house rule).
- Keep the default `directory_rules` that exclude `res://addons`: third-party code is not ours to fix. Never exclude our own folders, never write `@warning_ignore`.
- Lint and format with gdtoolkit (`gdlint`, `gdformat --check` in CI); `pip install "gdtoolkit==4.*"` matches Godot 4.

## GDScript code

```gdscript
class_name Health
extends Node

signal changed(current: int)

const DEFAULT_MAX: int = 100

@export var max_health: int = DEFAULT_MAX
var current: int = 0


func _ready() -> void:
	current = max_health


func apply_damage(amount: int) -> void:
	current = maxi(current - amount, 0)
	changed.emit(current)
```

- Typed collections: `Array[Enemy]`, `Dictionary[StringName, int]`. Typed signal parameters.
- Node references: `@onready var sprite: Sprite2D = %Sprite`, using scene-unique names, not long `$A/B/C` paths or `get_node` with built strings.
- Call down, signal up: a node calls methods on its children and emits signals to its parent; it never reaches up the tree.
- Game rules in `RefCounted` or `Resource` classes that need no scene, so they test fast. Tuning values in `Resource` files or named constants.
- Check freed objects with `is_instance_valid`, not `!= null`.

## C#

- Every script class is `partial` (`public partial class Player : CharacterBody2D`); Godot's source generators need it.
- Signals as `[Signal] public delegate void ChangedEventHandler(int current);`, exports with `[Export]`. Explicit types and nullable as in `csharp.md`.
- Use the .NET SDK the Godot release notes require; `TreatWarningsAsErrors` as in `csharp.md`. Logic in a separate class library with no Godot reference, tested with xUnit v3.

## Tests

- GDScript: GUT or gdUnit4 (whichever the project has; ask before adding). Both run only functions prefixed `test_`, so names read `test_apply_damage_more_than_current_clamps_to_zero`.
  ```gdscript
  extends GutTest

  func test_apply_damage_more_than_current_clamps_to_zero() -> void:
  	var health: Health = Health.new()
  	add_child_autofree(health)
  	health.apply_damage(OVERKILL)
  	assert_eq(health.current, 0)
  ```
- CI runs headless (`godot --headless --import` first, then the framework's command-line runner; check its docs for the exact flags).
- No GDScript coverage tool was verified: tell the user the 90% gate applies only to C# (`csharp.md`).
