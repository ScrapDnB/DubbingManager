# Структура проекта Dubbing Manager

## Обзор

Dubbing Manager — PySide6-приложение для проектов дубляжа. Архитектура постепенно движется к схеме:

```text
UI -> Controllers -> Services -> Project data / Working text files
```

Главная архитектурная договорённость: ASS/SRT/DOCX являются источниками импорта, а редактируемым источником текста после импорта становится рабочий JSON серии в папке `texts_dm`.

## Дерево проекта

```text
DubbingManager/
├── main.py
├── README.md
├── STRUCTURE.md
├── CODEX_CONTEXT.md
├── requirements.txt
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
│   ├── docx_import_service.py
│   ├── episode_service.py
│   ├── export_service.py
│   ├── global_settings_service.py
│   ├── osc_worker.py
│   ├── project_folder_service.py
│   ├── project_service.py
│   └── script_text_service.py
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── preview.py
│   ├── teleprompter.py
│   ├── video.py
│   │
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── actor_controller.py
│   │   ├── episode_controller.py
│   │   ├── export_controller.py
│   │   └── project_controller.py
│   │
│   └── dialogs/
│       ├── __init__.py
│       ├── actor_filter.py
│       ├── colors.py
│       ├── docx_import.py
│       ├── edit_text_dialog.py
│       ├── export.py
│       ├── project_files.py
│       ├── reaper.py
│       ├── replica_merge.py
│       ├── roles.py
│       ├── search.py
│       └── summary.py
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py
│   └── web_bridge.py
│
├── docs/
│   ├── DOCX_IMPORT.md
│   └── DOCX_IMPORT_IMPLEMENTATION.md
│
└── tests/
    ├── test_assignment_service.py
    ├── test_script_text_service.py
    ├── test_working_text_migration.py
    ├── test_docx_working_text_import.py
    ├── test_project_folder_service.py
    ├── test_project_files_dialog.py
    ├── test_teleprompter_episode_switch.py
    └── ...
```

## Формат проекта

Текущая версия формата задаётся в `config/constants.py`:

```python
PROJECT_VERSION = "1.2"
```

Ключевые поля проекта:

| Поле | Назначение |
|------|------------|
| `metadata` | Версия формата, даты создания/изменения |
| `project_name` | Имя проекта |
| `actors` | База актёров |
| `episodes` | Исходные файлы серий |
| `episode_texts` | Рабочие JSON-тексты серий |
| `global_map` | Глобальные назначения персонаж -> актёр |
| `episode_actor_map` | Локальные назначения персонаж -> актёр внутри серии |
| `video_paths` | Видео по сериям |
| `project_folder` | Рабочая папка проекта для сканирования файлов |
| `export_config` | Настройки экспорта |
| `prompter_config` | Настройки телесуфлёра |
| `replica_merge_config` | Настройки объединения реплик |

Обратная совместимость старых проектов обеспечивается в `ProjectService._ensure_compatibility`.

## Рабочие тексты

После импорта ASS/SRT/DOCX создаётся рабочий текст серии. Он хранится как JSON-файл в папке:

```text
texts_dm/
```

Название папки задаётся константой `SCRIPT_TEXT_DIR_NAME`.

Рабочий текст используется для:

- монтажных листов;
- телесуфлёра;
- глобального поиска;
- статистики серии и проекта;
- статистики выбранного персонажа;
- экспорта.

ASS/SRT/DOCX остаются источниками импорта. Запись изменений обратно в ASS/SRT отключена.

Ключевые места:

| Файл | Роль |
|------|------|
| `services/script_text_service.py` | Создание, загрузка, сохранение и переименование рабочих текстов |
| `ui/main_window.py` | `get_episode_lines`, импорт, миграция старых проектов |
| `ui/teleprompter.py` | Редактирование реплик рабочего текста |
| `ui/dialogs/project_files.py` | Перепривязка и регенерация рабочих текстов |
| `services/project_folder_service.py` | Сканирование папки проекта |

## Назначения актёров

Назначения бывают двух уровней:

| Уровень | Хранилище | Поведение |
|---------|-----------|-----------|
| Глобально | `global_map` | Роль получает одного актёра во всех сериях |
| Серия | `episode_actor_map[ep]` | Назначение действует только в выбранной серии |

Для чтения эффективного актёра используйте `services/assignment_service.py`, особенно:

- `get_actor_for_character(project_data, char_name, ep_num)`
- `get_assignment_scope(project_data, char_name, ep_num)`
- `get_assignment_map(project_data, scope, ep_num)`
- `get_actor_roles(project_data, actor_id)`
- `rename_character_assignments(project_data, old_name, new_name)`

`LOCAL_UNASSIGNED_ACTOR_ID` означает локальное “не назначено”, которое перекрывает глобальное назначение.

Места, где важен эффективный актёр:

- главный список персонажей;
- телесуфлёр;
- HTML/Excel экспорт;
- Reaper RPP;
- отчёты;
- роли актёра;
- статистика персонажа.

## Основные модули

### `config/`

| Файл | Описание |
|------|----------|
| `constants.py` | UI-размеры, версии проекта, имена папок, настройки по умолчанию |

### `core/`

