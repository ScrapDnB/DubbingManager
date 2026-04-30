# Dubbing Manager: Codex Context

This file is a handoff note for future Codex sessions. It describes the current architecture, recent decisions, user-confirmed behavior, and the safest places to continue work.

## High-Level Direction

Dubbing Manager is a PySide6 desktop app for dubbing project management. It imports episode scripts, lets the user assign actors to roles, edits working text, opens a teleprompter, previews video, and exports montage sheets.

The current architectural direction is important:

- ASS/SRT/DOCX files are import sources, not the editable source of truth.
- After import, each episode should use a generated working text JSON.
- Normal text editing happens in the working JSON, especially through the teleprompter/editing UI.
- Saving text changes back into ASS/SRT is intentionally disabled.
- Export, teleprompter, statistics, and search should read working text data.

## Project Format

Current `PROJECT_VERSION`: `1.2` in `config/constants.py`.

Project data now includes these important fields:

- `episodes`: source file path per episode. Historically ASS/SRT; now also DOCX source paths can appear.
- `episode_texts`: working text JSON path per episode.
- `global_map`: global role-to-actor assignments.
- `episode_actor_map`: per-episode role-to-actor overrides.
- `project_folder`: optional root folder used by the project file manager/scanner.
- `replica_merge_config`: settings used to merge source subtitle lines into usable replicas/rings.
- `export_config`, `prompter_config`: project-level settings, usually seeded from global settings.

Old projects must remain loadable. `ProjectService._ensure_compatibility` is the compatibility gate; add new project fields there and in `ProjectService.create_new_project`.

## Working Text Architecture

Working text files are created by `ScriptTextService` and stored under the folder named by `SCRIPT_TEXT_DIR_NAME`. Currently:

```python
SCRIPT_TEXT_DIR_NAME = "texts_dm"
```

The actual working text folder should be created relative to the project working folder when available, not blindly next to the `.json` project file.

Main rules:

- Use `MainWindow.get_episode_lines(ep)` as the UI-level entry point for episode lines.
- `get_episode_lines` should prefer `ScriptTextService.load_episode_lines`.
- Avoid reparsing ASS/SRT if a working text exists.
- If no working text exists for an old project, migration/import flows can generate one from the source.
- DOCX imports should also produce working text JSON so search/statistics/export see the same data path as subtitles.
- Global search, episode/project statistics, teleprompter, and export should work for ASS/SRT/DOCX sources because they use working lines.

Important files:

- `services/script_text_service.py`: create/load/save/rename working JSON text.
- `ui/main_window.py`: `get_episode_lines`, import flows, working text regeneration, old-project migration.
- `ui/dialogs/project_files.py`: scanning, relinking, and regeneration UI.
- `services/project_folder_service.py`: project folder scanning/relinking logic.

## Actor Assignment Architecture

Assignments have two scopes:

- Global: stored in `global_map`.
- Episode-local: stored in `episode_actor_map[str(ep_num)]`.

Use `services/assignment_service.py` for assignment logic instead of reading `global_map` directly when episode context matters.

Important helpers:

- `get_actor_for_character(project_data, char_name, ep_num)`
- `get_assignment_scope(project_data, char_name, ep_num)`
- `get_assignment_map(project_data, scope, ep_num)`
- `get_episode_assignments(project_data, ep_num)`
- `get_actor_roles(project_data, actor_id)`
- `rename_character_assignments(project_data, old_name, new_name)`

`LOCAL_UNASSIGNED_ACTOR_ID` is a sentinel. It means “this role is explicitly unassigned in this episode” even if the global role has an actor.

Places that should use effective assignment:

- HTML export
- Excel export and actor summary
- Teleprompter coloring/filtering
- Project and episode statistics
- Actor roles list/counts
- Reaper marker coloring
- Any future UI that asks “who voices this line in this episode?”

## UI Notes

Main table columns:

- `Персонаж`
- `Строчек`
- `Колец`
- `Слов`
- `Область`
- `Актер`
- `📺`

Column widths are in `config/constants.py`:

- `MAIN_TABLE_COUNT_COL_WIDTH`
- `MAIN_TABLE_SCOPE_COL_WIDTH`
- `MAIN_TABLE_VIDEO_COL_WIDTH`

Changing `Глобально` / `Серия` should not rebuild the whole table. It should update only the current row widgets so scroll position stays stable.

The right sidebar currently has:

- top block: tools (`Просмотр серии`, `Телесуфлёр`, `Reaper RPP`)
- bottom block: selected character statistics

Character sidebar statistics:

- Triggered by selecting a row in the main table.
- Shows total rings/words and episode list.
- Uses current replica merge settings through `ExportService.process_merge_logic`.

## Teleprompter Notes

The teleprompter now supports switching episodes while preserving window settings like selected actor/filter and synchronization. Keep that behavior when changing teleprompter state.

