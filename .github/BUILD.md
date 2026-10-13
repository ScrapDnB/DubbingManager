# CI/CD для Dubbing Manager

GitHub Actions собирает самодостаточные артефакты для:

- Windows: ZIP с папкой `Dubbing Manager` и `Dubbing Manager.exe`
- macOS: `Dubbing_Manager_macOS.dmg` с `Dubbing Manager.app`

Обычные push/PR запускают отдельный лёгкий workflow `Tests`, без сборки ZIP/DMG.

## Когда запускается сборка

- Теги вида `v*`
- Ручной запуск через `Actions` -> `Build Dubbing Manager` -> `Run workflow`

## Что делает workflow

1. Ставит Python 3.14 для Windows и Python 3.13 для macOS.
2. Устанавливает зависимости из `requirements.txt` для Windows и
   `requirements-macos13.txt` для macOS.
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

### Совместимость с macOS 13

Минимальная система приложения — macOS 13.0. Для этого библиотека Python,
bootloader и все нативные зависимости должны иметь deployment target не выше
13.0. SDK 26 и минимальная версия запуска — разные параметры: современный SDK
можно использовать при сохранении совместимости с macOS 13.

Python из Homebrew на новой macOS может требовать ту же новую систему.
Установка `MACOSX_DEPLOYMENT_TARGET=13.0` не меняет уже скомпилированный Python.
Кроме того, установленные пакеты PySide6 6.10.2 содержат модули с `minos 15.0`,
несмотря на метку `macosx_13_0` у wheel. Поэтому простой замены Python недостаточно.
Для macOS 13 подготовлен отдельный файл `requirements-macos13.txt` с PySide6 6.9.3.
Нативные файлы его официальных macOS wheels проверены на deployment target <=13.0.
Этот вариант использует Python 3.13: PySide6 6.9.3 не поддерживает Python 3.14.

Для локальной сборки установите обычный Python 3.13 из
[официального macOS installer](https://www.python.org/downloads/macos/)
(выберите выпуск ветки 3.13) и создайте отдельное
окружение. Указывайте полный путь, чтобы не использовать Python из Homebrew:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -m venv .venv-macos13
.venv-macos13/bin/python -m pip install --upgrade pip
MACOSX_DEPLOYMENT_TARGET=13.0 .venv-macos13/bin/python -m pip install -r requirements-macos13.txt
MACOSX_DEPLOYMENT_TARGET=13.0 PYINSTALLER_COMPILE_BOOTLOADER=1 \
  .venv-macos13/bin/python -m pip install \
  --no-cache-dir --no-binary=pyinstaller 'pyinstaller==6.20.0'
QT_QPA_PLATFORM=offscreen .venv-macos13/bin/python -m pytest -q
.venv-macos13/bin/python scripts/lint_qml.py
PYTHON_BIN=.venv-macos13/bin/python ./build.sh
```

Сборка проверяет библиотеку Python до очистки старых артефактов, а затем все
Mach-O файлы готового `.app`, включая Qt, Python, расширения `.so` и вложенные
исполняемые файлы. Несовместимая зависимость останавливает сборку. Ручная проверка:

```bash
.venv-macos13/bin/python scripts/verify_macos_compatibility.py 'dist/Dubbing Manager.app'
```

CI выполняет такую же проверку и задаёт `MACOSX_DEPLOYMENT_TARGET=13.0` до
установки зависимостей. macOS job использует Python 3.13 и
`requirements-macos13.txt`; Windows job сохраняет Python 3.14 / PySide6 6.10.2.
Перед выпуском проверьте запуск и основные функции на
macOS 13: проверка deployment target выявляет несовместимые бинарные файлы,
но не заменяет запуск на минимальной поддерживаемой системе. На Apple Silicon
эти команды создают ARM64-сборку; для Intel нужно отдельное окружение и сборка
под x86_64.

Релизная macOS-сборка выполняется на runner `macos-26`. PyInstaller bootloader
компилируется из исходников текущим Xcode, чтобы executable был связан с SDK 26
и системные AppKit-контролы получали актуальное оформление macOS, включая
Liquid Glass. Локальная сборка для проверки нового оформления также должна
использовать Xcode 26 и bootloader, собранный из исходников.

Если `./build.sh` обнаружит старый bootloader, он остановится до сборки. Его
можно пересобрать текущим Xcode командой:

```bash
MACOSX_DEPLOYMENT_TARGET=13.0 PYINSTALLER_COMPILE_BOOTLOADER=1 \
  .venv-macos13/bin/python -m pip install \
  --force-reinstall --no-cache-dir --no-binary=pyinstaller 'pyinstaller==6.20.0'
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
git tag -a v2.1.0 -m "Dubbing Manager 2.1.0"
git push origin master v2.1.0
```

Перед тегом обновите `APP_VERSION` в `config/constants.py`, README и
`RELEASE_NOTES.md`, затем выполните тесты и проверку QML.

После публикации тега workflow соберёт Windows и macOS артефакты и прикрепит
их к черновику GitHub Release. Тег без суффикса создаёт стабильный релиз; суффиксы
`-beta` и `-rc` — предварительный. Проверьте успешное завершение обеих сборок
и наличие ZIP/DMG, затем оформите описание из `RELEASE_NOTES.md` и опубликуйте черновик.

При переходе на 2.0 ветка `legacy/1.7` сохраняет прежний `master` на релизе
1.7.1, а QML-интерфейс переносится в `master` с сохранением истории коммитов.
