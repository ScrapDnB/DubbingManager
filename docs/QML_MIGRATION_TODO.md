# QML migration TODO

This document tracks the complete migration of the user-visible Widgets
application to QML. The parity baseline is the local `v1.7.1` tag at commit
`6cb0a61` (audited on 2026-07-15).

QML does not have to reproduce every Widgets interaction literally. A workflow
may be redesigned when the QML version is clearer or more native, but it must
preserve the data, settings, side effects, error handling, and resulting files.

The hidden legacy export group at the bottom of `MainWindowUiMixin` is not a
migration target. In 1.7.1, montage preview and export live in the montage sheet
window. Global and project settings remain visible main-window actions.

The legacy `.dmproject` archive is also outside the migration target. Portable
project storage is provided by the current `.dub` format.

Status markers:

- `[x]` implemented in the QML branch;
- `[~]` partially implemented;
- `[ ]` not implemented yet;
- `QML+` is an improvement backed by existing code but not exposed by the
  Widgets 1.7.1 interface, so it is not a strict parity blocker.

## 1. Application Foundation

- [x] QML is the production entry point; the Widgets application remains in
  source as a temporary fallback during the beta period.
- [x] Reuse Python services, controllers, data formats, and export code.
- [x] Reuse the command/undo infrastructure for migrated mutations.
- [x] Expose typed list models and bridge properties to QML.
- [x] Introduce `ProjectSession` and feature-oriented QML backends; project
  lifecycle, casting, video preview, Reaper, montage, and teleprompter are
  consumed through feature APIs.
- [x] Move the main casting workspace behind `appBridge.casting`, including
  actor mutations, filters, selection, assignment scope, and character rename.
- [x] Move project-folder links, file recovery, embedded working-text creation,
  and health diagnostics behind `appBridge.projectFiles`.
- [x] Move global search and casting summaries behind `appBridge.reports`,
  including navigation and XLSX export.
- [x] Expose global actor-library and project-role workflows through dedicated
  `appBridge.actorLibrary` and `appBridge.roles` feature APIs.
- [x] Use native Qt file and folder dialogs in migrated workflows.
- [x] Use a cross-platform `ComboBox` wrapper without macOS-only decoration.
- [x] Keep every migrated QML project mutation command-based; QML and backend
  contract tests consume feature bridges directly, with no root action aliases.
- [x] Remove emoji toolbar glyphs; use native text commands, familiar undo/redo
  symbols, tooltips, and accessible names without platform-specific artwork.
- [~] Use native confirmation, progress, warning, and error presentation across
  all migrated workflows; basic errors and destructive confirmations are wired.
- [x] Ship the beta with a Russian-only QML interface. English source strings
  stay in the repository for later editorial work but are not exposed in QML.
- [x] Preserve startup logging and rotating platform log files.
- [x] Build and launch QML by default, including QML sources, icons, backend
  modules, and Qt WebEngine dependencies.
- [x] Remove application-level Widgets imports from the QML path. Package
  initializers and startup helpers are lazy/UI-neutral; Qt WebEngine still
  loads Qt PrintSupport/Widgets internally for the HTML montage renderer.
- [x] Move reusable montage and Reaper export orchestration out of Widgets-era
  controllers so QML feature bridges depend on services.
- [~] Run visual and behavioral QA on macOS, including light/dark system themes
  and compact-window layout. Windows packaging and native integration are
  verified by the prerelease GitHub Actions build.

## 2. Project Lifecycle And Safety

- [x] Move project lifecycle, episode navigation, recent projects, autosave,
  and undo/redo behind `appBridge.project`.
- [x] Create a new subtitle project.
- [x] Open `.dub` projects and legacy `.json` projects through `ProjectService`.
- [x] Apply existing project compatibility upgrades when loading old projects.
- [x] Save and Save As `.dub`, excluding runtime-only caches.
- [x] Show, open, update, validate, and clear global recent projects.
- [x] Keep recent projects shared with the Widgets application.
- [x] Prompt Save / Discard / Cancel before New, Open, recent-project switch,
  OS-open, and application close when the project is dirty.
- [x] Show dirty state in the window title and keep title/project path in sync.
- [x] Run configurable autosave, retain the configured number of backups,
  support relative or absolute storage, and allow backups to be disabled.
