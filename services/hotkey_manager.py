"""Менеджер глобальных горячих клавиш"""

from PySide6.QtCore import QObject, Signal, Slot
from typing import Dict, Callable, Optional, List
import platform
import logging

from utils.helpers import log_exception

# Импортируем pynput только не на macOS
PYNPUT_AVAILABLE = False
keyboard = None
HotKey = None
KeyCode = None
Key = None

if platform.system() != 'Darwin':
    try:
        from pynput import keyboard
        from pynput.keyboard import HotKey, KeyCode, Key
        PYNPUT_AVAILABLE = True
    except ImportError:
        pass

logger = logging.getLogger(__name__)


class GlobalHotkeyManager(QObject):
    """
    Менеджер глобальных горячих клавиш на основе pynput.
    Работает на Windows и Linux даже когда окно не в фокусе.
    На macOS отключён из-за конфликта с Text Input Manager.
    """
    
    hotkey_triggered = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.listener = None
        self.hotkeys: Dict[str, HotKey] = {}
        self._running = False
        self._callbacks: Dict[str, Callable] = {}
    
    def _parse_key_string(self, key_str: str) -> List:
        """Преобразует строку клавиш в формат pynput"""
        key_parts = key_str.lower().replace(' ', '').split('+')
        vk_parts = []
        
        for part in key_parts:
            if part == 'ctrl':
                vk_parts.append(Key.ctrl)
            elif part == 'alt':
                vk_parts.append(Key.alt)
            elif part == 'shift':
                vk_parts.append(Key.shift)
            elif part == 'cmd' or part == 'win':
                vk_parts.append(Key.cmd)
            elif part == 'left':
                vk_parts.append(Key.left)
            elif part == 'right':
                vk_parts.append(Key.right)
            elif part == 'up':
                vk_parts.append(Key.up)
            elif part == 'down':
                vk_parts.append(Key.down)
            elif part == 'f1':
                vk_parts.append(Key.f1)
            elif part == 'f12':
                vk_parts.append(Key.f12)
            elif part == 'space':
                vk_parts.append(Key.space)
            elif part == 'enter' or part == 'return':
                vk_parts.append(Key.enter)
            elif part == 'tab':
                vk_parts.append(Key.tab)
            elif part == 'esc':
                vk_parts.append(Key.esc)
            elif len(part) == 1:
                vk_parts.append(KeyCode.from_char(part))
            else:
                try:
                    vk_parts.append(KeyCode.from_vk(int(part)))
                except ValueError:
                    logger.warning(f"Unknown key: {part}")
        
        return vk_parts
    
    def register_hotkey(self, name: str, key_str: str, callback: Optional[Callable] = None) -> bool:
        """Регистрация горячей клавиши"""
        if not PYNPUT_AVAILABLE:
            logger.warning("pynput not available")
            return False
        
        try:
            vk_parts = self._parse_key_string(key_str)
            if len(vk_parts) == 0:
                logger.error(f"Failed to parse hotkey: {key_str}")
                return False
            
            hotkey = HotKey(vk_parts, self._on_hotkey_triggered)
            self.hotkeys[name] = hotkey
            
            if callback:
                self._callbacks[name] = callback
            
            return True
        except Exception as e:
            logger.error(f"Error registering hotkey {name}: {e}", exc_info=True)
            return False
    
    def _on_hotkey_triggered(self, hotkey: HotKey) -> None:
        """Обработчик нажатия горячей клавиши"""
        for name, hk in self.hotkeys.items():
            if hk == hotkey:
                self.hotkey_triggered.emit(name)
                if name in self._callbacks:
                    try:
                        self._callbacks[name]()
                    except Exception as e:
                        log_exception(logger, f"Error in hotkey callback {name}", e)
                break
    
    @Slot()
    def start(self) -> None:
        """Запуск прослушивания горячих клавиш"""
        if not PYNPUT_AVAILABLE or self._running:
            return

        try:
            self._running = True
            self.listener = keyboard.Listener(
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
            logger.info("On macOS: System Settings -> Privacy & Security -> Accessibility")
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
        """Обработка нажатия клавиши"""
        if not self._running:
            return
        for hotkey in self.hotkeys.values():
            hotkey.press(key)
    
    def _on_release(self, key) -> None:
        """Обработка отпускания клавиши"""
        if not self._running:
            return
        for hotkey in self.hotkeys.values():
            hotkey.release(key)
    
    def clear_hotkeys(self) -> None:
        """Очистка всех зарегистрированных горячих клавиш"""
        self.hotkeys.clear()
        self._callbacks.clear()
        logger.debug("Hotkeys cleared")