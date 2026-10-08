"""OSC worker for Reaper synchronization."""

from PySide6.QtCore import QThread, Signal, Slot
from typing import Optional
import logging

try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import BlockingOSCUDPServer
    from pythonosc.udp_client import SimpleUDPClient
    OSC_AVAILABLE = True
except ImportError:
    OSC_AVAILABLE = False

logger = logging.getLogger(__name__)


class OscWorker(QThread):
    """Osc Worker class."""
    
    time_changed = Signal(float)
    transport_playing_changed = Signal(bool)
    error_occurred = Signal(object, str)
    
    def __init__(self, port: int = 8000, parent=None):
        super().__init__(parent)
        self.port = port
        self.running = True
        self.server: Optional[BlockingOSCUDPServer] = None
    
    def run(self) -> None:
        if not OSC_AVAILABLE:
            logger.warning("OSC not available - python-osc not installed")
            return
        
        try:
            dispatcher = self._setup_dispatcher()
            self._start_server(dispatcher)
        except Exception as exc:
            logger.error("OSC server error: %s", exc, exc_info=True)
            self.error_occurred.emit(self, str(exc))
    
    def _setup_dispatcher(self) -> Dispatcher:
        dispatcher = Dispatcher()
        
        # Receive time from standard Reaper addresses
        dispatcher.map("/time/seconds", self._handle_time)
        dispatcher.map("/time", self._handle_time)
        dispatcher.map("/play", self._handle_play)
        dispatcher.map("/stop", self._handle_stop_or_pause)
        dispatcher.map("/pause", self._handle_stop_or_pause)
        
        # Debug logger
        dispatcher.set_default_handler(self._debug_handler)
        
        return dispatcher
    
    def _start_server(self, dispatcher: Dispatcher) -> None:
        self.server = BlockingOSCUDPServer(("127.0.0.1", self.port), dispatcher)
        self.server.timeout = 0.1
        
        while self.running:
            self.server.handle_request()
        
        if self.server:
            self.server.server_close()
    
    def _debug_handler(self, address: str, *args) -> None:
        # Hide volume-meter messages
        if "/vu" in address:
            return
        logger.debug(f"OSC Message: {address} {args}")
    
    def _handle_time(self, address: str, *args) -> None:
        if args:
            try:
                self.time_changed.emit(float(args[0]))
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid time value: {args[0]}, error: {e}")

    @staticmethod
    def _osc_bool(args, default: bool) -> bool:
        if not args:
            return default
        value = args[0]
        if isinstance(value, str):
            return value.strip().lower() not in {"", "0", "false", "off"}
        return bool(value)

    def _handle_play(self, address: str, *args) -> None:
        self.transport_playing_changed.emit(self._osc_bool(args, True))

    def _handle_stop_or_pause(self, address: str, *args) -> None:
        if self._osc_bool(args, True):
            self.transport_playing_changed.emit(False)
    
    @Slot()
    def stop(self) -> None:
        """Stop the OSC server."""
        self.running = False
        if self.server:
            try:
                self.server.server_close()
            except Exception as e:
                logger.warning(f"Error closing OSC server: {e}")
        self.wait(1000)  # Wait for the thread to finish