- [x] Store complete project backups as `.dub_backup`, browse/restore them, and
  preserve temporary autosave for a project that has never been saved.
- [x] Open an existing `.dub`/`.dub_backup`/`.json` supplied on the QML command line at
  startup.
- [~] Handle macOS Finder `FileOpen` events and Windows project file association:
  `.dub` and `.dub_backup` are registered in packaging metadata/scripts;
  packaged Windows registration remains to be verified at cutover.
- [x] Accept drops over the central workspace: open the first project file,
  prepare dropped ASS/SRT files for import, or open dropped DOCX, without
  colliding with the future quick-converter drop zone.
- [x] Surface validation, malformed JSON, missing file, and save failures without
  losing the current project.
- [x] QML+: add a backup browser/restore flow using the existing
  `list_backups()` and `restore_from_backup()` service methods.
- [x] Remember the last folder used by project, source, document, actor-data,
  video, and export dialogs across sessions.

## 3. Main Window Shell

- [x] Match the 1.7.1 baseline structure: actor base, project toolbar, episode
  controls, central character table, tools sidebar, and settings shortcuts.
- [x] Keep the obsolete bottom export panel out of the QML layout.
- [x] Provide softer panel/table separators in the dark theme.
- [x] Keep the central table inside its bounds and reserve a visible preview
  column at supported window sizes.
- [~] Finish responsive behavior for compact windows: side panels retain useful
  minimums and episode/filter controls compact below 900 px; a final visual
  pass at every supported DPI remains.
- [x] Implement platform-standard undo/redo shortcuts and expected
  focus behavior.
- [x] Use real top-level QML windows with system title bars and close controls
  for migrated dialogs and tools on macOS and Windows.
- [x] Implement sortable central-table headers with direction state.
- [~] Add keyboard navigation, accessible names, focus indicators, and screen
  reader-friendly roles. Central tables, navigation, drop zones, and toolbar
  commands are covered; full screen-reader QA remains.
- [x] Keep destructive actions disabled when their target does not exist.
- [x] QML+: persist main-window geometry and splitter/panel sizes.

## 4. Episodes, Sources, And Working Texts

- [x] List episodes and switch the active episode.
- [x] Import multiple ASS/SRT files and create embedded working texts.
- [x] Match import naming behavior: show/edit each suggested episode number,
  resolve duplicates deliberately, and derive the project name from the first
  ASS import where applicable.
- [x] Rename and delete the current episode through undo/redo.
- [x] Attach, replace, resolve, and explicitly remove an episode video path from
  Project Files without deleting the media file.
- [x] Import DOCX with file selection, table selection, flexible automatic
  column detection, editable field mapping, configurable timing formats and
  separators, parsed-row preview/status, and Import current table / Import all
  tables.
- [x] Build one reusable Import settings pane for ASS, SRT, replica merging, and
  DOCX, including aliases/patterns, ignored/header rows, timing separators,
  fallback duration/mapping, detection priority, and named reusable presets.
- [x] Persist DOCX defaults globally and the latest mapping in project settings;
  allow per-import overrides without silently changing the saved defaults.
- [x] Relink a missing ASS/SRT/DOCX source from the central missing-file state.
- [x] Link existing external working-text JSON files when a project opens,
  embed them into `.dub`, and mark the project for saving.
- [x] Report the working-text migration when it occurs during project opening.
- [x] Regenerate one working text from ASS/SRT/DOCX, reusing the saved DOCX
  mapping when it fits and falling back to automatic detection.
- [x] Create all missing ASS/SRT/DOCX working texts as one undoable operation.
- [x] Keep imported source lines, source-origin metadata, and original ASS
  snapshot needed by exact Reaper markers and source recovery.
- [x] Save the untouched embedded original ASS snapshot to a user-selected file.
- [x] Preserve natural numeric episode sorting for subtitle projects and
  explicit book chapter order for audiobook projects.
- [x] Invalidate episode caches and refresh migrated tools after source changes.

## 5. Project Folder, Files, And Health

- [x] Set and clear a project folder, with path information and project counts.
- [x] Resolve relative paths against the project folder and rebase portable
  projects from the opened project file when their original folder moved.
- [x] Scan a project folder and automatically relink matching sources, legacy
  working texts, and videos.
- [x] Batch-import ASS/SRT/DOCX sources discovered in a folder, attach matching
  video for each imported/project episode, and create embedded working texts as
  one undoable operation.
