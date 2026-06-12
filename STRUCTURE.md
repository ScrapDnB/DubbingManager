# Структура проекта Dubbing Manager

## Обзор

Dubbing Manager — PySide6-приложение для подготовки проектов дубляжа. Основной поток данных:

```text
UI -> Controllers -> Services -> Project JSON / Working text JSON
```

Главная архитектурная договорённость:

- ASS/SRT/DOCX — источники импорта.
- Рабочий JSON серии в `texts_dm` — редактируемый источник текста после импорта.
- Экспорт, телесуфлёр, поиск и отчёты должны читать рабочие тексты.
- Назначения актёров могут быть глобальными для проекта или локальными для серии.

## Дерево проекта

```text
DubbingManager/
├── main.py
├── README.md
├── STRUCTURE.md
├── requirements.txt
├── dubbing_manager.spec
├── pytest.ini
│
├── .github/
│   ├── BUILD.md
│   └── workflows/
│       ├── build.yml
│       └── tests.yml
│
├── config/
│   ├── __init__.py
│   └── constants.py
│
├── core/
│   ├── __init__.py
│   ├── commands.py
│   └── models.py
│
├── services/
│   ├── __init__.py
│   ├── actor_service.py
│   ├── assignment_service.py
│   ├── assignment_transfer_service.py
│   ├── character_stats_service.py
│   ├── docx_import_service.py
│   ├── episode_service.py
│   ├── export_layouts.py
│   ├── export_service.py
│   ├── global_settings_service.py
│   ├── osc_worker.py
│   ├── project_compatibility.py
│   ├── project_folder_service.py
│   ├── project_health_service.py
│   ├── project_service.py
│   ├── quick_subtitle_service.py
│   ├── reaper_rpp_service.py
│   ├── replica_merge_service.py
│   ├── teleprompter_navigation_service.py
│   ├── script_text_service.py
│   └── update_service.py
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── main_window_ui.py
│   ├── preview.py
│   ├── preview_helpers.py
│   ├── teleprompter.py
│   ├── teleprompter_widgets.py
│   ├── video.py
│   │
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── actor_controller.py
│   │   ├── episode_controller.py
│   │   ├── export_controller.py
│   │   ├── global_actor_controller.py
│   │   ├── import_controller.py
│   │   ├── reaper_export_controller.py
│   │   ├── project_controller.py
│   │   └── settings_controller.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── main_table_model.py
│   │
│   ├── widgets/
│   │   ├── __init__.py
│   │   └── quick_subtitle_drop_zone.py
│   │
│   └── dialogs/
│       ├── __init__.py
│       ├── actor_filter.py
│       ├── colors.py
│       ├── docx_import.py
│       ├── project_files.py
│       ├── project_health.py
│       ├── reaper.py
│       ├── roles.py
│       ├── search.py
│       ├── settings.py
│       ├── settings_helpers.py
│       └── summary.py
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py
│   └── web_bridge.py
│
├── resources/
│   └── icons/
│
├── scripts/
│   └── prepare_icons.py
│
├── docs/
│   ├── CHANGELOG.md
│   ├── DOCX_IMPORT.md
│   ├── PROJECT_FILES_DIALOG.md
│   ├── PROJECT_FOLDER.md
│   └── UNDO_REDO.md
│
└── tests/
    ├── test_assignment_service.py
    ├── test_assignment_transfer_service.py
    ├── test_docx_working_text_import.py
    ├── test_export_service.py
    ├── test_global_settings_service.py
    ├── test_main_window_project.py
    ├── test_project_files_dialog.py
    ├── test_reaper_dialog.py
    ├── test_script_text_service.py
    ├── test_working_text_migration.py
    └── ...
```

## Версии

Версии задаются в `config/constants.py`:

```python
APP_VERSION = "1.6.0"
PROJECT_VERSION = "1.3"
SCRIPT_TEXT_DIR_NAME = "texts_dm"
```

`APP_VERSION` — версия приложения и сборки.  
`PROJECT_VERSION` — версия формата проекта, её стоит менять только при изменении схемы данных проекта.

## Формат проекта

Ключевые поля project JSON:

