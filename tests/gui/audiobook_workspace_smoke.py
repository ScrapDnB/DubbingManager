"""Live QML/WebEngine smoke check with isolated demo data; run in a desktop session.

.venv/bin/python tests/gui/audiobook_workspace_smoke.py
QT_QUICK_CONTROLS_STYLE=FluentWinUI3 .venv/bin/python tests/gui/audiobook_workspace_smoke.py --fluent

Screenshots are saved under output/audiobook-implementation. Fluent on macOS is
an emulated layout check and does not replace testing on Windows 11.
"""

import os
import json
import shutil
import tempfile
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import qml_main
from PySide6.QtCore import QTimer, QUrl, QMetaObject, Qt, QSettings, QObject, Signal, Slot, QCoreApplication, QEvent
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickWindow
from shiboken6 import wrapInstance,getCppPointer
from PySide6.QtQml import QQmlEngine, QQmlComponent, QQmlExpression
from PySide6.QtWebEngineQuick import QtWebEngineQuick
from ui.qml_backend.app_bridge import AppBridge
from ui.qml_backend.features.ui_state_bridge import UiStateBridge
from ui.macos_integration import MacOSIntegration
from services.audiobook_document_service import AudiobookDocumentService
import services.global_settings_service as gs
import ui.qml_backend.app_bridge as ab

isolation = tempfile.TemporaryDirectory(prefix='dm-audiobook-smoke-')
isolated = Path(isolation.name)
gs.SETTINGS_FILE=isolated / 'global.json'
ab.UiStateBridge=lambda parent=None: UiStateBridge(QSettings(str(isolated / 'ui.ini'), QSettings.IniFormat),parent)
QtWebEngineQuick.initialize()
app=QGuiApplication(sys.argv)
app.styleHints().setColorScheme(Qt.ColorScheme.Light)
bridge=AppBridge()
service=AudiobookDocumentService()
source=str(isolated / 'severny-svet.txt')
Path(source).write_text('Демонстрационная книга',encoding='utf-8')
body='''<h1>Глава 3. Обсерватория</h1>
<p>Макс остановился у старой обсерватории и выключил диктофон. Над крышей медленно разгоралась тонкая зелёная дуга.</p>
<p><span data-dm-character="Макс" data-dm-actor="max">— Если это маяк, кто-то всё ещё ждёт ответа, — сказал он.</span></p>
<p>В наушниках щёлкнуло. Антенна повернулась на север, и сигнал стал громче.</p>
<p>— Ты тоже слышишь этот сигнал? — тихо спросила Лена.</p>
<p>Сигнал повторился — длинный, низкий, с едва различимой мелодией. Он не походил ни на шум, ни на помехи. И это было послание, обращённое к кому-то далёкому.</p>
<p><span data-dm-character="Лена">Лена посмотрела на приборы и нахмурилась.</span></p>
<p>В этот момент купол обсерватории слегка задрожал, словно от порыва ветра. Где-то в глубине здания послышался скрип, и Макс замер, прислушиваясь.</p>'''
chapters=[('Пролог','<h1>Пролог</h1><p>Ночь на севере всегда была особенной.</p>'),('Глава 1','<h1>Глава 1</h1><p>Первый снег застал их в дороге.</p>'),('Глава 2','<h1>Глава 2</h1><p>Сигнал раздавался каждую минуту.</p>'),('Глава 3',body),('Глава 4','<h1>Глава 4</h1><p>Звёзды стали ярче.</p>'),('Эпилог','<h1>Эпилог</h1><p>Ночь закончилась.</p>')]
bridge._session.data.update({'project_kind':'audiobook','project_name':'Северный свет','episodes':{title:'audiobook' for title,_ in chapters},'audiobook_document':service.create_document(source,chapters),'actors':{'author':{'name':'Анна Миронова','color':'#367dc4'},'max':{'name':'Илья Волков','color':'#c88d25'}},'global_map':{'Автор':'author','Макс':'max'},'audiobook_settings':{'slots':[{'character':'Автор','actor_id':'author'},{'character':'Макс','actor_id':'max'},{'character':'Лена','actor_id':None}],'pronunciations':[{'word':'Альдебаран','pronunciation':'Альдебара́н','note':'Название звезды'}]}})
bridge.refresh()
engine=QQmlEngine()
platform=MacOSIntegration()
engine.rootContext().setContextProperty('platformIntegration',platform)
qml_dir = Path('qml').resolve()
fluent = '--fluent' in sys.argv
if fluent:
    qml_dir = isolated / 'qml'
    shutil.copytree(Path('qml').resolve(), qml_dir)
    for path in qml_dir.rglob('*.qml'):
        text = path.read_text(encoding='utf-8')
        text = text.replace('Qt.platform.os === "osx"', 'false').replace('Qt.platform.os === "windows"', 'true')
        path.write_text(text, encoding='utf-8')
