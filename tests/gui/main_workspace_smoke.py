"""Desktop regression/visual check; keeps user projects and preferences isolated.

Run: .venv/bin/python tests/gui/main_workspace_smoke.py
For a Fluent layout check on macOS add --fluent and set
QT_QUICK_CONTROLS_STYLE=FluentWinUI3 (this is not a Windows system test).
"""
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import qml_main
from PySide6.QtCore import QCoreApplication, QObject, QPoint, QSettings, QTimer, QUrl, Qt, qInstallMessageHandler
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtWebEngineQuick import QtWebEngineQuick
from shiboken6 import getCppPointer, wrapInstance

from ui.macos_integration import MacOSIntegration
from ui.qml_backend.app_bridge import AppBridge
from ui.qml_backend.features.ui_state_bridge import UiStateBridge
from ui.qml_backend.features.workspace_bridge import WorkspaceBridge
import services.global_settings_service as gs

isolated = tempfile.TemporaryDirectory(prefix="dm-main-smoke-")
root = Path(isolated.name)
gs.SETTINGS_FILE = root / "settings.json"
QtWebEngineQuick.initialize()
if "--fluent" in sys.argv:
    QCoreApplication.setAttribute(Qt.AA_DontUseNativeMenuBar)
app = QGuiApplication(sys.argv)
dark = "--dark" in sys.argv
system_scheme = app.styleHints().colorScheme()
initial_theme = "dark" if dark else "light"
ui = UiStateBridge(QSettings(str(root / "ui.ini"), QSettings.IniFormat))
ui.setStringValue("main.theme", initial_theme)
ui.setIntValue("onboarding.interfaceVersion", 1)
ui.setIntValue("main.width", 1540)
ui.setIntValue("main.height", 940)
bridge = AppBridge(ui_state=ui)
assert bridge.project.canOpenAudiobook
bridge._project_service.set_backup_config({"enabled": False})
platform = MacOSIntegration()
engine = QQmlEngine()
engine.rootContext().setContextProperty("platformIntegration", platform)
data = bridge._session.data
data["project_name"] = "Северный маяк"
names = ["Анна Лебедева", "Михаил Волков", "Дарья Соколова", "Алексей Морозов", "Павел Орлов", "Елена Белова"]
colors = ["#367dc4", "#d18e35", "#719d64", "#9876b7", "#48958d", "#c9717e"]
characters = ["Алиса", "Марк", "Вера", "Капитан", "Рассказчик", "Диспетчер", "Матрос", "Механик", "Незнакомец", "Радио", "Голос в толпе", "Смотритель"]
data["actors"] = {str(i): {"name": name, "color": colors[i], "gender": "Ж" if i in (0, 2, 5) else "М"} for i, name in enumerate(names)}
data["global_map"] = dict(zip(characters[:6], map(str, range(6))))
data["global_map"].update({"Радио": "2", "Голос в толпе": "3", "Смотритель": "1"})
quotes = ["Ты слышишь? Маяк снова работает.", "Я думал, его отключили много лет назад.", "Посмотрите на воду. Там кто-то есть.", "Всем оставаться на своих местах.", "Сигнал повторился ещё раз.", "Северный маяк, ответьте. Как слышите?"]
for number, title in enumerate(["01 · Огни гавани", "02 · Северный берег", "03 · Возвращение"]):
    path = str(root / f"episode-{number}.ass")
    Path(path).write_text("[Script Info]\nTitle: Demo\n", encoding="utf-8")
    data["episodes"][title] = path
    bridge._script_text_service.create_episode_text(data, title, path, [
        {"id": i, "s": i * 8.5, "e": i * 8.5 + 4, "char": characters[i % 12],
         "text": quotes[i % 6]} for i in range(144)
    ], bridge._script_text_service.get_merge_config(data))
