# QML interface

This branch contains the QML frontend for Dubbing Manager, which is the
production interface starting with 2.0.0-beta1.

Run it with:

```bash
.venv/bin/python qml_main.py
```

The classic PySide Widgets entry point remains `main.py`.

## Current scope

The migrated application currently includes:

- create an empty project in memory;
- open an existing `.dub` or legacy `.json` project;
- show a main-window layout close to the Widgets version: actor panel, episode
  controls, character table, tools sidebar, and settings shortcuts;
- show episodes and switch the active episode;
- show project actors;
- show character statistics for the selected episode;
- import ASS/SRT subtitle files into project episodes and embedded working
  texts;
- rename and delete the current episode through command-backed undo/redo;
- rename characters from the central table through command-backed undo/redo;
- edit the project title;
- save already-opened projects;
- save projects under a new path;
- show, open, update, and clear recent projects through the existing global
  settings service.
- preview and edit montage sheets through the shared HTML generator, configure
  actor highlighting, and export HTML/XLSX/DOCX/PDF;
- preview replicas against attached video;
- export Reaper projects and marker CSV files;
- run the teleprompter with presets, editing, navigation, and OSC support.
- manage project-folder links, missing sources, working texts, and project
  health through the dedicated project-files backend.

The main window consumes project lifecycle through `appBridge.project`, casting
through `appBridge.casting`, and file recovery through
`appBridge.projectFiles`. OS file-open events and every migrated dialog call
the same feature APIs directly.
Global search and casting summaries are provided by `appBridge.reports`.
The actor panel now switches between the project and shared global actor bases,
and the QML roles window supports filtered single or bulk assignment with undo.
Matching global actors synchronize on project load, while actor-role statistics
and multi-actor transfer are available from the project actor panel.

It reuses the existing Python services instead of duplicating business logic in
QML. Workflows use feature bridges under `ui/qml_backend/`; the root bridge
only composes them and routes shared status and errors.
See `docs/QML_ARCHITECTURE.md` for the target structure and migration rules.

Reusable QML pieces live in `qml/components/`:

- `ProjectToolbar.qml`;
- `EpisodeControls.qml`;
- `ActorPanel.qml`;
- `CharacterTable.qml`;
- `ToolsSidebar.qml`;
- `ExportPanel.qml`.

## Direction

The migration proceeds in complete vertical workflows:

1. Keep `services/` and `core/` as the application engine.
2. Keep open-project state and command execution in `ProjectSession`.
3. Give each workflow a focused feature bridge and typed QML models.
4. Route project mutations through the existing undo/redo infrastructure.
5. Remove Widgets dependencies from the production QML path after parity.

The legacy Widgets interface remains in source during the beta period as an
emergency fallback, but release builds start the QML application.
