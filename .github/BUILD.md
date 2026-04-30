# CI/CD для Dubbing Manager

GitHub Actions собирает самодостаточные артефакты для:

- Windows: ZIP с папкой `Dubbing Manager` и `Dubbing Manager.exe`
- macOS: `Dubbing_Manager_macOS.dmg` с `Dubbing Manager.app`

## Когда запускается сборка

- Push в `master` или `main`
- Pull request в `master` или `main`
- Теги вида `v*`
- Ручной запуск через `Actions` -> `Build Dubbing Manager` -> `Run workflow`

## Что делает workflow

1. Ставит Python 3.14.
2. Устанавливает зависимости из `requirements.txt` и `pyinstaller`.
3. Запускает тесты: `python -m pytest -q`.
4. Собирает приложение через `python -m PyInstaller dubbing_manager.spec --clean`.
5. Проверяет наличие итогового артефакта.
6. Загружает ZIP/DMG в artifacts.
7. Для тегов `v*` прикрепляет ZIP/DMG к GitHub Release.

## Локальная macOS-сборка

Локально macOS лучше собирать тем же скриптом, который повторён в CI:

```bash
./build.sh
```

Скрипт собирает `.app`, подписывает его ad-hoc подписью, проверяет подпись и удаляет служебную папку PyInstaller `dist/Dubbing Manager`, оставляя финальный `dist/Dubbing Manager.app`.

## Windows-сборка

Windows-артефакт собирается на Windows runner. PyInstaller обычно не умеет корректно собирать Windows `.exe` с macOS.

Команда, которую использует CI:

```powershell
python -m PyInstaller dubbing_manager.spec --clean
Compress-Archive -Path "dist\Dubbing Manager" -DestinationPath "Dubbing_Manager_Windows.zip" -Force
```

Windows собирается в формате `onedir`, а не `onefile`, чтобы запуск был быстрее и надёжнее для PySide6/Qt.

## Публикация релиза

```bash
git tag v1.2.0
git push origin v1.2.0
```

После этого workflow соберёт Windows и macOS артефакты и прикрепит их к релизу.
