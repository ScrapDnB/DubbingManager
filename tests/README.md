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

## Структура тестов

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
