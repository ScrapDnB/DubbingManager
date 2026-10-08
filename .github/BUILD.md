# CI/CD для Dubbing Manager

GitHub Actions собирает самодостаточные артефакты для:

- Windows: ZIP с папкой `Dubbing Manager` и `Dubbing Manager.exe`
- macOS: `Dubbing_Manager_macOS.dmg` с `Dubbing Manager.app`

Обычные push/PR запускают отдельный лёгкий workflow `Tests`, без сборки ZIP/DMG.

## Когда запускается сборка

- Теги вида `v*`
- Ручной запуск через `Actions` -> `Build Dubbing Manager` -> `Run workflow`

## Что делает workflow

1. Ставит Python 3.14.
2. Устанавливает зависимости из `requirements.txt`.
3. Запускает тесты: `python -m pytest -q`.
4. Устанавливает закреплённый PyInstaller 6.20.0 и собирает приложение через
   `python -m PyInstaller dubbing_manager.spec --clean`.
5. Проверяет наличие итогового артефакта.
6. Загружает ZIP/DMG в artifacts.
7. Для тегов `v*` прикрепляет ZIP/DMG к GitHub Release.

## Локальная macOS-сборка

Локально macOS лучше собирать тем же скриптом, который повторён в CI:

```bash
./build.sh
```

Скрипт собирает `.app`, подписывает его ad-hoc подписью, проверяет подпись и удаляет служебную папку PyInstaller `dist/Dubbing Manager`, оставляя финальный `dist/Dubbing Manager.app`.

Релизная macOS-сборка выполняется на runner `macos-26`. PyInstaller bootloader
компилируется из исходников текущим Xcode, чтобы executable был связан с SDK 26
и системные AppKit-контролы получали актуальное оформление macOS, включая
Liquid Glass. Локальная сборка для проверки нового оформления также должна
использовать Xcode 26 и bootloader, собранный из исходников.

Если `./build.sh` обнаружит старый bootloader, он остановится до сборки. Его
можно пересобрать текущим Xcode командой:

```bash
PYINSTALLER_COMPILE_BOOTLOADER=1 .venv/bin/python -m pip install \
  --force-reinstall --no-cache-dir --no-binary=pyinstaller pyinstaller
```

## Windows-сборка

Windows-артефакт собирается на Windows runner. PyInstaller обычно не умеет корректно собирать Windows `.exe` с macOS.

Команда, которую использует CI:

```powershell
python -m PyInstaller dubbing_manager.spec --clean
Compress-Archive -Path "dist\Dubbing Manager" -DestinationPath "Dubbing_Manager_Windows.zip" -Force
```

Windows собирается в формате `onedir`, а не `onefile`, чтобы запуск был быстрее и надёжнее для PySide6/Qt.

## Сборка QML-пакета

Основная сборка использует QML-вход:

```bash
python -m PyInstaller dubbing_manager.spec --clean
```

На Windows:

```powershell
python -m PyInstaller dubbing_manager.spec --clean
```

Используется `qml_main.py`; в пакет включаются каталог `qml`, иконки и QML
backend.

В Windows ZIP также кладётся скрипт:

```powershell
Register_DUB_File_Association.ps1
```

Его можно один раз запустить из распакованной папки приложения, чтобы
зарегистрировать `.dub` и `.dub_backup` за `Dubbing Manager.exe` для текущего
пользователя. После этого двойной клик по проекту или резервной копии будет
открывать его в программе. Для удаления
ассоциации:

```powershell
.\Register_DUB_File_Association.ps1 -Unregister
```

## Публикация релиза

```bash
git checkout master
git tag -a v2.0.0 -m "Dubbing Manager 2.0.0"
git push origin master v2.0.0
```

Перед тегом обновите `APP_VERSION` в `config/constants.py`, README и
`RELEASE_NOTES.md`, затем выполните тесты и проверку QML.

После публикации тега workflow соберёт Windows и macOS артефакты и прикрепит
их к GitHub Release. Тег без суффикса создаёт стабильный релиз; суффиксы
`-beta` и `-rc` — предварительный. Проверьте успешное завершение обеих сборок
и наличие ZIP/DMG, затем оформите описание из `RELEASE_NOTES.md`.

При переходе на 2.0 ветка `legacy/1.7` сохраняет прежний `master` на релизе
1.7.1, а QML-интерфейс переносится в `master` с сохранением истории коммитов.
