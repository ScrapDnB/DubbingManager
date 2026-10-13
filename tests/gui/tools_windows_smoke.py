"""Isolated teleprompter/montage interaction and visual checks.

Run .venv/bin/python tests/gui/tools_windows_smoke.py [--fluent] [--dark].
Fluent on macOS verifies Qt controls/layout, not Windows/DWM itself.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if '--all' in sys.argv:
    statuses = []
    for options in ([], ['--dark'], ['--fluent'], ['--fluent', '--dark']):
        result = subprocess.run([sys.executable, __file__, *options], check=False)
        statuses.append(result.returncode)
    sys.exit(any(statuses))
import qml_main  # Configure WebEngine before importing Qt.
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPoint, QSettings, QUrl, Qt, qInstallMessageHandler
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest
from PySide6.QtWebEngineQuick import QtWebEngineQuick
from shiboken6 import getCppPointer, wrapInstance
import services.global_settings_service as settings_module
from ui.macos_integration import MacOSIntegration
from ui.qml_backend.app_bridge import AppBridge
from ui.qml_backend.features.ui_state_bridge import UiStateBridge

fluent = '--fluent' in sys.argv
QQuickStyle.setStyle('FluentWinUI3' if fluent else 'macOS')
QtWebEngineQuick.initialize()
app = QGuiApplication(sys.argv)
scratch_context = tempfile.TemporaryDirectory(prefix='dm-tool-windows-')
scratch = Path(scratch_context.name)
settings_module.SETTINGS_FILE = scratch / 'settings.json'
ui = UiStateBridge(QSettings(str(scratch/'ui.ini'), QSettings.IniFormat))
dark = '--dark' in sys.argv
ui.setStringValue('main.theme', 'dark' if dark else 'light')
bridge = AppBridge(ui_state=ui)
bridge._project_service.set_backup_config({'enabled': False})
platform = MacOSIntegration()
engine = QQmlEngine()
engine.rootContext().setContextProperty('platformIntegration', platform)
qml_dir = ROOT/'qml'
if fluent:
    qml_dir = scratch/'qml'
    shutil.copytree(ROOT/'qml', qml_dir)
    shutil.copytree(ROOT/'resources', scratch/'resources')
    for p in qml_dir.rglob('*.qml'):
        p.write_text(p.read_text().replace('Qt.platform.os === "osx"', 'false')
                     .replace('Qt.platform.os === "windows"', 'true'))
data = bridge._session.data
data['project_name'] = 'Орбитальная станция'
data['actors'] = {'nav': {'name': 'Анна Миронова', 'color': '#ffc34c'},
                  'eng': {'name': 'Елена Соколова', 'color': '#78d9ca'}}
data['global_map'] = {'НАВИГАТОР': 'nav', 'ИНЖЕНЕР': 'eng'}
quotes = [
    (5., 7., 'СИСТЕМА', 'Проверка связи. Центральный модуль отвечает без задержки.'),
    (10., 14., 'НАВИГАТОР', 'Маршрут рассчитан, до стыковки осталось меньше минуты.'),
    (15., 17., 'ИНЖЕНЕР', 'Вижу маяк станции. Перехожу на ручное управление.'),
    (18., 28., 'НАВИГАТОР', 'Подтверждаю курс. Коррекция по второй оси завершена.'),
    (72., 76., 'НАВИГАТОР', 'Команда на борту, можно открывать внутренний шлюз.'),
    (82., 85., 'ИНЖЕНЕР', 'Все системы готовы.'),
]
for episode in ('1', '2'):
    path = scratch/f'{episode}.ass'
    path.write_text('[Script Info]\nTitle: Demo\n')
    data['episodes'][episode] = str(path)
    bridge._script_text_service.create_episode_text(data, episode, str(path), [
        {'id': str(i), 's': s, 'e': e, 'char': c, 'text': t}
        for i, (s,e,c,t) in enumerate(quotes)
    ], bridge._script_text_service.get_merge_config(data))
bridge.refresh()
config = bridge.teleprompter.config
config.update({'osc_enabled': False, 'page_scroll_mode': True, 'focus_ratio': .1})
bridge._global_settings_service.set_default_prompter_config(config)
errors, failures, checks = [], [], []
def handler(kind, context, message):
    if any(word in message for word in ('ReferenceError','TypeError','Binding loop','Cannot assign','Unable to assign','non-existent','failed to load','Cannot load')):
        errors.append(message)
    print(message, flush=True)
qInstallMessageHandler(handler)
def check(condition, label):
    checks.append(label)
    if not condition:
        failures.append(label)
    print(('PASS ' if condition else 'FAIL ')+label, flush=True)
def settle(seconds=.25):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.005)
def evaluate(obj, code):
    expr = QQmlExpression(QQmlEngine.contextForObject(obj) or engine.rootContext(), obj, code)
    result = expr.evaluate()
    if expr.hasError():
        raise AssertionError(expr.error().toString())
    return result[0] if isinstance(result, tuple) else result
def create(name):
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_dir/'components'/name)))
    result = component.createWithInitialProperties({
        'appBridge':bridge, 'softBorder':QColor('#dddddd'), 'softHeader':QColor('#eeeeee'),
        'softRow':QColor('#ffffff'), 'softAltRow':QColor('#fafafa'), 'softMuted':QColor('#888888'),
    })
    if result is None:
        raise AssertionError('\n'.join(x.toString() for x in component.errors()))
    result = wrapInstance(getCppPointer(result)[0], QQuickWindow)
    result.setColor(QColor('#202020' if dark else '#f7f7f7'))
    return component, result
def click(win, name):
    item = wrapInstance(getCppPointer(win.findChild(QObject, name))[0], QQuickItem)
    point = item.mapToScene(item.boundingRect().center())
    QTest.mouseClick(win, Qt.LeftButton, Qt.NoModifier, QPoint(round(point.x()),round(point.y())))
    settle()
def in_bounds(win, name):
    obj = win.findChild(QObject, name)
    item = wrapInstance(getCppPointer(obj)[0], QQuickItem)
    pos = item.mapToScene(item.boundingRect().topLeft())
    return pos.x() >= 0 and pos.y() >= 0 and pos.x()+item.width() <= win.width()+1 and pos.y()+item.height() <= win.height()+1
def reading_font_sizes(win):
    root = wrapInstance(getCppPointer(win.findChild(QObject, 'teleprompterReplicaView'))[0], QQuickItem)
    # ListView delegates belong to its visual tree, not the window's QObject tree.
    pending, reading_items = [root], []
    while pending:
        item = pending.pop()
        reading_items.append(item)
        pending.extend(item.childItems())
    result = {}
    for name in ('Timecode', 'Character', 'Actor', 'Text'):
        items = [item for item in reading_items if item.objectName() == 'teleprompterReplica' + name]
        check(bool(items), 'reading ' + name.lower() + ' is instantiated')
        result[name] = {evaluate(item, 'fontInfo.pixelSize') for item in items}
    return result
output=ROOT/'output'/'tools-window-redesign'
output.mkdir(parents=True, exist_ok=True)
prefix=('fluent-emulated' if fluent else 'macos')+('-dark' if dark else '')
windows=[]
try:
    tc, tele=create('TeleprompterWindow.qml'); windows.append(tele)
    evaluate(tele, 'openFor("1")')
    settle()
    tele.resize(1400, 920)
    bridge.teleprompter.jumpToIndex(1)
    settle(.8)
    check(tele.transientParent() is None, 'teleprompter remains an independent window')
    font_family=tele.property('timecodeFontFamily')
    check(font_family == 'Chakra Petch', 'bundled timecode font loads')
    timer=tele.findChild(QObject,'teleprompterTimecode')
    check(timer.property('text') == '00:10.000', 'timer keeps millisecond precision')
    timer_font_size = evaluate(timer, 'fontInfo.pixelSize')
    for key, value in {'f_tc': 40, 'f_char': 34, 'f_actor': 26, 'f_text': 44,
                       'show_end_timecode': True}.items():
        bridge.teleprompter.setConfigValue(key, value)
    settle()
    expected_font_sizes = {'Timecode': {40}, 'Character': {34}, 'Actor': {26}, 'Text': {44}}
    check(reading_font_sizes(tele) == expected_font_sizes, 'reading fonts use configured sizes in a large window')
    tele.grabWindow().save(str(output/(prefix+'-teleprompter.png')))
    check(bridge.teleprompter.config['page_scroll_mode'], 'page mode restored from settings')
    click(tele, 'teleprompterContinuousMode')
    check(not bridge.teleprompter.config['page_scroll_mode'], 'native continuous radio changes mode')
    click(tele, 'teleprompterPageMode')
    check(bridge.teleprompter.config['page_scroll_mode'], 'native page radio changes mode')
    click(tele, 'teleprompterNextReplica')
    check(bridge.teleprompter.currentIndex == 2, 'toolbar advances to the next replica')
    click(tele, 'teleprompterPreviousReplica')
    check(bridge.teleprompter.currentIndex == 1, 'toolbar returns to previous replica')
    evaluate(tele,'quickSearchText = "маяк"; refreshQuickSearch(false)')
    check(evaluate(tele,'quickSearchMatches.length') == 1, 'quick search still finds dialogue')
    evaluate(tele,'navigateQuickSearch(1)'); settle()
    check(evaluate(tele, 'quickSearchNavigationActive && !followEnabled'), 'quick search reveals a match without seeking DAW')
    evaluate(tele,'quickSearchText = ""; refreshQuickSearch(false)')
    evaluate(tele,'actorFilterWindow.open()'); settle()
    check(evaluate(tele,'actorFilterWindow.visible'), 'actor filter opens')
    evaluate(tele,'actorFilterWindow.close(); floatWindow.openNearOwner()'); settle()
    check(evaluate(tele,'floatWindow.visible'), 'floating controller opens')
    controller = wrapInstance(getCppPointer(tele.findChild(QObject, 'teleprompterFloatWindow'))[0], QQuickWindow)
    controller.setPosition(300, 180); settle()
    drag_area = wrapInstance(getCppPointer(controller.findChild(QObject, 'teleprompterFloatTitleDragArea'))[0], QQuickItem)
    drag_center = drag_area.mapToScene(drag_area.boundingRect().center())
    drag_point = QPoint(round(drag_center.x()), round(drag_center.y()))
    original_position = controller.position()
    original_size = controller.size()
    QTest.mousePress(controller, Qt.LeftButton, Qt.NoModifier, drag_point)
    QTest.mouseMove(controller, drag_point + QPoint(48, 30), 20)
    QTest.mouseRelease(controller, Qt.LeftButton, Qt.NoModifier, drag_point)
    settle()
    displacement = controller.position() - original_position
    check(abs(displacement.x() - 48) <= 2 and abs(displacement.y() - 30) <= 2,
          'dragging the controller title moves its window')
    check(controller.size() == original_size, 'dragging the controller title preserves its size')
    evaluate(tele,'floatWindow.close(); sidePanelVisible = false'); settle()
    check(not tele.property('sidePanelVisible'), 'reading area can hide settings')
    evaluate(tele,'sidePanelVisible = true; openReplicaEditor(["1"], "НАВИГАТОР", "Проверка редактора")'); settle()
    check(evaluate(tele,'editWindow.visible'), 'replica editor opens')
    evaluate(tele,'editWindow.close()')
    bridge.teleprompter.setConfigValue('is_mirrored', True); settle()
    check(evaluate(tele,'replicaView.transform[0].xScale') == -1, 'mirror mode retains its reading transform')
    bridge.teleprompter.setConfigValue('is_mirrored', False)
    original_header = tele.property('headerHeight')
    tele.setProperty('headerHeight', original_header + 12)
    settle()
    check(evaluate(tele,'teleprompterHeader.height') == original_header + 12, 'timer header remains resizable')
    check(evaluate(timer, 'fontInfo.pixelSize') == timer_font_size, 'resizing the header preserves the timer font size')
    tele.setProperty('headerHeight', original_header)
    tele.resize(760,520); settle()
    check(reading_font_sizes(tele) == expected_font_sizes, 'reading fonts keep configured sizes in a small window')
    check(evaluate(timer, 'fontInfo.pixelSize') == timer_font_size, 'resizing the window preserves the timer font size')
    check(in_bounds(tele,'teleprompterNextReplica') and in_bounds(tele,'teleprompterTimecode'), 'teleprompter controls fit minimum window size')
    tele.grabWindow().save(str(output/(prefix+'-teleprompter-small.png')))
    tele.close(); settle()

    config = bridge.montage.config
    bridge.montage.setOption('layout_type','Сценарий 3')
    bridge.montage.setOption('col_actor',True)
    bridge.montage.setOption('highlight_character_only',True)
    bridge.montage.setOption('soften_colors',True)
    bridge.montage.setOption('color_softening_level',1)
    bridge.montage.setOption('open_auto',False)
    mc,montage=create('MontagePreviewDialog.qml'); windows.append(montage)
    evaluate(montage,'openFor("1")'); montage.resize(1400,920); settle(1)
    check('montage-preview-document' in bridge.montage.html, 'document canvas is present in preview')
    montage.grabWindow().save(str(output/(prefix+'-montage.png')))
    click(montage, 'montageTimeStart')
    check(bridge.montage.config['time_display'] == 'start', 'native time radio sets start-only display')
    click(montage, 'montageTimeRange')
    check(bridge.montage.config['time_display'] == 'range', 'native time radio restores range')
    click(montage, 'montageFormatXlsx')
    check(bridge.montage.config['format_xls'], 'XLSX format checkbox persists')
    click(montage, 'montageFormatPdf')
    check(bridge.montage.config['format_pdf'], 'PDF format checkbox persists')
    # Exercise Chromium input/blur -> WebChannel -> working text -> undo.
    deadline = time.monotonic() + 3
    while evaluate(montage, 'previewBrowser.updating') and time.monotonic() < deadline:
        settle(.05)
    settle(.3)
    edit_id = bridge._script_text_service.load_atomic_episode_lines(data, '1')[1]['id']
    javascript = ('var el = document.getElementById(' + json.dumps(str(edit_id))
        + '); el.focus(); el.innerText = "Исправленная реплика";'
        + 'el.dispatchEvent(new Event("input", {bubbles:true})); onBlur(el); el.blur();')
    evaluate(montage, 'previewBrowser.runJavaScript(' + json.dumps(javascript) + ')')
    settle(.8)
    check('Исправленная реплика' in bridge.montage.html, 'WebChannel edits update the working text')
    bridge.project.undo(); settle()
    check('Исправленная реплика' not in bridge.montage.html, 'preview edits retain undo')
    # Export all actual formats for both episodes, without opening another app.
    bridge.montage.exportBatch(str(scratch/'exports'), True, True, True, True, True)
    deadline = time.monotonic() + 10
    while bridge.montage.batchBusy and time.monotonic() < deadline:
        settle(.02)
    results = bridge.montage.batchResultModel.rows()
    # XLSX intentionally combines both episodes into one workbook.
    check(not bridge.montage.batchBusy and len(results) == 7
          and all(r['statusKind'] == 'success' for r in results), 'batch exports HTML/XLSX/DOCX/PDF for all episodes')
    check(all(Path(r['path']).stat().st_size > 0 for r in results if r['path']), 'all exported files contain data')
    bridge.montage.clearBatchResults()
    # Small viewport must keep export actions available and sidebar scrollable.
    montage.resize(760,520); settle()
    check(in_bounds(montage,'montageExportButton') and in_bounds(montage,'montageAllEpisodes'), 'export controls fit minimum window size')
    montage.grabWindow().save(str(output/(prefix+'-montage-small.png')))
    evaluate(montage,'settingsVisible = false'); settle()
    check(not montage.property('settingsVisible'), 'document can hide settings')
    evaluate(montage,'settingsVisible = true')
    QTest.keyClick(montage,Qt.Key_Escape); settle()
    check(not montage.isVisible(), 'Escape closes montage window')
    check(not errors, 'no QML runtime errors')
finally:
    for window in windows:
        window.close()
        window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    settle()
    bridge.teleprompter.close()
    bridge.audiobook.shutdown()
    bridge.updates.shutdown()
    (output/(prefix+'-checks.json')).write_text(json.dumps({'failures':failures,'qmlErrors':errors,'checks':checks},ensure_ascii=False,indent=2))
print(json.dumps({'failures':failures,'qmlErrors':errors},ensure_ascii=False),flush=True)
sys.exit(bool(failures or errors))
