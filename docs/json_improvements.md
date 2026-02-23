# Улучшения сохранения данных в JSON

## Реализованные улучшения

### 1. ✅ Атомарное сохранение

**Проблема:** При ошибке записи файл проекта мог быть повреждён.

**Решение:** Сохранение через временный файл с атомарной заменой:

```python
def _do_save(self, data: Dict[str, Any], path: str) -> bool:
    temp_path = path + ".tmp"
    
    try:
        # Запись во временный файл
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())  # Гарантия записи на диск
        
        # Атомарная замена
        os.replace(temp_path, path)
        return True
    except Exception as e:
        # Очистка при ошибке
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False
```

**Преимущества:**
- ✅ Данные не будут повреждены при сбое питания
- ✅ Автоматическая очистка временных файлов
- ✅ Гарантия записи на диск через `fsync()`

---

### 2. ✅ Валидация структуры данных

**Проблема:** При загрузке повреждённого файла приложение могло упасть.

**Решение:** Валидация при загрузке:

```python
def _validate_project_structure(self, data: Dict[str, Any]) -> None:
    required_fields = ["project_name", "actors", "episodes"]
    
    for field in required_fields:
        if field not in data:
            raise ProjectValidationError(f"Missing required field: {field}")
    
    if not isinstance(data["project_name"], str):
        raise ProjectValidationError("Field 'project_name' must be a string")
    
    if not isinstance(data["actors"], dict):
        raise ProjectValidationError("Field 'actors' must be a dictionary")
```

**Преимущества:**
- ✅ Раннее обнаружение повреждённых файлов
- ✅ Понятные сообщения об ошибках
- ✅ Защита от некорректных данных

---

### 3. ✅ Мета-информация проекта

**Проблема:** Не было информации о версии формата, датах создания/изменения.

**Решение:** Добавлен блок `metadata`:

```json
{
  "metadata": {
    "format_version": "1.0",
    "app_version": "1.0+",
    "created_at": "2026-02-23T12:00:00.000",
    "modified_at": "2026-02-23T15:30:00.000",
    "created_by": "",
    "studio": ""
  },
  "project_name": "...",
  ...
}
```

**Автоматическое обновление:**
```python
def _update_metadata_on_save(self, data: Dict[str, Any]) -> None:
    if "metadata" not in data:
        data["metadata"] = {}
    
    data["metadata"]["modified_at"] = datetime.now().isoformat()
    data["metadata"]["format_version"] = PROJECT_FORMAT_VERSION
```

**Преимущества:**
- ✅ Отслеживание версии формата
- ✅ История изменений
- ✅ Обратная совместимость

---

### 4. ✅ Ротация бэкапов

**Проблема:** Бэкапы накапливались бесконечно.

**Решение:** Хранение только последних 10 бэкапов:

```python
def _rotate_backups(self, backup_dir: Path) -> None:
    backups = sorted(
        backup_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    # Удаляем старые
    for old_backup in backups[MAX_BACKUPS:]:
        old_backup.unlink()
```

**Структура бэкапов:**
```
project.json
.backups/
├── project_20260223_120000.json
├── project_20260223_130000.json
└── project_20260223_140000.json  # Максимум 10 файлов
```

**Преимущества:**
- ✅ Защита от потери данных
- ✅ Автоматическая очистка старых бэкапов
- ✅ Именованные с timestamp

---

### 5. ✅ Восстановление из бэкапа

**Проблема:** Не было возможности восстановить из бэкапа.

**Решение:** Метод восстановления:

```python
def restore_from_backup(self, backup_path: str, target_path: str) -> bool:
    with open(backup_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    self._validate_project_structure(data)
    return self._do_save(data, target_path)
```

**Использование:**
```python
service = ProjectService()
backups = service.list_backups()  # Список доступных бэкапов

# Восстановление
service.restore_from_backup(
    backup_path=str(backups[0]),
    target_path="/path/to/project.json"
)
```

---

## Структура проекта (обновлённая)

```json
{
  "metadata": {
    "format_version": "1.0",
    "app_version": "1.0+",
    "created_at": "2026-02-23T12:00:00.000",
    "modified_at": "2026-02-23T15:30:00.000",
    "created_by": "",
    "studio": ""
  },
  "project_name": "Название проекта",
  "actors": {
    "actor_id": {
      "name": "Имя актёра",
      "color": "#RRGGBB"
    }
  },
  "global_map": {
    "Персонаж": "actor_id"
  },
  "episodes": {
    "1": "/path/to/episode1.ass"
  },
  "video_paths": {
    "1": "/path/to/video1.mp4"
  },
  "export_config": { ... },
  "prompter_config": { ... }
}
```

---

## Тестирование

Все улучшения покрыты тестами:

```bash
# Запустить тесты ProjectService
pytest tests/test_services.py::TestProjectService -v

# С покрытием
pytest tests/test_services.py::TestProjectService -v --cov=services
```

### Покрытие тестами:

| Тест | Статус |
|------|--------|
| `test_create_new_project` | ✅ |
| `test_load_project` | ✅ |
| `test_save_project` | ✅ |
| `test_validate_project_structure` | ✅ |
| `test_rotate_backups` | ✅ |
| `test_auto_save_with_backup` | ✅ |
| `test_list_backups` | ✅ |
| `test_restore_from_backup` | ✅ |

---

## Миграция старых проектов

Старые проекты без `metadata` автоматически обновляются при загрузке:

```python
def _ensure_compatibility(self, data: Dict[str, Any]) -> None:
    if "metadata" not in data:
        now = datetime.now().isoformat()
        data["metadata"] = {
            "format_version": "0.9",
            "app_version": "pre-1.0",
            "created_at": now,
            "modified_at": now,
        }
```

---

## Будущие улучшения

### Не реализовано (опционально):

1. **Сжатие JSON** (gzip) для больших проектов
2. **Шифрование** проектов с конфиденциальными данными
3. **Инкрементальное сохранение** (только изменения)
4. **История изменений** (git-like)
5. **Синхронизация** с облачным хранилищем
