"""Behavioral regressions for montage preview focus and Reaper isolation."""

import re

import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtQml import QJSEngine

from services.export_service import ExportService
from ui.qml_backend.app_bridge import AppBridge
from ui.qml_backend.features.ui_state_bridge import UiStateBridge


@pytest.fixture
def app():
    return QCoreApplication.instance() or QCoreApplication([])


def test_preview_blur_only_submits_user_edits(app):
    engine = QJSEngine()
    source = ExportService({})._get_editable_js()
    script = re.search(r"<script>(.*?)</script>", source, re.S).group(1)
    result = engine.evaluate('''
        var sent = [];
        var qt = {webChannelTransport: {}};
        function QWebChannel(transport, ready) {
            ready({objects: {backend: {
                update_text: function(id, text) { sent.push([id, text]); }
            }}});
        }
    ''' + script + '''
        var el = {id: 'line-1', innerText: 'Normalized whitespace', dataset: {}};
        onBlur(el);
        var untouchedCount = sent.length;
        el.dataset.edited = 'true';
        el.innerText = 'Edited\\r\\ntext';
        onBlur(el);
        onBlur(el);
        [untouchedCount, sent];
    ''')
    assert not result.isError(), result.toString()
    assert result.toVariant() == [0, [['line-1', 'Edited\ntext']]]
    html = ExportService({})._format_text_html({
        'parts': [{'id': 'line-1', 'text': 'Original', 'sep': ''}],
    }, True)
    assert 'oninput=\'this.dataset.edited = "true"\'' in html


def test_reaper_transport_and_time_do_not_refresh_montage(app, monkeypatch, tmp_path):
    monkeypatch.setattr(
        'services.global_settings_service.SETTINGS_FILE',
        tmp_path / 'global_settings.json',
    )
    monkeypatch.setattr(
        'ui.qml_backend.app_bridge.UiStateBridge',
        lambda parent=None: UiStateBridge(
            QSettings(str(tmp_path / 'ui.ini'), QSettings.IniFormat), parent=parent
        ),
    )
    bridge = AppBridge()
    bridge._session.data['episodes'] = {'1': str(tmp_path / 'one.ass')}
    bridge._session.data['episode_working_texts'] = {
        '1': {'lines': [{
            'id': 'line-1', 'start': 1.0, 'end': 2.0,
            'character': 'Hero', 'text': 'Original',
        }]},
    }
    bridge.montage.prepare('1')
    original_html = bridge.montage.html
    changes = []
    bridge.montage.changed.connect(lambda: changes.append(True))
    bridge.teleprompter._on_osc_time(0.0)
    bridge.teleprompter._on_osc_transport(True)
    bridge.teleprompter._on_osc_time(10.0)
    bridge.teleprompter._on_osc_transport(False)
    assert changes == []
    assert bridge.montage.html == original_html
