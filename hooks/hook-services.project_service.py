# -*- mode: python ; coding: utf-8 -*-

"""PyInstaller hook for project service dependencies."""

# macOS-specific handling
hiddenimports = []

try:
    import fcntl
    hiddenimports.append('fcntl')
except ImportError:
    pass

try:
    import termios
    hiddenimports.append('termios')
except ImportError:
    pass