if shutil.which("ffmpeg"):
    video_path = root / "test-video.mp4"
    subprocess.run([shutil.which("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
                    "color=c=0x303744:size=320x180:rate=25", "-t", "70", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-y", str(video_path)], check=True)
    data["video_paths"]["01 · Огни гавани"] = str(video_path)
bridge.refresh()
bridge.casting.selectCharacter("Алиса")
qml_dir = Path("qml").resolve()
fluent = "--fluent" in sys.argv
if fluent:
    qml_dir = root / "qml"
    shutil.copytree(Path("qml"), qml_dir)
    shutil.copytree(Path("resources"), root / "resources")
    for path in qml_dir.rglob("*.qml"):
        content = path.read_text().replace('Qt.platform.os === "osx"', "false").replace('Qt.platform.os === "windows"', "true")
        path.write_text(content)
messages = []
def handler(kind, context, message):
    if any(word in message for word in ("ReferenceError", "TypeError", "Binding loop", "Cannot assign", "Unable to assign", "non-existent", "not found")):
        messages.append(message)
    print(message, flush=True)
qInstallMessageHandler(handler)
component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_dir / "Main.qml")))
if component.isError():
    raise RuntimeError("\n".join(error.toString() for error in component.errors()))
window = component.createWithInitialProperties({"appBridge": bridge, "macOSIntegration": platform})
if window is None:
    raise RuntimeError("\n".join(error.toString() for error in component.errors()))
window = wrapInstance(getCppPointer(window)[0], QQuickWindow)
if not fluent:
    platform.configure_main_window(window, bridge.project)
window.setProperty("startupChromeReady", True)
window.show()
output = Path("output/main-window-selected-elements")
output.mkdir(parents=True, exist_ok=True)
prefix = ("fluent-emulated" if fluent else "macos") + ("-dark" if dark else "")
failures = []
def check(value, label):
    print(("PASS " if value else "FAIL ") + label, flush=True)
    if not value:
        failures.append(label)
def evaluate(code, context=window):
    expression = QQmlExpression(QQmlEngine.contextForObject(context) or engine.rootContext(), context, code)
    result = expression.evaluate()
    if expression.hasError():
        raise AssertionError(expression.error().toString())
    return result
def choose_combo(dialog, name, index):
    combo = dialog.findChild(QObject, name)
    if fluent:
        evaluate("currentIndex = " + str(index) + "; activated(" + str(index) + ")", combo)
    else:
        platform.comboMenuSelected.emit(combo.property("nativeMenuToken"), index)

def click_dialog_button(dialog, name):
    button = wrapInstance(getCppPointer(dialog.findChild(QObject, name))[0], QQuickItem)
    point = button.mapToScene(button.boundingRect().center())
    QTest.mouseClick(dialog, Qt.LeftButton, Qt.NoModifier, QPoint(round(point.x()), round(point.y())))

def open_main_settings():
    check(bridge.workspace.workflow == 0, "Casting is the default startup section")
    ui.setIntValue("settings.lastPage", 1)
    dialog = window.findChild(QObject, "globalSettingsDialog")
    evaluate("openSettings()", dialog)
    QTimer.singleShot(250, cancel_main_settings)

def cancel_main_settings():
    dialog = wrapInstance(getCppPointer(window.findChild(QObject, "globalSettingsDialog"))[0], QQuickWindow)
    # Qt window captures omit the native AppKit material behind transparent QML.
    # Supply its theme background for visual checks of the dialog's contents.
    dialog.setColor(QColor("#202020" if dark else "#f7f7f7"))
    dialog.grabWindow().save(str(output / (prefix + "-main-settings.png")))
    click_dialog_button(dialog, "compactCastingRows")
    choose_combo(dialog, "themeCombo", 0 if dark else 1)
    choose_combo(dialog, "startupWorkflowCombo", 1)
    choose_combo(dialog, "timelinePlacementCombo", 1)
    check(dialog.property("characterCompactRowsDraft"),
          "changing timeline settings preserves the compact rows choice")
    click_dialog_button(dialog, "cancelGlobalSettings")
    check(bridge.workspace.startupWorkflow == 0 and window.property("episodeTimelinePlacement") == "table",
          "Cancel keeps startup and timeline settings unchanged")
    check(bridge.theme.mode == initial_theme,
          "Cancel keeps the active and saved theme unchanged")
    evaluate("openSettings()", dialog)
    QTimer.singleShot(250, save_main_settings)

