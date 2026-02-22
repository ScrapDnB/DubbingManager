"""Worker threads for Dubbing Manager"""

from PySide6.QtCore import (
    Qt, QUrl, QTimer, QThread, Signal, QRectF, QEvent, Slot, QObject
)
import platform

# Попытка импорта python-osc
try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import BlockingOSCUDPServer
    from pythonosc.udp_client import SimpleUDPClient
    OSC_AVAILABLE = True
except ImportError:
    OSC_AVAILABLE = False

# Попытка импорта pynput для глобальных горячих клавиш
# На macOS pynput конфликтует с PySide6 (TSM error), поэтому отключаем
PYNPUT_AVAILABLE = False
keyboard = None
HotKey = None
KeyCode = None
Key = None

# Отключаем pynput на macOS из-за конфликта с Text Input Manager
if platform.system() != 'Darwin':
    try:
        from pynput import keyboard
        from pynput.keyboard import HotKey, KeyCode, Key
        PYNPUT_AVAILABLE = True
    except ImportError:
        pass

class OscWorker(QThread):
    time_changed = Signal(float)
    navigation_requested = Signal(str) # Передает 'next' или 'prev'
    
    def __init__(self, port=8000):
        super().__init__()
        self.port = port
        self.running = True
        self.server = None

    def run(self):
        if not OSC_AVAILABLE:
            return
        
        dispatcher = Dispatcher()
        
        # 1. Принимаем время (стандартные адреса Reaper)
        dispatcher.map("/time/seconds", self.handle_time)
        dispatcher.map("/time", self.handle_time)
        
        # 2. Принимаем навигацию через адрес имени трека (самый надежный способ обхода фильтров)
        # Мы слушаем изменение имени первого трека
        dispatcher.map("/track/1/name", self.handle_nav_via_name)
        
        # 3. Резервные прямые адреса
        dispatcher.map("/prompter/next", lambda addr, *args: self.navigation_requested.emit("next"))
        dispatcher.map("/prompter/prev", lambda addr, *args: self.navigation_requested.emit("prev"))
        
        # Логгер для отладки в консоли
        dispatcher.set_default_handler(self.debug_handler)

        try:
            self.server = BlockingOSCUDPServer(("127.0.0.1", self.port), dispatcher)
            self.server.timeout = 0.1
            while self.running:
                self.server.handle_request()
            self.server.server_close()
        except Exception as e:
            print(f"Ошибка OSC сервера: {e}")

    def debug_handler(self, address, *args):
        # Скрываем сообщения индикаторов громкости, чтобы не забивать консоль
        if "/vu" in address:
            return
        print(f"OSC Сообщение: {address} {args}")

    def handle_nav_via_name(self, address, *args):
        # Если в качестве имени трека пришло 'next' или 'prev'
        if args and isinstance(args[0], str):
            cmd = args[0].lower()
            if cmd == "next":
                print("ПОЛУЧЕНА КОМАНДА: СЛЕДУЮЩАЯ РЕПЛИКА")
                self.navigation_requested.emit("next")
            elif cmd == "prev":
                print("ПОЛУЧЕНА КОМАНДА: ПРЕДЫДУЩАЯ РЕПЛИКА")
                self.navigation_requested.emit("prev")

    def handle_time(self, address, *args):
        if args:
            try:
                self.time_changed.emit(float(args[0]))
            except:
                pass

    def stop(self):
        self.running = False

class GlobalHotkeyManager(QObject):
    """Менеджер глобальных горячих клавиш на основе pynput.
    Работает на Windows и macOS даже когда окно не в фокусе.
    """
    hotkey_triggered = Signal(str)  # Сигнал с именем горящей клавиши
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.listener = None
        self.hotkeys = {}  # {name: HotKey}
        self._running = False
        
    def _parse_key_string(self, key_str):
        """Преобразует строку клавиш в формат pynput."""
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
            elif part.isdigit():
                try:
                    vk_parts.append(KeyCode.from_vk(int(part)))
                except:
                    pass
            else:
                # Handle special keys that might be represented as strings
                special_keys = {
                    'backspace': Key.backspace,
                    'delete': Key.delete,
                    'home': Key.home,
                    'end': Key.end,
                    'page_up': Key.page_up,
                    'page_down': Key.page_down,
                    'caps_lock': Key.caps_lock,
                    'num_lock': Key.num_lock,
                    'scroll_lock': Key.scroll_lock,
                }
                if part in special_keys:
                    vk_parts.append(special_keys[part])
        
        return vk_parts
        
    def register_hotkey(self, name, key_str, callback=None):
        """Регистрация горячей клавиши."""
        if not PYNPUT_AVAILABLE:
            print("pynput не доступен")
            return False
            
        try:
            vk_parts = self._parse_key_string(key_str)
            if len(vk_parts) == 0:
                print(f"Не удалось распарсить горячую клавишу: {key_str}")
                return False
                
            hotkey = HotKey(vk_parts, self._on_hotkey_triggered)
            self.hotkeys[name] = hotkey
            
            if callback:
                self.hotkey_triggered.connect(lambda n: callback() if n == name else None)
                
            return True
        except Exception as e:
            print(f"Ошибка регистрации горячей клавиши {name}: {e}")
            return False
    
    def _on_hotkey_triggered(self, hotkey):
        """Обработчик нажатия горячей клавиши"""
        for name, hk in self.hotkeys.items():
            if hk == hotkey:
                self.hotkey_triggered.emit(name)
                break
    
    def start(self):
        """Запуск прослушивания горячих клавиш"""
        if not PYNPUT_AVAILABLE or self._running:
            return

        try:
            self._running = True
            # На macOS pynput требует прав доступа к универсальному доступу
            # Если их нет, будет исключение - ловим его и продолжаем работу без глобальных клавиш
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
                suppress=False  # Не подавляем события клавиш
            )
            self.listener.start()
            # Проверяем, что listener действительно запустился
            if not self.listener.is_alive():
                raise RuntimeError("Listener не запустился")
        except Exception as e:
            print(f"Глобальные горячие клавиши отключены: {e}")
            print("На macOS: Системные настройки -> Защита и безопасность -> Универсальный доступ")
            self._running = False
            self.listener = None
    
    def stop(self):
        """Остановка прослушивания горячих клавиш"""
        if self.listener:
            self._running = False
            self.listener.stop()
            self.listener = None
    
    def _on_press(self, key):
        """Обработка нажатия клавиши"""
        if not self._running:
            return
        for hotkey in self.hotkeys.values():
            hotkey.press(key)
    
    def _on_release(self, key):
        """Обработка отпускания клавиши"""
        if not self._running:
            return
        for hotkey in self.hotkeys.values():
            hotkey.release(key)
    
    def clear_hotkeys(self):
        """Очистка всех зарегистрированных горячих клавиш"""
        self.hotkeys.clear()