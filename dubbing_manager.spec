# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file для Dubbing Manager
Сборка: pyinstaller dubbing_manager.spec
"""

import os
import sys
from config.constants import APP_VERSION

block_cipher = None
is_macos = sys.platform == 'darwin'
is_windows = sys.platform.startswith('win')
is_onedir = is_macos or is_windows

app_name = 'Dubbing Manager'
app_version = APP_VERSION
mac_icon = 'resources/icons/DubbingManager.icns'
win_icon = 'resources/icons/DubbingManager.ico'

mac_info_plist = {
    'CFBundleName': app_name,
    'CFBundleDisplayName': app_name,
    'CFBundleIdentifier': 'com.yuriromanov.dubbingmanager',
    'CFBundleVersion': app_version,
    'CFBundleShortVersionString': app_version,
    'NSHumanReadableCopyright': 'Copyright © 2026 Yuri Romanov. All rights reserved.',
    'NSHighResolutionCapable': True,
    'LSMinimumSystemVersion': '10.15',
    'NSPrincipalClass': 'NSApplication',
    'CFBundlePackageType': 'APPL',
    'CFBundleSignature': '????',
    'CFBundleExecutable': app_name,
    'CFBundleInfoDictionaryVersion': '6.0',
    'CFBundleSupportedPlatforms': ['MacOSX'],
    'NSMainNibFile': '',
    'CFBundleIconFile': 'DubbingManager.icns',
}

hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
    'PySide6.QtSvg',
    'PySide6.QtWebChannel',
    'PySide6.QtWebEngineWidgets',
]

# Add the remaining project dependencies.
hidden_imports += [
    'services', 'ui', 'utils', 'config',
    'certifi', 'charset_normalizer', 'idna', 'requests', 'urllib3',
    'openpyxl', 'docx', 'pythonosc', 'lxml',
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
    [] if is_onedir else a.binaries,
    [] if is_onedir else a.zipfiles,
    [] if is_onedir else a.datas,
    name=app_name,
    debug=False,
    exclude_binaries=is_onedir,
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
    icon=win_icon if is_windows else mac_icon,
    plist=mac_info_plist if is_macos else None,
)

if is_onedir:
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=app_name,
    )

if is_macos:
    # Create a macOS .app bundle.
    app = BUNDLE(
        coll,
        name=f'{app_name}.app',
        icon=mac_icon,
        bundle_identifier='com.yuriromanov.dubbingmanager',
        version=app_version,
        info_plist=mac_info_plist,
    )