def save_main_settings():
    dialog = wrapInstance(getCppPointer(window.findChild(QObject, "globalSettingsDialog"))[0], QQuickWindow)
    check(dialog.findChild(QObject, "startupWorkflowCombo").property("currentIndex") == 0,
          "startup combo resets after Cancel")
    check(dialog.findChild(QObject, "timelinePlacementCombo").property("currentIndex") == 0,
          "timeline placement combo resets after Cancel")
    check(not dialog.findChild(QObject, "compactCastingRows").property("checked"),
          "compact rows checkbox resets after Cancel")
    check(dialog.findChild(QObject, "themeCombo").property("currentIndex") == (1 if dark else 0),
          "theme combo resets after Cancel")
    choose_combo(dialog, "themeCombo", 0 if dark else 1)
    choose_combo(dialog, "startupWorkflowCombo", 1)
    choose_combo(dialog, "timelinePlacementCombo", 1)
    choose_combo(dialog, "timelineSortCombo", 2)
    dialog.setProperty("uiScalePercentDraft", 80)
    click_dialog_button(dialog, "saveGlobalSettings")
    check(not dialog.isVisible(), "settings Save closes the dialog")
    check(bridge.workspace.startupWorkflow == 1 and bridge.workspace.workflow == 0,
          "startup choice saved without switching the current section")
    check(window.property("uiScalePercent") == 80, "interface scale stays synchronized after Save")
    reopened = WorkspaceBridge(bridge._session, bridge._script_text_service,
                               bridge._project_folder_service, bridge.casting, ui)
    check(reopened.workflow == 1, "a new workspace opens the configured Text section")
    QTimer.singleShot(250, check_main_settings_layout)

def check_main_settings_layout():
    check(bridge.theme.mode == ("light" if dark else "dark"), "Save persists the selected theme")
    check(app.styleHints().colorScheme() == (Qt.ColorScheme.Light if dark else Qt.ColorScheme.Dark),
          "Save applies the native Qt color scheme without restarting")
    check(window.property("darkTheme") != dark, "the live QML palette follows the saved theme")
    dialog = window.findChild(QObject, "globalSettingsDialog")
    check(dialog.property("darkPalette") != dark,
          "auxiliary windows update their palette with the main window")
    window.grabWindow().save(str(output / (prefix + "-theme-switched.png")))
    if not fluent:
        from AppKit import NSAppearanceNameAqua, NSAppearanceNameDarkAqua
        appearance = platform._ns_window.effectiveAppearance().bestMatchFromAppearancesWithNames_(
            [NSAppearanceNameAqua, NSAppearanceNameDarkAqua])
        check(appearance == (NSAppearanceNameAqua if dark else NSAppearanceNameDarkAqua),
              "native AppKit chrome follows the selected theme")
    bottom = window.findChild(QObject, "castingBottomTimeline")
    check(bottom.property("visible") and abs(bottom.property("width") - window.width()) <= 16,
          "Casting bottom timeline spans the full window")
    window.grabWindow().save(str(output / (prefix + "-casting-bottom.png")))
    bridge.workspace.setWorkflow(1)
    timeline = window.findChild(QObject, "workspaceTimeline")
    check(timeline.property("visible") and not bottom.property("visible"),
          "Text uses its own timeline under replicas and video")
    window.setProperty("episodeTimelineVisible", False)
    check(not timeline.property("visible"), "timeline visibility preference applies to Text")
    window.setProperty("episodeTimelineVisible", True)
    window.setProperty("episodeTimelineActorColors", False)
    check(not timeline.property("useActorColors") and not bottom.property("useActorColors"),
          "timeline color preference applies to both sections")
    window.setProperty("episodeTimelineActorColors", True)
    bridge.workspace.setWorkflow(0)
    window.setProperty("episodeTimelinePlacement", "table")
    bridge.casting.setTimelineSortMode("appearance")
    window.setProperty("episodeTimelineSortMode", "appearance")
    bridge.theme.setMode("system")
    QTimer.singleShot(250, check_system_theme)

def check_system_theme():
    check(bridge.theme.mode == "system" and app.styleHints().colorScheme() == system_scheme,
          "System theme restores the operating system appearance")
    bridge.theme.setMode(initial_theme)
    QTimer.singleShot(250, capture)

