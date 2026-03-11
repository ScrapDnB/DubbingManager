# Структура проекта Dubbing Manager

## Обзор архитектуры

Проект следует архитектуре **Service Layer + MVC** с разделением бизнес-логики, UI и контроллеров.

```
dubbing_manager/
├── main.py                      # Точка входа приложения (логирование с ротацией)
├── requirements.txt             # Зависимости Python
├── README.md                    # Документация пользователя
├── STRUCTURE.md                 # Этот файл
│
├── config/                      # Конфигурация и константы
│   ├── __init__.py
│   └── constants.py             # Константы UI и настройки по умолчанию
│
├── core/                        # Модели данных (dataclass с валидацией)
│   ├── __init__.py
│   ├── models.py                # Actor, DialogueLine, ExportConfig, PrompterConfig, ReplicaMergeConfig
│   └── commands.py              # Команды для Undo/Redo (Command pattern)
│
├── services/                    # Бизнес-логика (Service Layer)
│   ├── __init__.py
│   ├── project_service.py       # Управление проектами (атомарное сохранение, file lock)
│   ├── episode_service.py       # Управление эпизодами (парсинг ASS/SRT, кэш с timestamp)
│   ├── actor_service.py         # Управление актёрами (CRUD операции)
│   ├── export_service.py        # Экспорт (HTML, Excel, пакетный экспорт)
│   ├── global_settings_service.py # Глобальные настройки приложения
│   ├── docx_import_service.py   # Импорт DOCX с гибкой настройкой колонок
│   └── osc_worker.py            # OSC сервер для синхронизации с Reaper (QThread)
│
├── ui/                          # Пользовательский интерфейс
│   ├── __init__.py
│   ├── main_window.py           # Главное окно приложения
│   ├── teleprompter.py          # Окно телесуфлёра (OSC синхронизация)
│   ├── preview.py               # Предпросмотр HTML (Live Preview)
│   ├── video.py                 # Окно предпросмотра видео
│   │
│   ├── controllers/             # UI контроллеры (MVC)
│   │   ├── __init__.py
│   │   ├── actor_controller.py  # Контроллер панели актёров
│   │   ├── episode_controller.py # Контроллер управления эпизодами
│   │   ├── export_controller.py # Контроллер экспорта
│   │   └── project_controller.py # Контроллер проектов
│   │
│   └── dialogs/                 # Диалоговые окна
│       ├── __init__.py
│       ├── actor_filter.py      # Выбор актёров для подсветки
│       ├── colors.py            # Настройка цветовой схемы
│       ├── docx_import.py       # Импорт DOCX с настройкой колонок
│       ├── edit_text_dialog.py  # Редактирование текста реплики
│       ├── export.py            # Настройки экспорта
│       ├── reaper.py            # Настройки экспорта в Reaper
│       ├── replica_merge.py     # Настройки объединения реплик
│       ├── roles.py             # Редактирование ролей актёра
│       ├── search.py            # Глобальный поиск
│       └── summary.py           # Сводный отчёт проекта
│
├── utils/                       # Утилиты
│   ├── __init__.py
│   ├── helpers.py               # Вспомогательные функции (валидация путей)
│   └── web_bridge.py            # Мост между JS и Python (для WebEngine)
│
├── docs/                        # Документация
│   ├── DOCX_IMPORT.md           # Документация по импорту DOCX
│   └── DOCX_IMPORT_IMPLEMENTATION.md  # Техническая документация
│
├── tests/                       # Тесты (pytest, 65% покрытие)
│   ├── __init__.py
│   ├── README.md
│   ├── test_services.py         # Тесты сервисов
│   ├── test_additional.py       # Дополнительные тесты
│   ├── test_controllers.py      # Тесты контроллеров
│   ├── test_export_service.py   # Тесты экспорта
│   ├── test_global_settings_service.py # Тесты глобальных настроек
│   ├── test_web_bridge.py       # Тесты web_bridge
│   ├── test_actor_service.py    # Тесты actor_service
│   ├── test_models.py           # Тесты моделей
│   ├── test_osc_worker.py       # Тесты OSC worker
│   ├── test_main.py             # Тесты main.py
│   ├── test_helpers.py          # Тесты helpers
│   ├── test_helpers_additional.py # Дополнительные тесты helpers
│   ├── test_docx_import.py      # Тесты импорта DOCX
│   ├── test_docx_import_service.py # Тесты сервиса импорта DOCX
│   ├── test_docx_save.py        # Тесты сохранения DOCX
│   ├── test_commands.py         # Тесты команд Undo/Redo
│   ├── test_project_file_integrity.py # Тесты целостности файлов
│   ├── test_project_files_dialog.py # Тесты диалогов проектов
│   ├── test_project_folder_service.py # Тесты сервиса папок
│   ├── test_srt_import.py       # Тесты импорта SRT
│   └── test_undo_stack.py       # Тесты UndoStack
│
└── dist/                        # Скомпилированные приложения (git-ignored)
```

