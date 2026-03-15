# -*- mode: python ; coding: utf-8 -*-

"""
Hook для services.project_service
Обрабатывает условный импорт fcntl для разных платформ
"""

# fcntl и termios доступны на Unix (macOS, Linux)
# Добавляем их в скрытые импорты для PyInstaller
hiddenimports = []

# Пробуем добавить fcntl если доступен
try:
    import fcntl
    hiddenimports.append('fcntl')
except ImportError:
    pass

# Пробуем добавить termios если доступен
try:
    import termios
    hiddenimports.append('termios')
except ImportError:
    pass