def capture():
    check(not bridge.project.canOpenAudiobook, "serial project disables the audiobook action")
    if fluent:
        check(not window.findChild(QObject, "audiobookToolbarButton").property("enabled"),
              "Fluent audiobook toolbar button is disabled for a serial")
    else:
        item = platform._delegate.items[platform.AUDIOBOOK]
        check(not platform._delegate.validateToolbarItem_(item) and not item.isEnabled(),
              "native audiobook toolbar button is disabled for a serial")
    window.grabWindow().save(str(output / (prefix + "-casting.png")))
    check(bridge.workspace.totalCount == 144, "script loaded")
    if not fluent:
        check(platform.nativeToolbarActive, "native AppKit toolbar active")
        check(platform._delegate.workspace_control.segmentCount() == 2, "native two-mode control")
    check(bridge.workspace.unassignedCount == 3, "unassigned count")
    check(bool(bridge.workspace.characterInfo), "character inspector populated")
    if fluent:
        modes = window.findChild(QObject, "workspaceModes")
        evaluate("select(1)", modes)
        check(bridge.workspace.workflow == 1, "Fluent mode control navigates")
        bridge.workspace.setWorkflow(0)
        check(modes.property("currentIndex") == 0, "Fluent mode follows backend after activation")
    bridge.workspace.openCharacter("Алиса")
    QTimer.singleShot(300, capture_text)
def capture_text():
    window.grabWindow().save(str(output / (prefix + "-text.png")))
    if not fluent:
        check(platform._delegate.workspace_control.selectedSegment() == 1, "native mode follows workspace")
    check(bridge.workspace.count == 12, "character filter opens matching replicas")
    if bridge.workspace.hasVideo:
        player = window.findChild(QObject, "workspaceVideo")
        check(player.property("duration") > 0, "embedded video loads")
    timeline = window.findChild(QObject, "workspaceTimeline")
    ruler = timeline.findChild(QObject, "timelineRuler")
    # Click the real ruler at 52 seconds, which is inside the Matros replica.
    seconds = 52
    point = evaluate("mapToItem(null, parent.timelineStartX + parent.availableWidth * "
                     + str(seconds / bridge.casting.timelineDuration) + ", height / 2)", ruler)[0]
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(round(point.x()), round(point.y())))
    check(bridge.workspace.selected["character"] == "Матрос", "mouse click on ruler selects active replica")
    if bridge.workspace.hasVideo:
        check(abs(player.property("position") - seconds * 1000) < 1000, "timeline mouse click seeks video")
    pending = [wrapInstance(getCppPointer(timeline)[0], QQuickItem)]
    visual_segments = []
    while pending:
        item = pending.pop()
        pending.extend(item.childItems())
        if item.objectName() == "timelineSegment":
            visual_segments.append(item)
    first = next(segment for segment in visual_segments if segment.property("start") == 0)
    point = first.mapToScene(first.boundingRect().center())
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(round(point.x()), round(point.y())))
    check(bridge.workspace.selected["number"] == 1, "mouse click on segment selects its replica")
    bridge.workspace.openCharacter("Алиса")
    original = bridge.workspace.selected["text"]
    editor = window.findChild(QObject, "scriptTextEditor")
    evaluate("forceActiveFocus()", editor)
    evaluate("selectAll()", editor)
    for character in "edited dialogue":
        QTest.keyClick(window, Qt.Key(ord(character.upper())), Qt.ShiftModifier if character.isupper() else Qt.NoModifier)
    check(bridge.workspace.draftDirty, "typing stages text")
    check(bridge.workspace.flush(), "edit applied")
    check(bridge.workspace.selected["text"] == "edited dialogue", "canonical line updated from editor: " + repr(bridge.workspace.selected["text"]))
    bridge.project.undo()
    check(bridge.workspace.selected["text"] == original, "undo restores line")
    bridge.project.redo()
    check(bridge.workspace.selected["text"] == "edited dialogue", "redo restores edit")
    bridge.workspace.setDraftField("outTime", "invalid")
    before = bridge.project.currentEpisode
    # Avoid modal error UI during the deliberate invalid-timing check.
    bridge.workspace.errorRequested.disconnect()
    bridge.project.selectEpisode("02 · Северный берег")
    check(bridge.project.currentEpisode == before, "invalid draft blocks navigation")
    check(bridge.workspace.draftDirty, "invalid draft retained")
    if fluent:
        modes = window.findChild(QObject, "workspaceModes")
        evaluate("select(0)", modes)
        check(modes.property("currentIndex") == 1, "Fluent mode retains selection after rejected navigation")
    else:
        platform._delegate.workspace_control.setSelectedSegment_(0)
        platform._delegate.workspaceChanged_(platform._delegate.workspace_control)
        check(platform._delegate.workspace_control.selectedSegment() == 1, "native mode retains selection after rejected navigation")
    bridge.workspace.discardDraft()
    if not fluent:
        platform._delegate.workspace_control.setSelectedSegment_(0)
        platform._delegate.workspaceChanged_(platform._delegate.workspace_control)
        check(bridge.workspace.workflow == 0, "native mode control navigates")
    bridge.workspace.setWorkflow(0)
    window.resize(760, 800)
    QTimer.singleShot(300, capture_compact)
