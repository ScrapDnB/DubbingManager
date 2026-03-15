# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file для Dubbing Manager
Сборка: pyinstaller dubbing_manager.spec
"""

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Собираем все подмодули PySide6
pyside6_modules = collect_submodules('PySide6')

# Исключаем ТОЛЬКО действительно ненужные тяжёлые модули
# Важно: QtMultimedia, QtMultimediaWidgets, QtWebChannel, QtWebEngineWidgets — используются!
excluded_pyside6 = [
    # 3D — не используется
    'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput',
    'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
    # Остальное ненужное
    'PySide6.QtAxContainer',
    'PySide6.QtBluetooth',
    'PySide6.QtCharts',
    'PySide6.QtConcurrent',
    'PySide6.QtDataVisualization',
    'PySide6.QtDBus',
    'PySide6.QtDesigner',
    'PySide6.QtGamepad',
    'PySide6.QtHelp',
    'PySide6.QtLocation',
    'PySide6.QtMacExtras',
    'PySide6.QtNetworkAuth',
    'PySide6.QtNfc',
    'PySide6.QtPdf',
    'PySide6.QtPdfWidgets',
    'PySide6.QtPositioning',
    'PySide6.QtPrintSupport',
    'PySide6.QtQml',
    'PySide6.QtQuick',
    'PySide6.QtQuick3D',
    'PySide6.QtQuickControls2',
    'PySide6.QtQuickWidgets',
    'PySide6.QtRemoteObjects',
    'PySide6.QtScxml',
    'PySide6.QtSensors',
    'PySide6.QtSerialPort',
    'PySide6.QtSql',
    'PySide6.QtStateMachine',
    'PySide6.QtSvgWidgets',
    'PySide6.QtTest',
    'PySide6.QtTextToSpeech',
    'PySide6.QtUiTools',
    'PySide6.QtWebSockets',
    'PySide6.QtXml',
    'PySide6.QtXmlPatterns',
]

# Фильтруем — оставляем только то, что НЕ в исключениях
hidden_imports = [
    mod for mod in pyside6_modules 
    if not any(mod.startswith(excl) for excl in excluded_pyside6)
]

# Добавляем явные импорты для надёжности
hidden_imports += [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
    'PySide6.QtSvg',
    'PySide6.QtWebChannel',
    'PySide6.QtWebEngineWidgets',
]

# Добавляем остальные зависимости проекта
hidden_imports += [
    'services', 'ui', 'utils', 'config',
    'certifi', 'charset_normalizer', 'idna', 'requests', 'urllib3',
    'openpyxl', 'docx', 'python_osc', 'lxml', 'etree',
    'services.episode_service', 'services.actor_service',
    'services.export_service', 'services.project_service',
    'services.docx_import_service', 'services.osc_worker',
    'ui.main_window', 'ui.preview', 'ui.video', 'ui.teleprompter',
    'ui.controllers', 'ui.dialogs',
    'utils.helpers', 'utils.web_bridge',
    'config.constants',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
    ],
    hiddenimports=hidden_imports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'doctest', 'pdb',
        'distutils', 'setuptools', 'pip', 'pytest',
        'numpy', 'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Dubbing Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # plist для macOS
    plist={
        'CFBundleName': 'Dubbing Manager',
        'CFBundleDisplayName': 'Dubbing Manager',
        'CFBundleIdentifier': 'com.yuriromanov.dubbingmanager',
        'CFBundleVersion': '1.2.0',
        'CFBundleShortVersionString': '1.2.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 Yuri Romanov. All rights reserved.',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
        'NSPrincipalClass': 'NSApplication',
        'NSMainNibFile': '',
        'CFBundleIconFile': '',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'CFBundleExecutable': 'Dubbing Manager',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundleSupportedPlatforms': ['MacOSX'],
    }
)

# Для macOS создаём .app bundle
app = BUNDLE(
    exe,
    name='Dubbing Manager.app',
    icon=None,
    bundle_identifier='com.yuriromanov.dubbingmanager',
    plist={
        'CFBundleName': 'Dubbing Manager',
        'CFBundleDisplayName': 'Dubbing Manager',
        'CFBundleIdentifier': 'com.yuriromanov.dubbingmanager',
        'CFBundleVersion': '1.2.0',
        'CFBundleShortVersionString': '1.2.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 Yuri Romanov. All rights reserved.',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
        'NSPrincipalClass': 'NSApplication',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'CFBundleExecutable': 'Dubbing Manager',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundleSupportedPlatforms': ['MacOSX'],
        'NSMainNibFile': '',
        'CFBundleIconFile': '',
    },
)
