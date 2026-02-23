# Гарантия обратной совместимости

## ✅ Старые проекты работают без изменений

**Если вы откроете старый проект в новой версии и сохраните его — он НЕ повредится.**

---

## Как это работает

### 1. Загрузка старого проекта

```python
# Старый формат (без metadata)
{
  "project_name": "Старый проект",
  "actors": {...},
  "episodes": {...}
  # Нет: metadata, video_paths, export_config, etc.
}
```

**При загрузке:**
```python
def load_project(self, path: str):
    data = json.load(f)
    
    # 1. Валидация (проверяем обязательные поля)
    self._validate_project_structure(data)
    
    # 2. Обратная совместимость (добавляем缺失ствующие поля)
    self._ensure_compatibility(data)
    
    return data
```

**После загрузки:**
```python
{
  "project_name": "Старый проект",
  "actors": {...},
  "episodes": {...},
  # Добавлено автоматически:
  "metadata": {
    "format_version": "0.9",  # Помечается как старый
    "app_version": "pre-1.0",
    "created_at": "2026-02-23T...",
    "modified_at": "2026-02-23T..."
  },
  "video_paths": {},
  "export_config": {...},
  "prompter_config": {...},
  "global_map": {},
  "loaded_episodes": {}
}
```

---

### 2. Сохранение проекта

```python
def save_project(self, data, path):
    # Обновляем metadata
    self._update_metadata_on_save(data)
    
    # Атомарное сохранение
    self._do_save(data, path)
```

**После сохранения:**
```json
{
  "metadata": {
    "format_version": "1.0",  # Обновлена версия
    "app_version": "1.0+",
    "modified_at": "2026-02-23T15:30:00"  # Обновлено время
  },
  "project_name": "Старый проект",
  ...
}
```

---

## Тесты на обратную совместимость

### test_load_old_project_format
```python
def test_load_old_project_format(self, tmp_path):
    """Загрузка старого формата проекта (без metadata)"""
    old_format = {
        "project_name": "Старый проект",
        "actors": {"actor1": {"name": "Актёр 1", "color": "#FF0000"}},
        "episodes": {"1": "/path/to/episode.ass"},
    }
    
    data = service.load_project(old_file)
    
    # Проверяем, что загрузился
    assert data["project_name"] == "Старый проект"
    
    # Проверяем, что добавлены缺失ствующие поля
    assert "metadata" in data
    assert "video_paths" in data
    assert "export_config" in data
```

### test_save_old_project_adds_metadata
```python
def test_save_old_project_adds_metadata(self, tmp_path):
    """Сохранение старого проекта добавляет metadata"""
    old_format = {
        "project_name": "Старый проект",
        "actors": {},
        "episodes": {},
    }
    
    data = service.load_project(old_file)
    service.save_project(data, new_file)
    
    # Проверяем, что metadata добавлен
    assert "metadata" in saved_data
    assert saved_data["metadata"]["format_version"] == "1.0"
```

---

## Что добавляется автоматически

| Поле | Значение по умолчанию | Когда добавляется |
|------|----------------------|-------------------|
| `metadata` | `{format_version: "0.9", ...}` | При загрузке старого |
| `video_paths` | `{}` | При загрузке старого |
| `export_config` | `DEFAULT_EXPORT_CONFIG` | При загрузке старого |
| `prompter_config` | `DEFAULT_PROMPTER_CONFIG` | При загрузке старого |
| `global_map` | `{}` | При загрузке старого |
| `loaded_episodes` | `{}` | При загрузке старого |

---

## Обновление metadata

### При загрузке:
```python
"metadata": {
  "format_version": "0.9",  # Старый формат
  "app_version": "pre-1.0",
  "created_at": "...",
  "modified_at": "..."
}
```

### При сохранении:
```python
"metadata": {
  "format_version": "1.0",  # Новый формат
  "app_version": "1.0+",
  "modified_at": "2026-02-23T15:30:00"  # Обновлено
}
```

---

## Гарантии

### ✅ Что сохраняется:
- Все актёры
- Все эпизоды
- Все назначения ролей
- Все настройки экспорта
- Все настройки суфлёра

### ✅ Что добавляется:
- `metadata` (автоматически)
- `video_paths` (пустой dict)
- `export_config` (значения по умолчанию)
- `prompter_config` (значения по умолчанию)

### ❌ Что НЕ ломается:
- Структура `actors`
- Структура `episodes`
- Структура `global_map`
- Пользовательские настройки

---

## Миграция по версиям

| Версия | Изменения |
|--------|-----------|
| **< 1.0** | Нет `metadata`, `video_paths`, `export_config` |
| **1.0** | Добавлен `metadata`, атомарное сохранение, бэкапы |

**Автоматическая миграция:**
```
Старый проект → Загрузка → _ensure_compatibility() → Сохранение → Новый формат
```

---

## Проверка на реальных проектах

### Шаг 1: Откройте старый проект
```bash
python main.py
# File → Open → выберите старый .json
```

### Шаг 2: Проверьте лог
```
INFO - Project loaded from /path/to/old.json
INFO - Actors count: 21
INFO - Global map count: 73
```

### Шаг 3: Сохраните проект
```bash
# File → Save
```

### Шаг 4: Проверьте новый файл
```json
{
  "metadata": {
    "format_version": "1.0",
    "app_version": "1.0+",
    "modified_at": "2026-02-23T..."
  },
  "project_name": "...",
  ...
}
```

### Шаг 5: Убедитесь, что всё работает
- ✅ Актёры на месте
- ✅ Эпизоды на месте
- ✅ Назначения ролей работают
- ✅ Экспорт работает

---

## Частые вопросы

### ❓ Можно ли открыть новый проект в старой версии?

**Нет.** Новая версия добавляет поля, которых нет в старой:
- `metadata`
- `video_paths`
- `export_config`

Старая версия может не понять эти поля.

### ❓ Нужно ли делать бэкап перед обновлением?

**Рекомендуется.** Хотя мы гарантируем обратную совместимость, бэкап защитит от:
- Ошибок пользователя
- Сбоев питания
- Повреждения диска

### ❓ Как откатиться к старой версии?

1. Найдите бэкап в `.backups/`
2. Скопируйте его в основную директорию
3. Откройте в старой версии

---

## Заключение

✅ **Старые проекты работают без изменений**

✅ **При сохранении добавляется metadata**

✅ **Все данные сохраняются**

✅ **Тесты покрывают обратную совместимость**

✅ **Бэкапы создаются автоматически**
