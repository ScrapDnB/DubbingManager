# -*- mode: python ; coding: utf-8 -*-

"""PyInstaller hook for project service dependencies."""

# macOS-specific handling
# Internal implementation detail
hiddenimports = []

# Internal implementation detail
try:
    import fcntl
    hiddenimports.append('fcntl')
except ImportError:
    pass

# Internal implementation detail
try:
    import termios
    hiddenimports.append('termios')
except ImportError:
    pass
