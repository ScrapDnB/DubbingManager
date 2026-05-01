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
    navigation_requested = Signal(str)
    
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
        except Exception as e:
            logger.error(f"OSC server error: {e}", exc_info=True)
    
    def _setup_dispatcher(self) -> Dispatcher:
        dispatcher = Dispatcher()
        
        # Receive time from standard Reaper addresses
        dispatcher.map("/time/seconds", self._handle_time)
        dispatcher.map("/time", self._handle_time)
        
        # Receive navigation through the track-name address
        dispatcher.map("/track/1/name", self._handle_nav_via_name)
        
        # Fallback direct addresses
        dispatcher.map("/prompter/next", lambda addr, *args: self.navigation_requested.emit("next"))
        dispatcher.map("/prompter/prev", lambda addr, *args: self.navigation_requested.emit("prev"))
        
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
    
    def _handle_nav_via_name(self, address: str, *args) -> None:
        if args and isinstance(args[0], str):
            cmd = args[0].lower().strip()
            if cmd == "next":
                logger.info("OSC: Next command received")
                self.navigation_requested.emit("next")
            elif cmd == "prev":
                logger.info("OSC: Prev command received")
                self.navigation_requested.emit("prev")
    
    def _handle_time(self, address: str, *args) -> None:
        if args:
            try:
                self.time_changed.emit(float(args[0]))
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid time value: {args[0]}, error: {e}")
    
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