# Структура проекта Dubbing Manager

## Обзор архитектуры

Проект следует архитектуре **Service Layer** с разделением бизнес-логики и UI.

```
dubbing_manager/
├── main.py                      # Точка входа приложения
├── requirements.txt             # Зависимости Python
├── README.md                    # Документация пользователя
├── STRUCTURE.md                 # Этот файл
│
├── config/                      # Конфигурация и константы
│   ├── __init__.py
│   └── constants.py             # Константы UI и настройки по умолчанию
│
├── core/                        # Модели данных
│   ├── __init__.py
│   └── models.py                # Dataclass: Actor, DialogueLine, ExportConfig, PrompterConfig
│
├── services/                    # Бизнес-логика (Service Layer)
│   ├── __init__.py
│   ├── project_service.py       # Управление проектами (загрузка/сохранение)
│   ├── episode_service.py       # Управление эпизодами (парсинг ASS)
│   ├── actor_service.py         # Управление актёрами (CRUD операции)
│   ├── export_service.py        # Экспорт (HTML, Excel, пакетный экспорт)
│   ├── osc_worker.py            # OSC сервер для синхронизации с Reaper
│   └── hotkey_manager.py        # (удалён) Глобальные горячие клавиши
│
├── ui/                          # Пользовательский интерфейс
│   ├── __init__.py
│   ├── main_window.py           # Главное окно приложения
│   ├── teleprompter.py          # Окно телесуфлёра
│   ├── preview.py               # Предпросмотр HTML (Live Preview)
│   ├── video.py                 # Окно предпросмотра видео
│   │
│   ├── controllers/             # UI контроллеры
│   │   ├── __init__.py
│   │   └── actor_controller.py  # Контроллер панели актёров
│   │
│   └── dialogs/                 # Диалоговые окна
│       ├── __init__.py
│       ├── actor_filter.py      # Выбор актёров для подсветки
│       ├── colors.py            # Настройка цветовой схемы
│       ├── export.py            # Настройки экспорта
│       ├── reaper.py            # Настройки экспорта в Reaper
│       ├── roles.py             # Редактирование ролей актёра
│       ├── search.py            # Глобальный поиск
│       └── summary.py           # Сводный отчёт проекта
│
├── utils/                       # Утилиты
│   ├── __init__.py
│   ├── helpers.py               # Вспомогательные функции
│   └── web_bridge.py            # Мост между JS и Python (для WebEngine)
│
└── dist/                        # Скомпилированные приложения (git-ignored)
```

## Детальное описание модулей

### config/
| Файл | Описание |
|------|----------|
| `constants.py` | Константы приложения: цветовые палитры, настройки по умолчанию, размеры UI |

### core/
| Файл | Описание |
|------|----------|
| `models.py` | Модели данных с использованием `@dataclass`: `Actor`, `DialogueLine`, `ExportConfig`, `PrompterConfig`, `PrompterColors` |

### services/
| Файл | Описание | Строк |
|------|----------|-------|
| `project_service.py` | Загрузка/сохранение проектов, автосохранение | ~150 |
| `episode_service.py` | Парсинг ASS файлов, загрузка эпизодов, сохранение | ~230 |
| `actor_service.py` | CRUD операции с актёрами, назначение ролей | ~290 |
| `export_service.py` | Экспорт в HTML, Excel, пакетный экспорт | ~600 |
| `osc_worker.py` | OSC сервер для синхронизации с Reaper (поток) | ~100 |

### ui/controllers/
| Файл | Описание | Строк |
|------|----------|-------|
| `actor_controller.py` | Контроллер панели актёров: отображение, редактирование, назначение | ~190 |

### ui/dialogs/
| Файл | Описание |
|------|----------|
| `actor_filter.py` | Диалог выбора актёров для фильтрации/подсветки |
| `colors.py` | Диалоги настройки цветовой схемы (PrompterColorDialog, CustomColorDialog) |
| `export.py` | Диалог настроек экспорта (ExportSettingsDialog) |
| `reaper.py` | Диалог настроек экспорта в Reaper (ReaperExportDialog) |
| `roles.py` | Диалог редактирования ролей актёра (ActorRolesDialog) |
| `search.py` | Диалог глобального поиска (GlobalSearchDialog) |
| `summary.py` | Диалог сводного отчёта (SummaryDialog) |

### utils/
| Файл | Описание |
|------|----------|
| `helpers.py` | Вспомогательные функции: `ass_time_to_seconds()`, `format_seconds_to_tc()`, `hex_to_rgba_string()`, `customize_table()`, `wrap_widget()`, `log_exception()` |
| `web_bridge.py` | Мост между JavaScript и Python для редактирования в WebEngine |

## Архитектурные принципы

### 1. Service Layer
Бизнес-логика вынесена в сервисы:
```
UI (MainWindow) → Services → Data
```

### 2. Controllers
UI-логика вынесена в контроллеры:
```
MainWindow → ActorController → ActorService
```

### 3. Type Hints
Все файлы используют аннотации типов (PEP 484):
```python
def refresh_actor_list(self) -> None:
    if self.actor_controller:
        self.actor_controller.refresh()
```

### 4. Логирование
Используется стандартный модуль `logging`:
```python
logger.info(f"Project loaded from {path}")
log_exception(logger, "Load failed", e)
```

## Статистика кода

| Компонент | Файлов | Строк |
|-----------|--------|-------|
| **Services** | 5 | ~1,400 |
| **UI** | 4 | ~3,200 |
| **Controllers** | 1 | ~190 |
| **Dialogs** | 7 | ~800 |
| **Utils** | 2 | ~150 |
| **Config** | 1 | ~170 |
| **Core** | 1 | ~150 |
| **Итого** | **21** | **~6,060** |

## Зависимости

| Пакет | Версия | Назначение |
|-------|--------|------------|
| `pyside6` | 6.10.2 | GUI фреймворк |
| `pyside6-addons` | 6.10.2 | Дополнительные компоненты Qt |
| `python-osc` | 1.9.3 | OSC протокол |
| `openpyxl` | (опционально) | Excel экспорт |
| `requests` | 2.32.5 | HTTP запросы |

## Примечания

- **Горячие клавиши удалены** — модуль `hotkey_manager.py` удалён (не работал на macOS)
- **ActorController** — новый контроллер для управления панелью актёров (добавлен в 2026)
- **ExportService** — расширен для поддержки пакетного экспорта (2026)