Text edits in the teleprompter should save to the working text JSON and then refresh the visible episode data. Avoid adding ASS/SRT write-back paths.

Important file:

- `ui/teleprompter.py`

Useful test:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_teleprompter_episode_switch.py -q
```

## DOCX Notes

DOCX import supports flexible column mapping and preview. Column settings persist in global settings through `DEFAULT_DOCX_IMPORT_CONFIG` and `GlobalSettingsService`.

DOCX source behavior should match ASS/SRT after import:

- create working text JSON
- support episode/project statistics
- support global search
- support export
- support teleprompter

Important files:

- `services/docx_import_service.py`
- `ui/dialogs/docx_import.py`
- `services/global_settings_service.py`
- `config/constants.py`

## Actor UI Notes

Actor table:

- Actor name can be renamed.
- Roles button opens a read-only roles dialog.
- Roles dialog should show role names plus rings/words.
- It should not provide role-add functionality.

Important files:

- `ui/controllers/actor_controller.py`
- `ui/dialogs/roles.py`
- `ui/main_window.py` (`edit_roles`, `_get_actor_role_stats`)

## Export Notes

HTML and Excel export should use working text lines and effective actor assignments. Export filters can highlight selected actors; when all actors are selected, that is treated like no restrictive filter.

Reaper RPP export exists in both `ui/main_window.py` and `ui/controllers/export_controller.py`; be careful not to update only one path if adding behavior used by both.

Important files:

- `services/export_service.py`
- `ui/controllers/export_controller.py`
- `ui/main_window.py`

## Project Files / Scanner Notes

The project file manager is supposed to scan/relink missing known files, not invent new project episodes on its own. The user explicitly asked to stop at scanning/relinking for now, not add “import new source through manager” behavior.

Working text JSON files should be included in scan/relink behavior.

Important files:

- `ui/dialogs/project_files.py`
- `services/project_folder_service.py`

## Key Files Map

- `main.py`: app entry point and logging setup.
- `config/constants.py`: project version, folder names, default configs, UI sizes.
- `core/commands.py`: Undo/Redo command objects.
- `services/project_service.py`: project load/save, metadata, compatibility.
- `services/script_text_service.py`: working text JSON lifecycle.
- `services/assignment_service.py`: global vs episode-local actor assignment.
- `services/export_service.py`: merge logic plus HTML/XLSX export.
- `services/docx_import_service.py`: DOCX parsing and conversion.
- `services/project_folder_service.py`: project folder scanner.
- `ui/main_window.py`: central orchestration; large but still the main integration surface.
- `ui/teleprompter.py`: teleprompter display/edit workflow.
- `ui/dialogs/search.py`: global search.
- `ui/dialogs/summary.py`: reports/statistics.
- `ui/dialogs/project_files.py`: file status/relink/regenerate UI.
- `ui/controllers/actor_controller.py`: actor table.
- `ui/controllers/export_controller.py`: export controller path.

## Tests

Full suite:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ -q
```

Recent baseline after local-assignment and sidebar-statistics work:

```text
540 passed, 11 skipped
```

Focused tests:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_assignment_service.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_script_text_service.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_export_service.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_project_folder_service.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_project_files_dialog.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_teleprompter_episode_switch.py -q
```

## Recent User-Confirmed Behavior

- Working text architecture works for ASS/SRT/DOCX flows.
- Save-back to ASS/SRT is removed/disabled from normal UI.
- Regenerating working text from subtitles no longer mixes old edited text into the teleprompter.
- Old projects can generate missing working texts.
- Generated working texts use `texts_dm`.
- Project folder scanner can find/relink generated working texts.
- DOCX source supports episode stats, project stats, and global search.
- DOCX import column settings persist.
- Actor roles dialog is read-only and shows rings/words.
- Actor renaming updates project data correctly.
- Teleprompter can switch episodes while preserving settings.
- Per-episode role assignments work.
- Main table scroll does not jump when switching assignment scope.
- Main table compact columns are tuned for counts/scope/video.
- Sidebar character statistics work.

## Common Pitfalls

- Do not reintroduce ASS/SRT write-back without explicit user request.
- Do not read only `global_map` when episode-local assignment can matter.
- Do not create `texts` again; use `SCRIPT_TEXT_DIR_NAME`.
- Do not add new “manager imports new files” behavior unless the user asks; scanning/relinking is the current scope.
- When renaming characters, update working text and assignment maps.
- When deleting/renaming actors or episodes, consider local assignment maps.
- Keep UI changes modest and consistent with the current PySide style.

## Implementation Preferences

- Prefer existing services and helpers over ad hoc logic.
- Preserve old-project compatibility.
- Put reusable constants in `config/constants.py`.
- Keep user edits and dirty worktree changes; do not revert unrelated changes.
- Use `apply_patch` for manual file edits.
- Run focused tests for the changed area and the full suite for architectural changes.