| Файл | Описание |
|------|----------|
| `commands.py` | Command pattern для Undo/Redo |
| `models.py` | Dataclass-модели с валидацией |

### `services/`

| Файл | Описание |
|------|----------|
| `project_service.py` | Загрузка/сохранение проекта, атомарная запись, совместимость |
| `script_text_service.py` | Рабочие тексты серий |
| `assignment_service.py` | Глобальные и локальные назначения актёров |
| `episode_service.py` | Парсинг ASS/SRT и кэш эпизодов |
| `docx_import_service.py` | Импорт DOCX и парсинг таблиц |
| `export_service.py` | Объединение реплик, HTML/XLSX экспорт |
| `actor_service.py` | Операции с актёрами и ролями |
| `global_settings_service.py` | Глобальные настройки приложения |
| `project_folder_service.py` | Сканирование и перепривязка файлов проекта |
| `osc_worker.py` | OSC-синхронизация с Reaper |

### `ui/`

| Файл | Описание |
|------|----------|
| `main_window.py` | Главное окно, импорт, таблица ролей, статистика персонажа, интеграция сервисов |
| `teleprompter.py` | Телесуфлёр, редактирование текста, переключение серий |
| `preview.py` | HTML Live Preview |
| `video.py` | Видео-предпросмотр |

### `ui/controllers/`

| Файл | Описание |
|------|----------|
| `actor_controller.py` | Таблица актёров и кнопка ролей |
| `episode_controller.py` | Операции с эпизодами |
| `export_controller.py` | Экспорт через контроллер |
| `project_controller.py` | Сохранение, загрузка и автосохранение проекта |

### `ui/dialogs/`

| Файл | Описание |
|------|----------|
| `actor_filter.py` | Фильтр/подсветка актёров |
| `colors.py` | Цветовые диалоги |
| `docx_import.py` | Настройки импорта DOCX |
| `edit_text_dialog.py` | Редактирование реплики |
| `export.py` | Настройки экспорта |
| `project_files.py` | Состояние, перепривязка и регенерация файлов проекта |
| `reaper.py` | Настройки Reaper RPP |
| `replica_merge.py` | Настройки объединения реплик |
| `roles.py` | Просмотр ролей актёра со статистикой |
| `search.py` | Глобальный поиск |
| `summary.py` | Отчёты по серии/проекту |

## Главный UI

Главная таблица персонажей:

| Колонка | Значение |
|---------|----------|
| `Персонаж` | Имя персонажа, редактируемое |
| `Строчек` | Количество исходных строк в текущей серии |
| `Колец` | Количество объединённых реплик |
| `Слов` | Количество слов |
| `Область` | `Глобально` или `Серия` |
| `Актер` | Назначенный актёр |
| `📺` | Предпросмотр реплик персонажа |

Правая панель:

- сверху инструменты: предпросмотр серии, телесуфлёр, Reaper RPP;
- снизу статистика выбранного персонажа по всем сериям.

## DOCX импорт

DOCX поддерживает:

- выбор таблицы;
- гибкое назначение колонок;
- тайминг в одной или разных колонках;
- предпросмотр;
- сохранение последней конфигурации колонок в глобальные настройки.

После импорта DOCX должен вести себя как ASS/SRT: создаётся рабочий текст, работают поиск, статистика, экспорт и телесуфлёр.

## Проектная папка и файлы

Окно `Файлы` показывает состояние:

- исходников серий;
- рабочих текстов;
- видео.

Сканер должен искать и перепривязывать существующие файлы. Он не должен сам создавать новые серии или импортировать новые исходники без явного отдельного решения.

## Архитектурные принципы

1. **Service Layer + MVC**  
   UI вызывает контроллеры и сервисы, бизнес-логика не должна жить в виджетах, если её легко вынести.

2. **Рабочий текст как источник правок**  
   После импорта редактируется рабочий JSON, не ASS/SRT.

3. **Эффективное назначение актёра**  
   Любой код с контекстом серии должен учитывать `episode_actor_map` поверх `global_map`.

4. **Command Pattern**  
   Основные операции должны проходить через команды Undo/Redo, когда это ожидаемо для пользователя.

5. **Совместимость проектов**  
   Новые поля добавляются через `ProjectService._ensure_compatibility`.

6. **Константы вместо магических значений**  
   UI-размеры, имена папок и настройки по умолчанию держать в `config/constants.py`.

## Тесты

Полный прогон:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ -q
```

Актуальный ориентир:

```text
540 passed, 11 skipped
```

Полезные точечные прогоны:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_assignment_service.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_script_text_service.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_export_service.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_project_folder_service.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_project_files_dialog.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_teleprompter_episode_switch.py -q
```

## Зависимости

| Пакет | Назначение |
|-------|------------|
| `PySide6` | GUI |
| `python-osc` | OSC-синхронизация с Reaper |
| `openpyxl` | Excel экспорт |
| `python-docx` | DOCX импорт |
| `pytest`, `pytest-cov` | Тесты |

## Документация для продолжения работы

Для Codex/разработческих заметок см. `CODEX_CONTEXT.md`. Там перечислены последние архитектурные решения, пользовательски подтверждённое поведение и частые ловушки.