## Детальное описание модулей

### config/
| Файл | Описание |
|------|----------|
| `constants.py` | Константы приложения: цветовые палитры, настройки по умолчанию, размеры UI, отступы |

### core/
| Файл | Описание | Покрытие |
|------|----------|----------|
| `models.py` | Модели данных с `@dataclass` и валидацией `__post_init__` | 99% |
| `commands.py` | Команды для Undo/Redo (AddActorCommand, DeleteActorCommand, etc.) | 96% |

### services/
| Файл | Описание | Покрытие |
|------|----------|----------|
| `project_service.py` | Загрузка/сохранение проектов, автосохранение, ротация бэкапов, file lock | 70% |
| `episode_service.py` | Парсинг ASS/SRT, кэш с timestamp invalidation, сохранение | 83% |
| `actor_service.py` | CRUD операции с актёрами, назначение ролей, статистика | 100% |
| `export_service.py` | Экспорт в HTML, Excel, Reaper RPP, объединение реплик | 88% |
| `global_settings_service.py` | Глобальные настройки (экспорт, телесуфлёр, объединение) | 99% |
| `docx_import_service.py` | Импорт DOCX: таблицы, маппинг колонок, парсинг таймингов | 94% |
| `osc_worker.py` | OSC сервер для синхронизации с Reaper (QThread) | 75% |

### ui/controllers/
| Файл | Описание | Покрытие |
|------|----------|----------|
| `actor_controller.py` | Контроллер панели актёров: отображение, редактирование, назначение | 19%* |
| `episode_controller.py` | Контроллер эпизодов: импорт, сохранение, переименование | 86% |
| `export_controller.py` | Контроллер экспорта: HTML, Excel, Reaper, пакетный экспорт | 83% |
| `project_controller.py` | Контроллер проектов: сохранение, загрузка, автосохранение | 94% |

*\*Требуется pytest-qt для полного покрытия*

### ui/dialogs/
| Файл | Описание |
|------|----------|
| `actor_filter.py` | Диалог выбора актёров для фильтрации/подсветки |
| `colors.py` | Диалоги настройки цветовой схемы (PrompterColorDialog, CustomColorDialog) |
| `docx_import.py` | Диалог импорта DOCX: маппинг колонок, предпросмотр, несколько таблиц |
| `edit_text_dialog.py` | Диалог редактирования текста реплики |
| `export.py` | Диалог настроек экспорта (ExportSettingsDialog) |
| `reaper.py` | Диалог настроек экспорта в Reaper (ReaperExportDialog) |
| `replica_merge.py` | Диалог настроек объединения реплик (ReplicaMergeSettingsDialog) |
| `roles.py` | Диалог редактирования ролей актёра (ActorRolesDialog) |
| `search.py` | Диалог глобального поиска (GlobalSearchDialog) |
| `summary.py` | Диалог сводного отчёта (SummaryDialog) |
| `project_files.py` | Диалог просмотра структуры файлов проекта |

### utils/
| Файл | Описание | Покрытие |
|------|----------|----------|
| `helpers.py` | Вспомогательные функции: `ass_time_to_seconds()`, `format_seconds_to_tc()`, `get_video_fps()` (с валидацией путей) | 72% |
| `web_bridge.py` | Мост между JavaScript и Python для редактирования в WebEngine | 95% |

### tests/
| Файл | Описание | Покрытие |
|------|----------|----------|
| `test_services.py` | Тесты для сервисов (actor, episode, export) | 99% |
| `test_additional.py` | Дополнительные тесты | 99% |
| `test_controllers.py` | Тесты UI контроллеров (Episode, Export, Project) | 87% |
| `test_export_service.py` | Тесты сервиса экспорта | 96% |
| `test_global_settings_service.py` | Тесты глобальных настроек | 100% |
| `test_web_bridge.py` | Тесты web_bridge | 100% |
| `test_actor_service.py` | Тесты actor_service | 100% |
| `test_models.py` | Тесты моделей данных | 100% |
| `test_osc_worker.py` | Тесты OSC worker | 96% |
| `test_main.py` | Тесты main.py (логирование, пути) | 100% |
| `test_helpers.py` + `test_helpers_additional.py` | Тесты вспомогательных функций | 100% |
| `test_docx_import_service.py` | Тесты сервиса импорта DOCX | 99% |
| `test_commands.py` | Тесты команд Undo/Redo | 99% |
| `test_undo_stack.py` | Тесты UndoStack | 100% |

## Архитектурные принципы

### 1. Service Layer + MVC
Бизнес-логика вынесена в сервисы, UI-логика в контроллеры:
```
MainWindow → Controllers → Services → Data
```

### 2. Command Pattern (Undo/Redo)
Все основные операции поддерживают отмену/повтор:
```python
command = AddActorCommand(actors, actor_id, name, color)
undo_stack.push(command)  # Выполняет и сохраняет
undo_stack.undo()         # Отменяет
undo_stack.redo()         # Повторяет
```