- [x] Show a central missing-file state with an immediate relink action.
- [x] Build the combined Project Files dialog with Files and Health views.
- [x] Show the per-episode source, embedded/legacy working text, and video list,
  including path, found/missing status, and aggregate counts.
- [x] Relink the selected source, legacy working text, or video.
- [x] Regenerate selected and missing ASS/SRT/DOCX working texts.
- [x] Save the selected episode's embedded original ASS snapshot.
- [x] Delete an episode and all of its source/text/video references from the file
  manager through the command infrastructure.
- [x] Run project health checks for missing sources/videos, malformed or missing
  working texts, invalid line records, timing errors, and empty data.
- [x] Present health severity, episode, category, message, path, summary counts,
  and refresh actions.

## 6. Character Table And Assignments

- [x] Show per-character lines, rings, and words for the selected episode.
- [x] Filter by actors used in the selected episode.
- [x] Filter unassigned characters and search the current table.
- [x] Select a character and show project totals.
- [x] Rename a character and update assignments through undo/redo.
- [x] Assign an actor globally through undo/redo.
- [x] Switch a character between global and episode-local assignment scope.
- [x] Assign a local actor or explicit local-unassigned override.
- [x] Assign several project actors to one role without replacing the existing
  cast; show every actor as a separate compact line in the main table and keep
  the operation undoable.
- [x] Show complete selected-character statistics with per-series rings/words
  breakdown and a readable empty state.
- [x] Open per-character replica preview from the preview column.
- [x] Keep actor/filter/role/statistics views synchronized after assignment,
  actor, character, or episode changes.
- [x] Support efficient row interaction and keyboard operation without changing
  layout dimensions on hover, selection, or editor opening.

## 7. Project And Global Actor Bases

- [x] Show project actors with name, color, gender, and role count.
- [x] Add, rename, delete, recolor, and change gender through undo/redo.
- [x] Offer the project's custom actor colors first, then open the native system
  color dialog for an arbitrary color.
- [x] Let Add Actor select an existing global actor or create a new actor.
- [x] Make the Project / Global selector actually switch models and actions.
- [x] Show and edit the global actor name and gender; keep project colors local.
- [x] Add the selected global actor to the project without creating duplicates.
- [x] Add selected project actors to the global base in one operation, mark
  existing matches, and report added/already-present totals.
- [x] Synchronize project actors with matching global actors when loading,
  preserving project colors and replacing assignment/highlight references.
- [x] Merge duplicate project/global actors and replace all global assignment,
  episode assignment, and filter references safely.
- [x] Import/export the global actor base JSON from Global Settings.
- [x] Import/export project actors plus global and per-episode assignments from
  Project Settings; match actors by name and report added/matched/skipped data.

## 8. Roles And Casting Workflows

- [x] Open an actor's roles view with merged-replica ring and word statistics.
- [x] Build the Project Roles view with role/actor filtering, appearance series,
  current actor, multi-selection reassignment, and assignment reset.
- [x] Build bulk role assignment: choose an actor, filter roles, select/clear all
  visible roles, keep checked state across filtering, and apply once.
- [x] Refresh the actor base and central casting table after role changes.
- [x] Route role assignment mutations through one atomic undo command and clear
  matching episode-local overrides when assigning globally.

## 9. Search, Statistics, And Reports

- [x] Search character names and replica text across every episode.
- [x] Show episode, timecode, character, and text in global-search results.
- [x] Jump from a result to its episode and select the related character.
- [x] Show episode and project casting summaries with actor color, rings, words,
  roles, and unassigned totals.
- [x] Export the project casting matrix to formatted XLSX for Google Sheets.
- [x] Select and persist the XLSX metric: rings, lines, or words.
- [x] Recalculate active search and summary views after working-text edits and
  assignment changes, including direct edits from the teleprompter.
- [x] Add sorting, keyboard navigation, empty states, and copyable
  report/search rows.

## 10. Montage Preview And Export

- [x] Move the complete QML workflow behind `appBridge.montage`, including
  models, HTML editing, actor highlighting, commands, and export.
- [x] Open a QML montage-sheet window and switch episodes without closing.
- [x] Render the exact shared HTML document inside QML through `WebEngineView`,
  including Table and Scenario 1/2/3 layouts.
