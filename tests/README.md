# Тесты для Dubbing Manager

## Запуск тестов

### Базовый запуск
```bash
# Активировать виртуальное окружение
source .venv/bin/activate  # macOS/Linux
# или
.venv\Scripts\activate     # Windows

# Запустить все тесты
pytest tests/ -v
```

### Запуск с покрытием кода
```bash
# Запуск с отчётом о покрытии
pytest tests/ -v --cov=services --cov-report=term-missing

# Запуск с HTML отчётом
pytest tests/ -v --cov=services --cov-report=html

# Открыть HTML отчёт
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov\index.html  # Windows
```

### Запуск отдельных тестов
```bash
# Конкретный файл
pytest tests/test_services.py -v

# Конкретный класс тестов
pytest tests/test_services.py::TestProjectService -v

# Конкретный тест
pytest tests/test_services.py::TestProjectService::test_create_new_project -v

# Тесты по маркеру
pytest tests/ -v -m "not slow"
pytest tests/ -v -m integration
```

## Импорт DOCX и таблиц

`test_spreadsheet_import.py` проверяет настоящие XLS/XLSX/CSV, кодировки,
тайминг, разные схемы листов, скрытые и пустые листы, один Undo на пакет,
сохранение без исходника и восстановление выбранного листа. XLS-образец
`fixtures/spreadsheet_import.xls` — синтетическая BIFF8-книга; дополнительных
библиотек создания XLS для тестов не требуется.

```bash
.venv/bin/python tests/gui/script_import_smoke.py
.venv/bin/python tests/gui/script_import_smoke.py --dark
.venv/bin/python tests/gui/script_import_smoke.py --fluent
```

Проверка окон не изменяет пользовательские проекты и настройки. Снимки и
результаты сохраняются в `output/import-smoke/`. Fluent на macOS проверяет
компоновку; проверка на настоящей Windows выполняется отдельно.

## Структура тестов

### Живая проверка главного окна

```bash
.venv/bin/python tests/gui/main_workspace_smoke.py
.venv/bin/python tests/gui/main_workspace_smoke.py --dark
QT_QUICK_CONTROLS_STYLE=FluentWinUI3 .venv/bin/python tests/gui/main_workspace_smoke.py --fluent
QT_QUICK_CONTROLS_STYLE=FluentWinUI3 .venv/bin/python tests/gui/main_workspace_smoke.py --fluent --dark
```

Проверка использует временный проект и настройки, проверяет выбор стартового
раздела, сохранение и отмену настроек, переключение тем без перезапуска и
возврат к системной палитре, таймлайн на всю ширину в Кастинге,
доступность кнопки «Аудиокнига» для нового проекта и открытой аудиокниги,
её блокировку для сериала,
границы и выравнивание панелей серий, центрирование пустого окна аудиокниги,
редактирование, undo/redo, защиту неверного черновика, реальные клики по шкале
и сегментам с выбором реплики и перемоткой видео, а также узкую компоновку.
На macOS проверяется нативный переключатель AppKit. Снимки и отчёты находятся
в `output/main-window-selected-elements`. Fluent на macOS проверяет
компоновку и не заменяет проверку системных эффектов на настоящей Windows.

### Живая проверка модуля аудиокниг

В графической сессии macOS или Windows:

```bash
python tests/gui/audiobook_workspace_smoke.py
```

Сценарий создаёт изолированный демонстрационный проект и настройки, проверяет
WebEngine/WebChannel, разметку части абзаца и нескольких абзацев, отмену/повтор,
сохранность вступления при удалении границы главы, суфлёр, F8 и сохранение позиции. Снимки окна сохраняются в
`output/audiobook-implementation`.

Для проверки Windows-компоновки на macOS:

```bash
QT_QUICK_CONTROLS_STYLE=FluentWinUI3 python tests/gui/audiobook_workspace_smoke.py --fluent
```

Этот режим подменяет платформенные условия только во временной копии QML.
Он не заменяет запуск на настоящей Windows 11.