def capture_compact():
    window.grabWindow().save(str(output / (prefix + "-compact.png")))
    check(window.property("compactLayout"), "compact layout")
    evaluate("toggleInspector()")
    QTimer.singleShot(150, close_inspector)
def close_inspector():
    evaluate("toggleInspector()")
    bridge.workspace.setWorkflow(1)
    window.resize(1180, 820)
    QTimer.singleShot(200, capture_medium)
def capture_medium():
    window.grabWindow().save(str(output / (prefix + "-medium-text.png")))
    window.resize(680, 720)
    QTimer.singleShot(200, capture_small_text)
def capture_small_text():
    window.grabWindow().save(str(output / (prefix + "-small-text.png")))
    QTimer.singleShot(150, finish)
def finish():
    evaluate("setQuickConverterVisible(true, true)")
    check(window.property("converterShown"), "converter remains available in text and narrow windows")
    evaluate("setQuickConverterVisible(false, true)")
    bridge.project.create()
    evaluate("saveChangesDialog.close()")
    bridge.project.resolvePendingChanges("discard")
    check(bridge.project.canOpenAudiobook, "New project re-enables the audiobook action")
    QTimer.singleShot(250, finish_new_project)

def finish_new_project():
    if fluent:
        check(window.findChild(QObject, "audiobookToolbarButton").property("enabled"),
              "Fluent audiobook button re-enables after New")
    else:
        item = platform._delegate.items[platform.AUDIOBOOK]
        check(platform._delegate.validateToolbarItem_(item) and item.isEnabled(),
              "native audiobook button re-enables after New")
    window.resize(1540, 940)
    panel = window.findChild(QObject, "inlineEpisodeSidebar")
    evaluate("SplitView.preferredWidth = 160", panel)
    bridge.workspace.setWorkflow(0)
    QTimer.singleShot(250, lambda: check_empty_sidebar(0))

def check_empty_sidebar(step):
    panel = wrapInstance(getCppPointer(window.findChild(QObject, "inlineEpisodeSidebar"))[0], QQuickItem)
    expected_width = 160 if step < 2 else 200
    check(panel.isVisible() and abs(panel.width() - expected_width) <= 1,
          f"inline sidebar uses the requested width, layout {step}")
    for name in ("episodeImportButton", "workspaceEpisodes", "episodeActionsButton",
                 "episodeFilesButton", "episodeSettingsButton"):
        item = wrapInstance(getCppPointer(panel.findChild(QObject, name))[0], QQuickItem)
        left = item.mapToItem(panel, item.boundingRect().topLeft()).x()
        check(left >= 8 and left + item.width() <= panel.width() - 8,
              f"empty sidebar contains {name}, layout {step}")
    hint = wrapInstance(getCppPointer(panel.findChild(QObject, "episodeSidebarEmptyState"))[0], QQuickItem)
    center = hint.mapToItem(panel, hint.boundingRect().center()).x()
    check(abs(center - panel.width() / 2) <= 1, f"sidebar empty hint stays centered, layout {step}")
    section = "casting" if bridge.workspace.workflow == 0 else "text"
    window.grabWindow().save(str(output / f"{prefix}-empty-{section}-{round(panel.width())}.png"))
    if step < 3:
        if step == 1:
            evaluate("SplitView.preferredWidth = 200", panel)
        bridge.workspace.setWorkflow(1 if step % 2 == 0 else 0)
        QTimer.singleShot(250, lambda: check_empty_sidebar(step + 1))
        return
    prepare_saved_audiobook()