- [x] Toggle timing, character, actor, and replica elements.
- [x] Select timing range/start-only, rounding, actor colors, softened colors,
  and four font sizes.
- [x] Add table column-width controls and apply them to preview and export.
- [x] Add the actor highlight filter with select all/none and per-actor inverted
  white-on-color mode.
- [x] Add the `allow_edit` setting for preview and standalone editable HTML.
- [x] Edit replica text directly in the WebEngine preview and persist it to the
  episode working text through a tested undoable command.
- [x] Create one complete project backup before the first direct edit of an
  episode from either montage or teleprompter, then refresh every dependent view.
- [x] Let the settings sidebar be hidden and restored without resizing glitches.
- [x] Select HTML, XLSX, DOCX, and PDF formats.
- [x] Export the current episode to one selected file.
- [x] Export one or all episodes and multiple selected formats to a folder.
- [x] Open exported files when `open_auto` is enabled.
- [x] Use the standalone HTML generator for the on-screen preview so layout,
  colors, timing, typography, and editability cannot drift from export.
- [x] For a multi-actor role, show all actor names but use a color only when
  exactly one of its actors is selected in the montage highlight filter.
- [x] Present batch progress, partial failures, cancellation, and exported paths.

## 11. Video Preview

- [x] Move video state and models behind `appBridge.video`.
- [x] Open a replica list for all lines or one selected character.
- [x] Play/pause attached video with seek slider and clean media shutdown.
- [x] Seek and play from a clicked replica when synchronization is enabled.
- [x] Allow disabling click-to-video synchronization.
- [x] Keep a useful replica-only view when no valid video is attached.

## 12. Reaper Export

- [x] Open the Reaper export dialog for the selected episode.
- [x] Preview region count, actor-track count/names, video inclusion, invalid
  lines, and sample regions as options change.
- [x] Select optional video track, text regions, and actor-name transliteration.
- [x] Select merged-replica markers or exact source-line markers; disable exact
  mode with a useful explanation when imported source lines are unavailable.
- [x] Export a complete `.rpp` with project structure, actor tracks, regions,
  colors, and optional video, then offer to open it in Reaper.
- [x] Export Reaper-compatible marker-only CSV with number, name, start, end,
  duration, and actor color.
- [x] Reuse project-folder path resolution and existing Reaper services rather
  than implementing RPP/CSV generation in QML.

## 13. Teleprompter

- [x] Open a QML teleprompter window for the current episode and working text.
- [x] Switch episodes and refresh cast/actor filters without reopening.
- [x] Render timecode, character, actor, and replica text with actor filtering.
- [x] Navigate manually to previous/next or a selected replica.
- [x] Smoothly follow the active time/replica with configurable focus position
  and scroll smoothness. There is no timed autoplay workflow in 1.7.1.
- [x] Show/hide the service header and support mirror mode.
- [x] Configure timecode/character/actor/text fonts and the full color scheme.
- [x] Load, apply, save, and clear the four global teleprompter color presets.
- [x] Connect/disconnect OSC; configure input/output ports, receive-from-Reaper,
  send-navigation-to-Reaper, persisted connection state, and time offset.
- [ ] Restore the non-focus-stealing always-on-top floating controller with
  previous/next, episode selection, replica list, and Hide.
- [ ] Keep the existing Cocoa floating controller on macOS behind a small
  platform adapter; use the QML/Qt window implementation on Windows and Linux.
- [x] Edit replica text and character from the teleprompter with autocompletion.
- [x] Split selected text into another character while preserving timings,
  assignments, embedded working text, and undo/redo.
- [x] Keep a multi-actor role visible when any assigned actor is selected; use
  that actor's color only when the current teleprompter selection is unambiguous.

## 14. Audiobook / Audioserial

- [x] Open the audiobook workspace and load previously stored book chapters.
- [x] Import PDF off the UI thread with progress and failure handling.
- [x] Preserve headings, paragraphs, basic formatting, and the full source HTML.
- [x] Detect chapters using the configurable global keyword list.
- [x] Show the book-like rich-text editor, chapter list, font family, and zoom.
- [x] Build the full-book boundary editor: add at cursor, move, drag, rename, and
  delete boundaries while keeping removed chapter text in the source book.
