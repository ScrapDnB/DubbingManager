# Исправление ошибки логирования на Windows

## Проблема

При запуске собранного приложения на Windows возникала ошибка:

```
Traceback (most recent call last):
  File "main.py", line 14, in <module>
  File "logging\__init__.py", line 1219, in __init__
  File "logging\__init__.py", line 1248, in _open
```

### Причина

`FileHandler` пытался создать файл лога (`dubbing_manager.log`) в текущей рабочей директории, которая может быть:
- `C:\Program Files\DubbingManager\` — нет прав на запись
- Другая защищённая директория — нет прав на запись

## Решение

### 1. Использование AppData для логов

Теперь файл лога создаётся в директории данных приложения Windows:

```
C:\Users\<User>\AppData\Local\DubbingTools\Dubbing Manager\dubbing_manager.log
```

Это стандартное расположение для данных приложения на Windows.

### 2. RotatingFileHandler

Вместо обычного `FileHandler` используется `RotatingFileHandler`:
- Максимальный размер файла: 5 MB
- Количество резервных копий: 3
- Автоматическая ротация при достижении лимита

### 3. Защита от ошибок

Если не удалось создать файл лога:
- Приложение продолжает работать
- Логи пишутся только в консоль
- Выводится предупреждение

### 4. Дополнительная информация в логе

Теперь при запуске логируется:
- Версия Python
- Платформа
- Рабочая директория

## Изменения в main.py

### Было:

```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dubbing_manager.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
```

### Стало:

```python
def get_log_file_path() -> str:
    """Получение пути к файлу лога через QStandardPaths"""
    app_data = QStandardPaths.writableLocation(
        QStandardPaths.AppDataLocation
    )
    if app_data:
        os.makedirs(app_data, exist_ok=True)
        return os.path.join(app_data, "dubbing_manager.log")
    return "dubbing_manager.log"

def setup_logging() -> logging.Logger:
    """Настройка с RotatingFileHandler и обработкой ошибок"""
    # ... код ...
```

## Преимущества

1. **Работа на Windows** — нет проблем с правами доступа
2. **Автоматическая ротация** — логи не занимают много места
3. **Защита от ошибок** — приложение работает даже если лог не создан
4. **Кроссплатформенность** — работает на Windows, macOS, Linux

## Расположение файлов лога

### Windows:
```
C:\Users\<User>\AppData\Local\DubbingTools\Dubbing Manager\dubbing_manager.log
```

### macOS:
```
/Users/<User>/Library/Application Support/DubbingTools/Dubbing Manager/dubbing_manager.log
```

### Linux:
```
/home/<User>/.local/share/DubbingTools/Dubbing Manager/dubbing_manager.log
```

## Проверка после сборки

После сборки на Windows проверьте:

1. Приложение запускается без ошибок
2. Файл лога создаётся в AppData
3. При повторном запуске логи добавляются
4. При достижении 5 MB создаётся `.1`, `.2`, `.3` файлы

## Сборка на Windows

```bash
# Виртуальное окружение
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Сборка
pyinstaller --name="Dubbing Manager" ^
    --windowed ^
    --onefile ^
    --icon=icon.ico ^
    --add-data "config;config" ^
    --add-data "core;core" ^
    --add-data "services;services" ^
    --add-data "ui;ui" ^
    --hidden-import=PySide6.QtCore ^
    main.py

# Проверка
dist\"Dubbing Manager".exe
```

## Тестирование

Запустите приложение из разных директорий:

```cmd
# Из директории установки
cd "C:\Program Files\DubbingManager"
"Dubbing Manager.exe"

# Из рабочей папки
cd %USERPROFILE%\Documents
"Dubbing Manager.exe"

# С правами администратора (должно работать без ошибок)
Run as Administrator
```

Во всех случаях приложение должно запускаться без ошибок логирования.
