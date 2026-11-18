# Qt (Qt Quick / QML, Qt Widgets)

Builds on `cpp.md` (CMake presets, clang-tidy, warnings as errors, sanitizers). Verified against the Qt 6 docs for qmllint and `qt_add_qml_module` (6.10 pages, Nov 2026). Current release: the folders under `download.qt.io/official_releases/qt/` (6.12 listed in Nov 2026) or the Qt Maintenance Tool. Use Qt 6 for new code; Qt 5.15 standard support has ended.

## Build

```cmake
find_package(Qt6 REQUIRED COMPONENTS Quick QuickTest Test)
qt_standard_project_setup(REQUIRES 6.8)
qt_add_executable(shop main.cpp)
qt_add_qml_module(shop URI Shop QML_FILES Main.qml ProfilePage.qml SOURCES profilemodel.h profilemodel.cpp)
```

- Declare every QML file and C++ type in `qt_add_qml_module`: it enables the QML compilers, tooling and the lint targets.
- Register C++ types with `QML_ELEMENT` / `QML_SINGLETON` in the class, never `qmlRegisterType` at runtime.

## Lint and format: qmllint, qmlformat

- CI builds the generated `all_qmllint` target. Generate `.qmllint.ini` with `qmllint --write-defaults`, raise every category to `error`, and turn on the `compiler` category (off by default) so code that qmlsc cannot compile fails too.
- Never write `// qmllint disable`: it is an inline suppression.
- Format with `qmlformat -i`; CI reformats and fails on `git diff --exit-code`.
- C++ follows `cpp.md`. In `.clang-tidy`, turn off `cppcoreguidelines-owning-memory`: it flags Qt's parent-owned allocations (`new QLabel(parent)`), which are the correct Qt pattern. Write that reason on the line above.

## QML

- Type everything QML can type: properties (`property int count: 0`, never `property var` for a known type), function parameters and returns:
  ```qml
  pragma ComponentBehavior: Bound
  import QtQuick
  import QtQuick.Controls

  Item {
      id: root
      required property ProfileModel profile

      function canSave(name: string): bool {
          return name.trim().length > 0
      }

      Button {
          text: qsTr("Save")
          enabled: root.canSave(root.profile.name)
          onClicked: root.profile.save()
      }
  }
  ```
- `required property` for inputs, qualified access through `id` (no unqualified lookups into parents), `pragma ComponentBehavior: Bound` for delegates.
- Logic lives in C++ models (`Q_PROPERTY` with `NOTIFY`, `QAbstractListModel` for lists); QML only binds and forwards events.
- Sizes, spacing and colors from a theme singleton, never literals. User-visible text through `qsTr`.
- Accessibility: `Accessible.name` on icon-only controls.

## C++ with Qt

- `connect` with member-function pointers (`&Model::nameChanged`), never the `SIGNAL()`/`SLOT()` string macros.
- Ownership: a `QObject` with a parent is owned by it; everything else in `std::unique_ptr`. No naked `delete`.
- Never block the GUI thread: `QtConcurrent` / `QThreadPool`, results delivered through signals.

## Tests

- C++: Qt Test (`QTest`) with one private slot per behavior, named `saveWithBlankNameIsRejected()`; table cases with `_data()` functions.
- QML: Qt Quick Test `TestCase`; Qt runs only functions prefixed `test_`, so name them `test_save_with_blank_name_is_disabled()`.
- Register tests with CTest; CI sets `QT_QPA_PLATFORM=offscreen`.
- Coverage of C++ as in `cpp.md`. No Qt-provided QML coverage tool was found: tell the user QML logic is covered only through the C++ models and Quick tests.