| Поле | Назначение |
|------|------------|
| `metadata` | версия формата, версия приложения, даты |
| `project_name` | имя проекта |
| `project_folder` | рабочая папка проекта |
| `actors` | актёры, занятые в проекте |
| `episodes` | исходные файлы серий: ASS/SRT/DOCX |
| `episode_texts` | рабочие JSON-тексты серий |
| `global_map` | глобальные назначения персонаж -> актёр |
| `episode_actor_map` | локальные назначения внутри серии |
| `video_paths` | видео по сериям |
| `export_config` | настройки HTML/Excel экспорта |
| `prompter_config` | настройки телесуфлёра |
| `replica_merge_config` | настройки объединения реплик |
| `docx_import_config` | настройки импорта DOCX |

Совместимость старых проектов обеспечивается в `services/project_compatibility.py`, а `ProjectService._ensure_compatibility` остаётся совместимым фасадом.

## Рабочие тексты

`ScriptTextService` создаёт и читает рабочие JSON-файлы серий. После импорта рабочий текст становится основным источником для UI и экспорта.

Стандартные места поиска рабочих текстов:

- папка проекта: `texts_dm/episode_N.json`;
- папка рядом с файлом проекта: `<project_name>_texts_dm/episode_N.json`;
- папка `texts_dm` рядом с исходником серии.

Перед перезаписью рабочих текстов создаются бэкапы в `.backups`.

Ключевые места:

| Файл | Роль |
|------|------|
| `services/script_text_service.py` | создание, загрузка, сохранение, поиск и бэкап рабочих текстов |
| `ui/main_window.py` | координация окна и `get_episode_lines` |
| `ui/controllers/import_controller.py` | импорт, миграция и пересоздание текстов |
| `ui/teleprompter.py` | отображение и редактирование реплик |
| `utils/web_bridge.py` | сохранение правок из HTML/телесуфлёра |
| `ui/dialogs/project_files.py` | перепривязка и пересоздание рабочих текстов |

## DOCX

DOCX импорт реализован через:

| Файл | Роль |
|------|------|
| `services/docx_import_service.py` | извлечение таблиц, автоопределение колонок, парсинг |
| `ui/dialogs/docx_import.py` | UI маппинга колонок и предпросмотра |
| `services/script_text_service.py` | сохранение результата как рабочего JSON |

DOCX считается уже подготовленным монтажным источником. При создании рабочего текста строки DOCX не проходят через объединение реплик.

## Назначения актёров

Назначения хранятся в двух уровнях:

| Уровень | Хранилище | Поведение |
|---------|-----------|-----------|
| Глобально | `global_map` | роль получает актёра во всех сериях |
| Серия | `episode_actor_map[ep]` | назначение действует только в выбранной серии |

Для чтения эффективного назначения используйте `services/assignment_service.py`:

- `get_actor_for_character(project_data, char_name, ep_num)`
- `get_assignment_scope(project_data, char_name, ep_num)`
- `get_assignment_map(project_data, scope, ep_num)`
- `get_actor_roles(project_data, actor_id)`
- `rename_character_assignments(project_data, old_name, new_name)`

`LOCAL_UNASSIGNED_ACTOR_ID` означает локальное «не назначено», которое перекрывает глобальное назначение.

## Глобальная база актёров

Глобальная база хранится в глобальных настройках через `GlobalSettingsService`.

Запись актёра содержит:

```json
{
  "name": "Actor Name",
  "gender": "М"
}
```

Основные правила:

- В проекте хранятся только занятые актёры.
- В глобальной базе хранятся общие актёры между проектами.
- Актёры сопоставляются по имени, а не только по ID.
- При совпадении имени проектный актёр сопоставляется с записью глобальной базы, но проектный цвет остаётся настройкой проекта.
- Изменение цвета актёра внутри проекта не обязано менять глобальную базу.

Перенос распределения актёров между проектами реализован в `services/assignment_transfer_service.py`.

## Экспорт

Экспорт разделён на фасад и специализированные модули:

| Файл | Роль |
|------|------|
| `services/export_service.py` | фасад экспорта и файловые операции |
| `services/export_layouts.py` | HTML/DOCX-разметки монтажных листов |
| `services/replica_merge_service.py` | объединение соседних реплик |
| `services/reaper_rpp_service.py` | генерация и предпросмотр Reaper RPP |

HTML/Excel/DOCX экспорт поддерживает:

- выбор колонок;
- цветовую подсветку актёров;
- фильтр актёров для подсветки;
- округление тайминга;
- режим тайминга «начало и конец» или «только начало».

