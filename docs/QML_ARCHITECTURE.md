# QML application architecture

The migrated application is designed as a QML frontend over a Python
application and domain backend. It is not a Widgets application wrapped in a
Qt Quick shell.

## Dependency direction

```text
QML views
    -> AppBridge
        -> feature bridges
            -> ProjectSession
            -> services
                -> project data
            -> commands / UndoStack
        -> platform adapters
```

- QML owns presentation, interaction, animation, and temporary control state.
- Feature bridges own QML-facing properties, models, signals, and actions for
  one workflow.
- `ProjectSession` owns the open project reference, current episode, dirty
  state, command execution, and targeted domain-change notifications.
- Services implement parsing, calculation, import, export, and persistence
  without depending on QML or Widgets.
- `ProjectService` owns backup naming, relative/absolute directory resolution,
  rotation, validation, and the complete `.dub_backup` payload; global settings
  only provide its normalized policy.
- Commands implement every undoable project mutation.
- Platform adapters contain the small amount of Cocoa, Windows, and operating
  system integration that cannot be expressed portably in QML.

Feature bridges must not directly update each other. A project mutation is
executed through `ProjectSession`, which publishes the affected domain. Other
features refresh only when that domain matters to them.

## Backend layout

```text
ui/qml_backend/
├── app_bridge.py
├── project_session.py
├── models/
│   └── dict_list_model.py
└── features/
    ├── project_bridge.py
    ├── project_files_bridge.py
    ├── casting_bridge.py
    ├── actor_library_bridge.py
    ├── roles_bridge.py
    ├── montage_bridge.py
    ├── video_bridge.py
    ├── reaper_bridge.py
    ├── reports_bridge.py
    ├── teleprompter_bridge.py
    ├── settings_bridge.py
    ├── ui_state_bridge.py
    ├── audiobook_bridge.py
    ├── converter_bridge.py
    └── update_bridge.py
```

`app_bridge.py` is the sole composition root. The former `ui/qml_bridge.py`
compatibility facade and its historical class name have been removed. All
feature modules shown above are present.

## Migration rules

1. New QML functionality is added to its feature bridge, never to the legacy
   root bridge.
2. Existing functionality moves one complete workflow at a time, including
   models, mutations, undo/redo, errors, tests, and QML bindings.
3. The root exposes feature objects, shared status, and shared errors only.
   Models and workflow actions belong to their feature bridge.
4. Widgets controllers are reused only when they are UI-independent. Business
   logic coupled to widgets moves into services instead.
5. Broad `refresh()` calls are transitional. Feature bridges react to targeted
   session domains and update only their own models.
6. QML application code must not import `QtWidgets`. Qt WebEngine may load Qt
   PrintSupport/Widgets internally while providing the required HTML view.

The migrated feature APIs currently exposed by the root are:

- `appBridge.project` for lifecycle, episodes, recent projects, and undo/redo;
- `appBridge.uiState` for native UI preferences such as window geometry,
  splitter sizes, and the last folders used by file dialogs;
- `appBridge.projectFiles` for project-folder links, source and working files,
  missing-file recovery, and project health diagnostics;
- `appBridge.casting` for project actors, character filters, assignments, and
  the central casting workspace;
- `appBridge.actorLibrary` for the shared actor base, project transfers, and
  load-time synchronization;
- `appBridge.roles` for project role assignment and per-actor role statistics;
- `appBridge.settings` for staged project/global settings and atomic project
  mutations;
- `appBridge.teleprompter` for prompting, presets, editing, and OSC;
- `appBridge.audiobook` for PDF import, HTML role markup, chapter structure,
  and undoable audiobook persistence;
- `appBridge.montage` for HTML preview, editing, actor highlights, and export;
- `appBridge.video` for synchronized video and replica preview;
- `appBridge.reaper` for RPP and marker export;
- `appBridge.reports` for global search, casting summaries, and spreadsheet
  export.
- `appBridge.converter` for standalone ASS/SRT preview and cancellable
  HTML/DOCX/PDF conversion without mutating the open project.

There are no workflow/model aliases on the root bridge. Both QML and backend
contract tests consume the feature APIs directly.