component=QQmlComponent(engine,QUrl.fromLocalFile(str(qml_dir / 'components/AudiobookWindow.qml')))
if component.isError():
 print('\n'.join(e.toString() for e in component.errors()),flush=True);sys.exit(2)
window=component.createWithInitialProperties({'appBridge':bridge,'softBorder':'#dcdce0','softHeader':'#f2f2f4','softRow':'#f5f5f7','softAltRow':'#fafafa','softMuted':'#74747b'})
if window is None:
 print('\n'.join(e.toString() for e in component.errors()),flush=True);sys.exit(3)
window=wrapInstance(getCppPointer(window)[0],QQuickWindow)
QMetaObject.invokeMethod(window,'openWorkspace')
bridge.audiobook.selectChapter('Глава 3')
platform.configure_window(window)
window.setColor('#f3f3f5')
output=Path('output/audiobook-implementation')
output.mkdir(parents=True,exist_ok=True)


class Reporter(QObject):
    completed = Signal(str)

    @Slot(str)
    def complete(self, result):
        self.completed.emit(result)

reporter = Reporter()
engine.rootContext().setContextProperty('qa', reporter)
checks = []
failures = []
reader = None
raw_reader = None
reader_component = None
prefix = 'fluent-emulated' if fluent else 'macos'


def evaluate(script, callback, object_name='audiobookEditorView'):
    web = window.findChild(QObject, object_name)
    expression = QQmlExpression(engine.rootContext(), web, 'runJavaScript(' + json.dumps(script) + ', function(v) { qa.complete(JSON.stringify(v)); })')
    def received(payload):
        reporter.completed.disconnect(received)
        callback(json.loads(payload))
    reporter.completed.connect(received)
    expression.evaluate()
    if expression.hasError():
        raise AssertionError(expression.error().toString())


def ensure(condition, description):
    checks.append(description)
    if not condition:
        failures.append(description)
        print('FAIL:', description, flush=True)
    else:
        print('PASS:', description, flush=True)


def capture():
    ensure(window.property('editorLoaded'), 'WebEngine/WebChannel editor loads')
    window.grabWindow().save(str(output / (prefix + '-editor.png')))
    window.setProperty('workflow', 1)
    bridge.audiobook.openNextReviewItem()
    QTimer.singleShot(700, capture_review)


def capture_review():
    window.grabWindow().save(str(output / (prefix + '-review.png')))
    window.setProperty('workflow', 0)
    evaluate(r"""(() => {
        const editor=document.getElementById('editor');
        window.smokeText=editor.textContent;
        window.smokeParagraphs=editor.querySelectorAll('p').length;
        const span=editor.querySelector('[data-dm-character="Макс"]');
        const r=document.createRange();r.setStart(span.firstChild,3);r.setEnd(span.firstChild,8);
        savedRange=r;getSelection().removeAllRanges();getSelection().addRange(r);
        const ok=window.dmEditor.applyMarkup('Лена','','');
        return {ok,sameText:editor.textContent===window.smokeText,paragraphs:editor.querySelectorAll('p').length};
    })()""", partial_marked)


def partial_marked(result):
    ensure(result['ok'] and result['sameText'], 'Partial role assignment preserves text')
    ensure(result['paragraphs'] == 7, 'Partial role assignment preserves paragraphs')
    QTimer.singleShot(150, check_partial_backend)


def check_partial_backend():
    chapter = bridge.audiobook._parsed_chapter('Глава 3')
    runs = chapter['blocks'][2]['runs']
    ensure(any(r['character']=='Лена' and len(r['text'])==5 for r in runs), 'Partial assignment reaches canonical document')
    ensure(any(r['character']=='Макс' for r in runs), 'Unselected text keeps its role')
    evaluate(r"""(() => {
        window.dmEditor.undo();
        const editor=document.getElementById('editor');
        const undone=editor.textContent===window.smokeText && ![...editor.querySelectorAll('p')[1].querySelectorAll('[data-dm-character]')].some(n=>n.dataset.dmCharacter==='Лена');
        window.dmEditor.redo();
        const redone=[...editor.querySelectorAll('p')[1].querySelectorAll('[data-dm-character]')].some(n=>n.dataset.dmCharacter==='Лена');
        return {undone,redone};
    })()""", check_history)