Reaper RPP экспорт должен использовать начало и конец фразы для регионов и не применять offset телесуфлёра к регионам.

Быстрый временный предпросмотр ASS/SRT без добавления серии в проект реализован через `services/quick_subtitle_service.py` и `ui/widgets/quick_subtitle_drop_zone.py`.

## Главный UI

Главное окно находится в `ui/main_window.py`. Это интеграционный слой, который связывает сервисы, контроллеры и диалоги. Сборка виджетов вынесена в `ui/main_window_ui.py`, а модель главной таблицы — в `ui/models/main_table_model.py`.

Главная таблица персонажей:

| Колонка | Значение |
|---------|----------|
| `Персонаж` | имя персонажа, редактируемое |
| `Строчек` | количество строк |
| `Колец` | количество реплик |
| `Слов` | количество слов |
| `Область` | `Глобально` или `Серия` |
| `Актер` | назначенный актёр |
| `📺` | предпросмотр реплик персонажа |

Верхняя панель:

- новый проект;
- недавние проекты;
- открыть/сохранить/сохранить копию;
- папка проекта;
- импорт;
- привязка видео;
- поиск и фильтры.

Правая панель:

- инструменты: предпросмотр серии, телесуфлёр, Reaper RPP, отчёт серии;
- статистика выбранного персонажа.

## Диалоги и настройки

`ui/dialogs/settings.py` — единое окно настроек. Общие фабрики контролов вынесены в `ui/dialogs/settings_helpers.py`.

- экспорт;
- объединение реплик;
- телесуфлёр;
- DOCX;
- проект;
- базы актёров.

`ui/preview.py` — HTML Live Preview. Настройки колонок и тайминга в предпросмотре сохраняются в основные настройки экспорта. Чистые операции подготовки данных вынесены в `ui/preview_helpers.py`.

`ui/dialogs/reaper.py` — параметры Reaper RPP и живой предпросмотр будущего RPP.

## Сборка

Основные файлы:

| Файл | Назначение |
|------|------------|
| `dubbing_manager.spec` | PyInstaller spec для macOS и Windows |
| `scripts/prepare_icons.py` | подготовка `.icns`, `.ico` и iconset |
| `.github/workflows/tests.yml` | тесты на macOS и Windows |
| `.github/workflows/build.yml` | сборка macOS DMG и Windows ZIP |
| `.github/BUILD.md` | инструкция по сборке и релизу |

Локальный запуск PyInstaller:

```bash
python scripts/prepare_icons.py
python -m PyInstaller dubbing_manager.spec --clean
```

Локальная macOS-сборка:

```bash
./build.sh
```

`build.sh` локальный и игнорируется Git.

## Архитектурные принципы

1. **Рабочий JSON как источник правок**  
   После импорта редактируется JSON, не ASS/SRT/DOCX.

2. **Сервисы отвечают за бизнес-логику**  
   UI может оставаться интеграционным слоем, но повторяемая логика должна жить в `services/`.

3. **Эффективное назначение актёра**  
   Любой код с контекстом серии должен учитывать `episode_actor_map` поверх `global_map`.

4. **Глобальная база по имени**  
   Актёры из старых проектов синхронизируются с глобальной базой по имени.

5. **Совместимость проектов**  
   Новые поля добавляются через `services/project_compatibility.py`.

6. **Бэкапы перед перезаписью**  
   Рабочие тексты и глобальные настройки должны сохранять резервную копию перед опасной записью.

7. **Тесты на macOS и Windows**  
   Любые изменения путей, файлов и настроек должны быть кроссплатформенными.

## Тесты

Полный прогон:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Актуальный ориентир для версии 1.6.0:

```text
698 passed, 11 skipped, 1 warning
```

Полезные точечные прогоны:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_global_settings_service.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_main_window_project.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_assignment_transfer_service.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_export_service.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_replica_merge_service.py tests/test_reaper_dialog.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_project_files_dialog.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_preview_helpers.py tests/test_project_compatibility.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_teleprompter_navigation_service.py -q
```

## Зависимости

| Пакет | Назначение |
|-------|------------|
| `PySide6` | GUI |
| `python-osc` | OSC-синхронизация с Reaper |
| `openpyxl` | Excel экспорт |
| `python-docx` | DOCX импорт |
| `requests` | вспомогательные HTTP-запросы |
| `pytest`, `pytest-cov` | тесты |