### 3. Type Hints
Все файлы используют аннотации типов (PEP 484):
```python
def refresh_actor_list(self) -> None:
    if self.actor_controller:
        self.actor_controller.refresh()
```

### 4. Логирование с ротацией
Используется `RotatingFileHandler` (10MB, 5 файлов):
```python
from logging.handlers import RotatingFileHandler

file_handler = RotatingFileHandler(
    log_path,
    maxBytes=10*1024*1024,
    backupCount=5
)
```

### 5. Валидация данных
Модели используют `__post_init__` для валидации:
```python
@dataclass
class PrompterConfig:
    f_tc: int = 20
    
    def __post_init__(self):
        if not 10 <= self.f_tc <= 150:
            raise ValueError(f"f_tc must be 10-150, got {self.f_tc}")
```

### 6. Безопасность
- Валидация путей (защита от path traversal)
- File lock для предотвращения race conditions
- Атомарное сохранение через временный файл

## Зависимости

| Пакет | Версия | Назначение |
|-------|--------|------------|
| `pyside6` | 6.10.2 | GUI фреймворк |
| `pyside6-addons` | 6.10.2 | Дополнительные компоненты Qt |
| `python-osc` | 1.9.3 | OSC протокол для Reaper |
| `openpyxl` | >=3.0.0 | Excel экспорт |
| `python-docx` | >=1.0.0 | Импорт DOCX файлов |
| `requests` | 2.32.5 | HTTP запросы |
| `pytest` | >=7.0.0 | Тестирование |
| `pytest-cov` | >=4.0.0 | Покрытие кода |

## Запуск тестов

```bash
# Все тесты
python -m pytest tests/ -v

# С покрытием
python -m pytest tests/ --cov=. --cov-report=html

# Конкретный модуль
python -m pytest tests/test_controllers.py -v

# Только быстрые тесты (без integration)
python -m pytest tests/ -v -m "not slow"
```

## Покрытие кода

| Категория | Покрытие | Статус |
|-----------|----------|--------|
| **Общее** | 65% | ✅ Отлично |
| **Бизнес-логика** | 80-100% | ✅ Отлично |
| **Контроллеры** | 83-94% | ✅ Отлично |
| **Модели** | 99% | ✅ Отлично |
| **UI диалоги** | 6-73% | ⚠️ Требуют pytest-qt |
| **UI окна** | 9-16% | ⚠️ Требуют интеграционных тестов |

## Примечания

### Улучшения (Code Review 2024)

1. **Безопасность:**
   - ✅ RotatingFileHandler для логов
   - ✅ Валидация путей (path traversal protection)
   - ✅ File lock для concurrent access

2. **Производительность:**
   - ✅ Оптимизация ActorController.refresh()
   - ✅ Кэш эпизодов с timestamp invalidation
   - ✅ Memory leak fix в UndoStack

3. **Код-стиль:**
   - ✅ Удалён закомментированный код
   - ✅ Magic numbers вынесены в constants
   - ✅ Рефакторинг main_window.py → контроллеры

4. **Тесты:**
   - ✅ +251 тест (245 → 496)
   - ✅ +8 тест-файлов
   - ✅ Покрытие 50% → 65%

### Ключевые компоненты

- **ActorController** — контроллер панели актёров (оптимизирован)
- **EpisodeController** — контроллер эпизодов (новый)
- **ExportController** — контроллер экспорта (новый)
- **ProjectController** — контроллер проектов (новый)
- **DocxImportService** — сервис импорта DOCX
- **GlobalSettingsService** — глобальные настройки (~/.dubbing_manager/)
- **UndoStack** — система отмены/повтора действий (Command pattern)

## Новые возможности

### DOCX импорт
- **Импорт DOCX** — кнопка "+ .DOCX" в панели управления сериями
- **Гибкий маппинг** — настройка соответствия колонок
- **Автоопределение** — распознавание колонок по заголовкам
- **Тайминг в одной колонке** — формат `00:00:01,000 - 00:00:03,000`
- **Настраиваемые разделители** — `-`, `–`, `—`, `|`, `/`
- **Предпросмотр** — визуальная проверка перед импортом
- **Несколько таблиц** — поддержка документов с несколькими таблицами

### Undo/Redo
- **Ctrl+Z** — отмена действия
- **Ctrl+Shift+Z** — повтор действия
- Поддерживает: добавление/удаление актёров, переименование, назначение ролей, операции с эпизодами

### Глобальные настройки
- Настройки экспорта сохраняются между проектами
- Настройки телесуфлёра сохраняются между проектами
- Настройки объединения реплик сохраняются между проектами
- Файл: `~/.dubbing_manager/global_settings.json` (macOS/Linux) или `%APPDATA%/dubbing_manager/global_settings.json` (Windows)
