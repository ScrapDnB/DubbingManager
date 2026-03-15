# CI/CD для Dubbing Manager

## Автоматическая сборка

Этот проект использует GitHub Actions для автоматической сборки приложений для:
- **Windows** (.exe)
- **macOS** (.app + .dmg)
- **Linux** (.tar.gz + .AppImage + .deb)

## Как работает

### Триггеры сборки:

1. **Push в main/master** — сборка всех артефактов
2. **Тег версии (v*)** — сборка + публикация в GitHub Releases
3. **Pull Request** — тестовая сборка
4. **Workflow Dispatch** — ручная сборка через UI GitHub

### Артефакты:

После успешной сборки артефакты доступны:
- В разделе **Actions** → выбранная сборка → **Artifacts**
- В **Releases** (для тегов версий)

## Локальная сборка

### Windows:
```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller dubbing_manager.spec --clean
```

### macOS:
```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller dubbing_manager.spec --clean
codesign --force --deep --sign - dist/Dubbing\ Manager.app
```

### Linux:
```bash
pip install -r requirements.txt
pip install pyinstaller
sudo apt-get install libxcb-xinerama0 libxcb-cursor0
pyinstaller dubbing_manager.spec --clean
```

## Публикация релиза

```bash
# Создать тег версии
git tag v1.2.0
git push origin v1.2.0
```

GitHub Actions автоматически:
1. Соберёт приложения для всех платформ
2. Создаст релиз на GitHub
3. Прикрепит бинарники к релизу

## Структура артефактов:

| Платформа | Формат | Файл |
|-----------|--------|------|
| Windows | ZIP | `Dubbing_Manager_Windows.zip` |
| macOS | DMG | `Dubbing_Manager_macOS.dmg` |
| Linux | tar.gz | `Dubbing_Manager_Linux.tar.gz` |
| Linux | AppImage | `Dubbing_Manager_Linux.AppImage` |
| Ubuntu/Debian | DEB | `Dubbing_Manager_Ubuntu.deb` |
