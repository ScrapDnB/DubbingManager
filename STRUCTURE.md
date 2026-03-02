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
│   └── models.py                # Dataclass: Actor, DialogueLine, ExportConfig, PrompterConfig, ReplicaMergeConfig
│
├── services/                    # Бизнес-логика (Service Layer)
│   ├── __init__.py
│   ├── project_service.py       # Управление проектами (загрузка/сохранение)
│   ├── episode_service.py       # Управление эпизодами (парсинг ASS)
│   ├── actor_service.py         # Управление актёрами (CRUD операции)
│   ├── export_service.py        # Экспорт (HTML, Excel, пакетный экспорт)
│   ├── global_settings_service.py # Глобальные настройки приложения
│   └── osc_worker.py            # OSC сервер для синхронизации с Reaper
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
│   ├── helpers.py               # Вспомогательные функции
│   └── web_bridge.py            # Мост между JS и Python (для WebEngine)
│
├── tests/                       # Тесты
│   ├── __init__.py
│   ├── README.md
│   ├── test_services.py         # Тесты сервисов
│   └── test_additional.py       # Дополнительные тесты
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
| Файл | Описание |
|------|----------|
| `project_service.py` | Загрузка/сохранение проектов, автосохранение, ротация бэкапов |
| `episode_service.py` | Парсинг ASS файлов, загрузка эпизодов, сохранение, подсчёт колец |
| `actor_service.py` | CRUD операции с актёрами, назначение ролей |
| `export_service.py` | Экспорт в HTML, Excel, пакетный экспорт, объединение реплик |
| `global_settings_service.py` | Глобальные настройки приложения (экспорт, телесуфлёр, объединение) |
| `osc_worker.py` | OSC сервер для синхронизации с Reaper (поток) |

### ui/controllers/
| Файл | Описание |
|------|----------|
| `actor_controller.py` | Контроллер панели актёров: отображение, редактирование, назначение |

### ui/dialogs/
| Файл | Описание |
|------|----------|
| `actor_filter.py` | Диалог выбора актёров для фильтрации/подсветки |
| `colors.py` | Диалоги настройки цветовой схемы (PrompterColorDialog, CustomColorDialog) |
| `edit_text_dialog.py` | Диалог редактирования текста реплики |
| `export.py` | Диалог настроек экспорта (ExportSettingsDialog) |
| `reaper.py` | Диалог настроек экспорта в Reaper (ReaperExportDialog) |
| `replica_merge.py` | Диалог настроек объединения реплик (ReplicaMergeSettingsDialog) |
| `roles.py` | Диалог редактирования ролей актёра (ActorRolesDialog) |
| `search.py` | Диалог глобального поиска (GlobalSearchDialog) |
| `summary.py` | Диалог сводного отчёта (SummaryDialog) |

### utils/
| Файл | Описание |
|------|----------|
| `helpers.py` | Вспомогательные функции: `ass_time_to_seconds()`, `format_seconds_to_tc()`, `hex_to_rgba_string()`, `customize_table()`, `wrap_widget()`, `log_exception()` |
| `web_bridge.py` | Мост между JavaScript и Python для редактирования в WebEngine |

### tests/
| Файл | Описание |
|------|----------|
| `test_services.py` | Тесты для сервисов (actor, episode, export) |
| `test_additional.py` | Дополнительные тесты |

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

## Зависимости

| Пакет | Версия | Назначение |
|-------|--------|------------|
| `pyside6` | 6.10.2 | GUI фреймворк |
| `pyside6-addons` | 6.10.2 | Дополнительные компоненты Qt |
| `python-osc` | 1.9.3 | OSC протокол |
| `openpyxl` | >=3.0.0 | Excel экспорт |
| `requests` | 2.32.5 | HTTP запросы |
| `pytest` | >=7.0.0 | Тестирование |
| `pytest-cov` | >=4.0.0 | Покрытие кода |

## Примечания

- **ActorController** — контроллер для управления панелью актёров
- **ExportService** — поддержка пакетного экспорта, объединение реплик
- **ReplicaMergeSettingsDialog** — диалог настроек объединения реплик
- **GlobalSettingsService** — глобальные настройки приложения (сохраняются в ~/.dubbing_manager/ или %APPDATA%)