def prepare_saved_audiobook():
    from services.audiobook_document_service import AudiobookDocumentService
    bridge._session.data["project_kind"] = "audiobook"
    bridge._session.data["audiobook_document"] = AudiobookDocumentService().create_document("", [])
    bridge._session.notify_changed("project_files")
    bridge.project.saveAs(str(root / "saved-book.dmproj"))
    saved_book = bridge.project.path
    bridge.project.create()
    bridge.project.open(saved_book)
    QTimer.singleShot(250, finish_opened_audiobook)

def finish_opened_audiobook():
    check(bridge.project.canOpenAudiobook and bridge._session.data["project_kind"] == "audiobook",
          "an opened audiobook keeps access to its editor")
    if fluent:
        check(window.findChild(QObject, "audiobookToolbarButton").property("enabled"),
              "Fluent audiobook button is active for an opened audiobook")
    else:
        check(platform._delegate.items[platform.AUDIOBOOK].isEnabled(),
              "native audiobook button is active for an opened audiobook")
    evaluate("audiobookWindow.openWorkspace()")
    book = wrapInstance(getCppPointer(window.findChild(QObject, "audiobookWindow"))[0], QQuickWindow)
    if not fluent:
        platform.configure_window(book)
    book.setColor(QColor("#202020" if dark else "#f7f7f7"))
    QTimer.singleShot(350, lambda: check_empty_audiobook(0))

def check_empty_audiobook(step):
    book = wrapInstance(getCppPointer(window.findChild(QObject, "audiobookWindow"))[0], QQuickWindow)
    area = wrapInstance(getCppPointer(book.findChild(QObject, "audiobookEditorArea"))[0], QQuickItem)
    content = wrapInstance(getCppPointer(book.findChild(QObject, "audiobookEmptyContent"))[0], QQuickItem)
    center = content.mapToItem(area, content.boundingRect().center())
    check(abs(center.x() - area.width() / 2) <= 1 and abs(center.y() - area.height() / 2) <= 1,
          f"audiobook preparation is centered in the editor area, layout {step}")
    tabs = wrapInstance(getCppPointer(book.findChild(QObject, "audiobookWorkflowTabs"))[0], QQuickItem)
    check(abs(tabs.mapToScene(tabs.boundingRect().center()).x() - book.width() / 2) <= 1,
          f"audiobook workflow tabs are centered in the window, layout {step}")
    sidebar = wrapInstance(getCppPointer(book.findChild(QObject, "audiobookChapterSidebar"))[0], QQuickItem)
    speed = wrapInstance(getCppPointer(book.findChild(QObject, "audiobookReadingSpeed"))[0], QQuickItem)
    left = speed.mapToItem(sidebar, speed.boundingRect().topLeft()).x()
    check(left >= 10 and left + speed.width() <= sidebar.width() - 10,
          f"audiobook reading speed stays inside the sidebar, layout {step}")
    fits_value = evaluate("contentItem.width >= contentItem.contentWidth", speed)[0]
    check(fits_value, f"audiobook reading speed displays the complete value, layout {step}")
    book.grabWindow().save(str(output / f"{prefix}-empty-audiobook-{step}.png"))
    if step < 2:
        if step == 0:
            book.resize(1000, 680)
            evaluate("SplitView.preferredWidth = 170", sidebar)
        else:
            book.setProperty("sidebarVisible", False)
        QTimer.singleShot(250, lambda: check_empty_audiobook(step + 1))
        return
    book.close()
    finish_checks()

def finish_checks():
    check(not messages, "no QML runtime errors: " + repr(messages[:5]))
    (output / (prefix + "-checks.json")).write_text(json.dumps({"failures": failures, "qmlErrors": messages}, ensure_ascii=False, indent=2))
    window.setProperty("closeApproved", True)
    window.close()
    app.exit(1 if failures else 0)
QTimer.singleShot(1800, open_main_settings)
QTimer.singleShot(30000, lambda: app.exit(3))
code = app.exec()
qInstallMessageHandler(None)
window.deleteLater()
QCoreApplication.sendPostedEvents(None, 52)
bridge.audiobook.shutdown()
sys.exit(code)
