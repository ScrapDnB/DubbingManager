"""Менеджер глобальных горячих клавиш"""

from PySide6.QtCore import QObject, Signal, Slot
from typing import Dict, Callable, Optional, List, TYPE_CHECKING
import platform
import logging

from utils.helpers import log_exception

logger = logging.getLogger(__name__)

# Проверка доступности pynput (не на macOS)
PYNPUT_AVAILABLE = False

if platform.system() != 'Darwin':
    try:
        from pynput import keyboard
        from pynput.keyboard import HotKey, KeyCode, Key
        PYNPUT_AVAILABLE = True
    except ImportError:
        pass


class GlobalHotkeyManager(QObject):
    """
    Менеджер глобальных горячих клавиш на основе pynput.
    
    Работает на Windows и Linux даже когда окно не в фокусе.
    На macOS отключён из-за конфликта с Text Input Manager.
    
    Attributes:
        hotkey_triggered: Сигнал с именем нажатой горячей клавиши
    """

    hotkey_triggered = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Состояние
        self.listener = None
        self._running = False
        
        # Зарегистрированные горячие клавиши и колбэки
        self.hotkeys: Dict[str, 'HotKey'] = {}
        self._callbacks: Dict[str, Callable] = {}
        
        # Модули pynput (инициализируются только если доступны)
        self._keyboard = None
        self._HotKey = None
        self._KeyCode = None
        self._Key = None
        
        # Инициализируем pynput если доступен
        if PYNPUT_AVAILABLE:
            self._init_pynput()

    def _init_pynput(self) -> None:
        """Инициализация модулей pynput"""
        try:
            from pynput import keyboard
            from pynput.keyboard import HotKey, KeyCode, Key
            
            self._keyboard = keyboard
            self._HotKey = HotKey
            self._KeyCode = KeyCode
            self._Key = Key
            
            logger.debug("pynput initialized successfully")
        except Exception as e:
            log_exception(logger, "Failed to initialize pynput", e)
            PYNPUT_AVAILABLE = False

    def _parse_key_string(self, key_str: str) -> List:
        """
        Преобразует строку клавиш в формат pynput.
        
        Args:
            key_str: Строка вида "Ctrl+Shift+A" или "Left"
            
        Returns:
            Список объектов KeyCode/Key
        """
        if not PYNPUT_AVAILABLE or not self._KeyCode or not self._Key:
            return []
            
        key_parts = key_str.lower().replace(' ', '').split('+')
        vk_parts = []

        for part in key_parts:
            if part == 'ctrl':
                vk_parts.append(self._Key.ctrl)
            elif part == 'alt':
                vk_parts.append(self._Key.alt)
            elif part == 'shift':
                vk_parts.append(self._Key.shift)
            elif part == 'cmd' or part == 'win':
                vk_parts.append(self._Key.cmd)
            elif part == 'left':
                vk_parts.append(self._Key.left)
            elif part == 'right':
                vk_parts.append(self._Key.right)
            elif part == 'up':
                vk_parts.append(self._Key.up)
            elif part == 'down':
                vk_parts.append(self._Key.down)
            elif part == 'f1':
                vk_parts.append(self._Key.f1)
            elif part == 'f12':
                vk_parts.append(self._Key.f12)
            elif part == 'space':
                vk_parts.append(self._Key.space)
            elif part == 'enter' or part == 'return':
                vk_parts.append(self._Key.enter)
            elif part == 'tab':
                vk_parts.append(self._Key.tab)
            elif part == 'esc':
                vk_parts.append(self._Key.esc)
            elif len(part) == 1:
                vk_parts.append(self._KeyCode.from_char(part))
            else:
                try:
                    vk_parts.append(self._KeyCode.from_vk(int(part)))
                except ValueError:
                    logger.warning(f"Unknown key: {part}")

        return vk_parts

    def register_hotkey(
        self,
        name: str,
        key_str: str,
        callback: Optional[Callable] = None
    ) -> bool:
        """
        Регистрация горячей клавиши.
        
        Args:
            name: Имя горячей клавиши для идентификации
            key_str: Строка клавиш (например, "Ctrl+Shift+S")
            callback: Функция для вызова при нажатии
            
        Returns:
            True если регистрация успешна
        """
        if not PYNPUT_AVAILABLE:
            logger.warning("pynput not available")
            return False

        try:
            vk_parts = self._parse_key_string(key_str)
            if len(vk_parts) == 0:
                logger.error(f"Failed to parse hotkey: {key_str}")
                return False

            if not self._HotKey:
                logger.error("HotKey class not available")
                return False
                
            hotkey = self._HotKey(vk_parts, self._on_hotkey_triggered)
            self.hotkeys[name] = hotkey

            if callback:
                self._callbacks[name] = callback

            logger.debug(f"Registered hotkey '{name}': {key_str}")
            return True
            
        except Exception as e:
            log_exception(logger, f"Error registering hotkey '{name}'", e)
            return False

    def _on_hotkey_triggered(self, hotkey: 'HotKey') -> None:
        """
        Обработчик нажатия горячей клавиши.
        
        Args:
            hotkey: Объект нажатой горячей клавиши
        """
        for name, hk in self.hotkeys.items():
            if hk == hotkey:
                self.hotkey_triggered.emit(name)
                if name in self._callbacks:
                    try:
                        self._callbacks[name]()
                    except Exception as e:
                        log_exception(logger, f"Error in hotkey callback '{name}'", e)
                break

    @Slot()
    def start(self) -> None:
        """Запуск прослушивания горячих клавиш"""
        if not PYNPUT_AVAILABLE or self._running:
            return

        try:
            self._running = True
            
            if not self._keyboard:
                logger.error("Keyboard module not available")
                return
            
            self.listener = self._keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
                suppress=False
            )
            self.listener.start()

            if not self.listener.is_alive():
                raise RuntimeError("Listener did not start")

            logger.info("Global hotkey listener started")
            
        except Exception as e:
            log_exception(logger, "Global hotkeys disabled", e)
            logger.info(
                "On macOS: System Settings -> Privacy & Security -> Accessibility"
            )
            self._running = False
            self.listener = None

    @Slot()
    def stop(self) -> None:
        """Остановка прослушивания горячих клавиш"""
        if self.listener:
            self._running = False
            self.listener.stop()
            self.listener = None
            logger.info("Global hotkey listener stopped")

    def _on_press(self, key) -> None:
        """
        Обработка нажатия клавиши.
        
        Args:
            key: Объект нажатой клавиши
        """
        if not self._running:
            return
        for hotkey in self.hotkeys.values():
            hotkey.press(key)

    def _on_release(self, key) -> None:
        """
        Обработка отпускания клавиши.
        
        Args:
            key: Объект отпущенной клавиши
        """
        if not self._running:
            return
        for hotkey in self.hotkeys.values():
            hotkey.release(key)

    def clear_hotkeys(self) -> None:
        """Очистка всех зарегистрированных горячих клавиш"""
        self.hotkeys.clear()
        self._callbacks.clear()
        logger.debug("Hotkeys cleared")

    def is_available(self) -> bool:
        """
        Проверка доступности горячих клавиш.
        
        Returns:
            True если pynput доступен и работает
        """
        return PYNPUT_AVAILABLE and self._keyboard is not None

    def is_running(self) -> bool:
        """
        Проверка состояния прослушивания.
        
        Returns:
            True если слушатель запущен
        """
        return self._running