- [x] Preserve explicit chapter order and subtitle/audiobook project kind.
- [x] Provide nine character/actor quick slots and keyboard keys 1-9.
- [x] Apply a slot to selected text, remove markup, and list marked characters.
- [x] Keep markup colors synchronized with assigned actor colors.
- [x] Save the current chapter or all chapters as embedded project episodes,
  including characters, assignments, source HTML, and chapter order.
- [x] Persist audiobook font, zoom, slots, and global chapter keywords.

## 15. Global And Project Settings

- [x] Build Project Settings tabs: Project, Series and Files, Roles, Montage
  Sheet, Import, Teleprompter, and Transfer.
- [x] Edit project name, author, and studio; show the read-only project type,
  project path/folder, episode count, and working-text count.
- [x] Expose project folder, project files/health, DOCX mapping, and project roles
  from the appropriate tabs.
- [x] Configure replica merging: enabled, FPS, merge gap, short `/` pause, and
  long `//` pause; refresh dependent tools immediately.
- [x] Configure every montage option listed in section 10, reusing one QML pane
  for project settings and global defaults.
- [x] Configure every teleprompter option listed in section 13, including
  native color selection, navigation, floating-controller mode, and OSC.
- [x] Build Project Transfer for actor/assignment import and export, preserving
  actor color/gender and applying imports as one undoable project mutation.
- [x] Build Global Settings tabs: Interface, Audiobooks, Actors, Import,
  Montage Sheet, and Teleprompter.
- [x] Apply global montage, teleprompter, and unified import defaults to the open
  project.
- [x] Save current project montage, teleprompter, and import settings as defaults
  for new projects.
- [x] Import/export the global actor base and edit the audiobook keyword list.
- [x] Select interface language and show the same restart requirement as 1.7.1.
- [x] Apply settings atomically through commands where project data changes, and
  keep Cancel free of side effects.

## 16. Quick Subtitle Converter

- [x] Add a dedicated ASS/SRT drop zone that is visually native in both themes.
- [x] Accept multiple files and ignore/report unsupported paths safely.
- [x] Convert without importing files into the current project or inheriting its
  actor assignments/highlight filters.
- [x] Hold Option/Alt while dropping to preview the first file, then continue the
  multi-file conversion with the preview's temporary montage settings, or cancel
  the whole queue without exporting.
- [x] Export enabled HTML/DOCX/PDF formats next to each source with unique names
  and the current montage settings.
- [x] Show cancellable progress, successful paths, and per-file errors.

## 17. About And Updates

- [x] Build an About dialog with app version, Python/PySide/Qt versions, GitHub link,
  copyright, and Check for Updates.
- [x] Check GitHub Releases asynchronously and distinguish current, newer, and forced reinstall
  states.
- [x] For a source checkout, update through the existing git-based service and
  request restart.
- [x] For packaged macOS/Windows builds, select the platform asset, show
  cancellable download progress, launch the external replacement helper, and
  exit cleanly.
- [x] Fall back to opening the release page when automatic update is unavailable
  or fails.

## 18. Verification And Cutover

- [~] Add bridge/model tests for every migrated read workflow.
- [~] Add command tests for every migrated mutation and undo/redo pair.
- [x] Keep service/controller/export tests shared between Widgets and QML.
- [~] Add QML runtime smoke tests for every dialog and tool entry point.
- [~] Exercise desktop and compact sizes; the compact shell now switches between
  Actors, Replicas, and Tools instead of squeezing three panels into one row.
  A full high-DPI visual matrix remains.
- [ ] Verify native controls, dialogs, tooltips, keyboard behavior, file paths,
  media playback, and updater behavior on macOS and Windows.
- [ ] Verify old `.json`, current `.dub`, subtitle, DOCX, missing-file, Reaper,
  and audiobook fixtures end to end.
- [x] Keep Widgets tests green until final cutover.
- [x] Make QML the production entry point after the beta parity and release QA.

## Recommended Migration Blocks

1. Project safety, project folder/files/health, and missing-file recovery.
2. Video attachment/preview and remaining episode source flows.
3. Global actor base, role management, assignment transfer, and settings.
4. Montage editing/filter parity and Reaper RPP/CSV export.
5. Teleprompter, including OSC and floating controls.
6. Audiobook/audioserial workspace.
7. Quick converter, About/updater, i18n, packaging, and cross-platform cutover.