def check_history(result):
    ensure(result['undone'] and result['redone'], 'Undo and redo restore role assignment')
    evaluate(r"""(() => {
        window.dmEditor.undo();
        const editor=document.getElementById('editor'),p=editor.querySelectorAll('p');
        const start=p[0].querySelector('span').firstChild,end=p[1].querySelector('span').firstChild;
        const r=document.createRange();r.setStart(start,5);r.setEnd(end,10);savedRange=r;
        const ok=window.dmEditor.applyMarkup('Макс','max','');
        const same=editor.textContent===window.smokeText;
        const paragraphs=editor.querySelectorAll('p').length;
        window.dmEditor.undo();
        return {ok,same,paragraphs};
    })()""", check_multiblock)


def check_multiblock(result):
    ensure(result['ok'] and result['same'] and result['paragraphs']==7, 'Cross-paragraph assignment keeps manuscript structure')
    markup = window.findChild(QObject, 'chapterMarkupWindow')
    expression = QQmlExpression(engine.rootContext(), markup, 'openEditor()')
    expression.evaluate()
    if expression.hasError():
        raise AssertionError(expression.error().toString())
    QTimer.singleShot(1000, check_chapter_structure)


def check_chapter_structure():
    evaluate(r"""(() => {
        const before=document.getElementById('source').textContent;
        const first=document.querySelector('.dm-boundary');
        window.dmChapters.selectTitle(first.dataset.title);
        window.dmChapters.deleteSelected();
        const payload=chapterPayload();
        const holder=document.createElement('div');
        holder.innerHTML=payload.map(c=>c.html.replace(/<!DOCTYPE[^>]*>/gi,'')).join('');
        return {count:payload.length,opening:holder.textContent.includes('Ночь на севере всегда была особенной.'),
                latest:holder.textContent.includes('Макс остановился у старой обсерватории')};
    })()""", chapter_structure_checked, 'audiobookChapterStructureView')


def chapter_structure_checked(result):
    ensure(result['count']==5 and result['opening'] and result['latest'], 'Deleting first chapter boundary preserves opening and live manuscript text')
    QMetaObject.invokeMethod(window.findChild(QObject, 'chapterMarkupWindow'), 'close')
    QTimer.singleShot(200, recording)


def recording():
    global reader, raw_reader, reader_component
    bridge.audiobook.flush()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_dir / 'components/TeleprompterWindow.qml')))
    if component.isError():
        raise AssertionError('\n'.join(e.toString() for e in component.errors()))
    reader_component = component
    raw_reader = component.createWithInitialProperties({'appBridge':bridge,'ownerWindow':window,'softBorder':'#dcdce0','softHeader':'#f2f2f4','softRow':'#f5f5f7','softAltRow':'#fafafa','softMuted':'#74747b'})
    ensure(raw_reader is not None, 'Existing teleprompter with audiobook tools instantiates')
    QQmlEngine.setObjectOwnership(raw_reader, QQmlEngine.ObjectOwnership.CppOwnership)
    reader=wrapInstance(getCppPointer(raw_reader)[0],QQuickWindow)
    reader.setColor('#f3f3f5')
    expr=QQmlExpression(engine.rootContext(),reader,'openFor("Глава 3")')
    expr.evaluate()
    if expr.hasError():
        raise AssertionError(expr.error().toString())
    bridge.teleprompter.jumpToIndex(1)
    QTimer.singleShot(1000, capture_recording)


def capture_recording():
    from PySide6.QtTest import QTest
    reader.raise_()
    reader.requestActivate()
    ensure(QTest.qWaitForWindowActive(reader, 1500), 'Teleprompter receives keyboard focus')
    QTest.keyClick(reader, Qt.Key.Key_F8)
    QTimer.singleShot(200, finish)


def finish():
    ensure(len(bridge.audiobook.retakes)==1, 'F8 creates a retake from the active teleprompter fragment')
    reader.grabWindow().save(str(output / (prefix + '-recording.png')))
    reader.close()
    ensure(bool(bridge.audiobook.recordingPosition('Глава 3')), 'Closing teleprompter stores reading position')
    reader.deleteLater()
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    print(json.dumps({'checks':len(checks),'failures':failures,'style':prefix},ensure_ascii=False),flush=True)
    app.exit(1 if failures else 0)


QTimer.singleShot(3500,capture)
QTimer.singleShot(25000,lambda: app.exit(4))
sys.exit(app.exec())