Проверка синхронизации с DAW:

```bash
python -m pytest tests/test_midi_sync.py tests/test_qml_bridge.py
python tests/gui/daw_sync_smoke.py
python tests/gui/daw_sync_smoke.py --fluent
```

MIDI-тесты проверяют MTC Full Frame/Quarter Frame, компенсацию задержки,
drop-frame и дробные частоты кадров, MMC Locate, выбранные порты Windows,
потерю порта, освобождение ресурсов, сохранение настроек и переключение DAW.
GUI-сценарий на macOS дополнительно проверяет настоящую петлю CoreMIDI между
двумя тестовыми клиентами и телесуфлёром. `--fluent` проверяет компоновку Windows
с примером портов loopMIDI; это не проверка реальной Windows или Nuendo.
Проект и настройки изолированы, снимки сохраняются в `output/daw-sync`.
Для проверки MTC-переходов в Stop и MMC-навигации внутри DAW нужен запуск
с установленной Nuendo на каждой целевой системе.

```
tests/
├── __init__.py
└── test_services.py          # Тесты сервисов
    ├── TestProjectService    # Тесты ProjectService
    ├── TestEpisodeService    # Тесты EpisodeService
    ├── TestActorService      # Тесты ActorService
    ├── TestExportService     # Тесты ExportService
    └── TestIntegration       # Интеграционные тесты
```

## Покрытие тестами

| Сервис | Строк | Покрытие |
|--------|-------|----------|
| `project_service.py` | 188 | 70% |
| `episode_service.py` | 107 | 85% |
| `actor_service.py` | 76 | 80% |
| `export_service.py` | 181 | 82% |
| `osc_worker.py` | 72 | 0% ⚠️ |
| **Итого** | **629** | **69%** |

### Тесты:

| Файл | Тестов | Описание |
|------|--------|----------|
| `test_services.py` | 35 | Основные тесты сервисов |
| `test_additional.py` | 18 | Дополнительные тесты (edge cases) |

### Не покрыто:
- `osc_worker.py` — требует мокирования OSC сервера
- Обработка исключений в некоторых методах

## Зависимости для тестирования

```bash
# Установить зависимости для тестирования
pip install pytest pytest-cov

# Или из requirements.txt
pip install -r requirements.txt
```

## Написание новых тестов

### Шаблон теста
```python
import pytest
from services import YourService

class TestYourService:
    """Тесты для YourService"""
    
    def test_something(self, sample_project_data):
        """Описание теста"""
        service = YourService()
        result = service.do_something()
        
        assert result is not None
        assert result["key"] == "expected_value"
```

### Полезные fixtures
- `sample_project_data` — пример данных проекта
- `sample_lines` — пример реплик
- `temp_json_file` — временный JSON файл
- `temp_ass_file` — временный ASS файл

### Маркеры
```python
@pytest.mark.slow  # Медленный тест
@pytest.mark.integration  # Интеграционный тест
```

## Непрерывная интеграция (CI)

### GitHub Actions пример
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v --cov=services
```

## Статистика

- **Всего тестов:** 28
- **Успешных:** 28 (100%)
- **Время выполнения:** ~0.4s

### Телесуфлёр и монтажный лист

```bash
.venv/bin/python tests/gui/tools_windows_smoke.py --all
```

Проверка использует временные проекты и настройки. Она последовательно запускает
macOS и Fluent в светлой и тёмной темах, сохраняет снимки обычных и минимальных
окон в `output/tools-window-redesign/` и проверяет навигацию, поиск, переключение
режимов, зеркальное чтение, редактор, плавающий контроллер, правку через
WebChannel с Undo и пакетный экспорт HTML/XLSX/DOCX/PDF. При экспорте всех серий
XLSX содержит общий файл, остальные форматы — отдельные файлы серий.

`--fluent` на macOS проверяет компоновку и стиль Qt, а не системное оформление
или работу DWM на Windows. Для отдельных вариантов доступны `--fluent` и
`--dark`; без аргументов запускается светлый вариант macOS.
