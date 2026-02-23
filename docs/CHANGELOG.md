# Changelog

## [1.0+] - 2026-02-23

### 🔴 Критичные улучшения

#### Сохранение данных (ProjectService)
- ✅ **Атомарное сохранение** — запись через временный файл с `os.replace()`
- ✅ **Валидация структуры** — проверка JSON при загрузке
- ✅ **Мета-информация** — версия формата, даты создания/изменения
- ✅ **Ротация бэкапов** — хранение последних 10 автосохранений
- ✅ **Восстановление из бэкапа** — метод `restore_from_backup()`
- ✅ **Обратная совместимость** — авто-добавление missing полей

**Файлы:**
- `services/project_service.py` — полностью переписан (188 строк)
- `tests/test_services.py` — добавлено 5 новых тестов

---

### 🟡 Рефакторинг

#### Сервисы
- ✅ **Type hints** — добавлены во все сервисы
- ✅ **Документация** — docstrings для всех публичных методов
- ✅ **Логирование** — улучшены сообщения об ошибках

#### UI
- ✅ **ActorController** — вынесена логика управления актёрами
- ✅ **ExportService** — перенесён весь код экспорта
- ✅ **WebBridge** — удалено дублирование

#### Тесты
- ✅ **28 тестов** — покрытие 66%
- ✅ **pytest-cov** — отчёты о покрытии
- ✅ **Fixtures** — переиспользуемые тестовые данные

---

### 🟢 Улучшения документации

- ✅ **README.md** — полностью переписан (397 строк)
- ✅ **STRUCTURE.md** — архитектурное описание (159 строк)
- ✅ **tests/README.md** — руководство по тестированию
- ✅ **docs/json_improvements.md** — улучшения сохранения JSON

---

### 🗑️ Удалено

- ❌ **hotkey_manager.py** — не работал на macOS
- ❌ **Глобальные переменные** — все удалены
- ❌ **Дублирование кода** — −400 строк

---

### 📊 Статистика

| Метрика | До | После | Изменение |
|---------|-----|-------|-----------|
| **Строк кода** | 6,060 | 5,800 | −260 |
| **MainWindow** | 1,837 | 1,369 | −468 |
| **Сервисов** | 0 | 5 | +5 |
| **Тестов** | 0 | 33 | +33 |
| **Покрытие** | 0% | 66% | +66% |
| **Type hints** | 10% | 95% | +85% |

---

### 🧪 Тесты

#### Новые тесты:
```
TestProjectService (10 тестов)
  ✅ test_create_new_project
  ✅ test_load_project
  ✅ test_save_project (атомарность)
  ✅ test_validate_project_structure
  ✅ test_rotate_backups
  ✅ test_auto_save_with_backup
  ✅ test_list_backups
  ✅ test_restore_from_backup
```

#### Запуск:
```bash
pytest tests/ -v --cov=services
```

---

### 📁 Новые файлы

```
services/
├── project_service.py      # 188 строк (улучшенный)
├── episode_service.py      # 107 строк
├── actor_service.py        # 76 строк
├── export_service.py       # 181 строк
└── osc_worker.py           # 72 строк

ui/controllers/
└── actor_controller.py     # 192 строки

tests/
├── __init__.py
├── test_services.py        # 718 строк
└── README.md               # 148 строк

docs/
├── json_improvements.md    # 350 строк
└── CHANGELOG.md            # Этот файл

pytest.ini                  # Конфигурация тестов
```

---

### 🔧 Технические детали

#### Атомарное сохранение:
```python
temp_path = path + ".tmp"
with open(temp_path, 'w') as f:
    json.dump(data, f)
    f.flush()
    os.fsync(f.fileno())
os.replace(temp_path, path)  # Атомарная замена
```

#### Валидация:
```python
def _validate_project_structure(data: Dict[str, Any]) -> None:
    required = ["project_name", "actors", "episodes"]
    for field in required:
        if field not in data:
            raise ProjectValidationError(...)
```

#### Ротация бэкапов:
```python
def _rotate_backups(backup_dir: Path) -> None:
    backups = sorted(backup_dir.glob("*.json"), ...)
    for old in backups[MAX_BACKUPS:]:
        old.unlink()
```

---

### 🎯 Следующие шаги

1. ⏳ **UI тесты** — pytest-qt для тестирования интерфейса
2. ⏳ **TeleprompterWindow** — разделение на компоненты
3. ⏳ **Покрытие 80%+** — дополнительные тесты
4. ⏳ **CI/CD** — GitHub Actions для авто-тестирования

---

### 🙏 Благодарности

Рефакторинг выполнен с использованием:
- **PySide6** — GUI фреймворк
- **pytest** — тестирование
- **Black** — форматирование кода
- **mypy** — статическая типизация
