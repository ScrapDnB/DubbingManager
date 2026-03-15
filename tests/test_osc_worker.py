"""Тесты для osc_worker.py"""

import pytest
from unittest.mock import patch, MagicMock, call

from services.osc_worker import OscWorker, OSC_AVAILABLE


class TestOscWorker:
    """Тесты для OscWorker"""

    @pytest.fixture
    def worker(self):
        """Worker для тестов"""
        return OscWorker(port=8000)

    def test_init_default_values(self, worker):
        """Тест значений по умолчанию"""
        assert worker.port == 8000
        assert worker.running == True
        assert worker.server is None

    def test_init_custom_port(self):
        """Тест пользовательского порта"""
        worker = OscWorker(port=9000)
        assert worker.port == 9000

    @pytest.mark.skipif(not OSC_AVAILABLE, reason="python-osc not installed")
    def test_run_with_osc(self, worker):
        """Тест запуска с OSC"""
        with patch.object(worker, '_setup_dispatcher') as mock_setup:
            mock_server = MagicMock()
            mock_setup.return_value = mock_server
            
            with patch.object(worker, '_start_server') as mock_start:
                worker.run()
                
                mock_setup.assert_called_once()
                mock_start.assert_called_once_with(mock_setup.return_value)

    @pytest.mark.skipif(OSC_AVAILABLE, reason="python-osc installed")
    def test_run_without_osc(self, worker):
        """Тест запуска без OSC"""
        # Не должно вызывать исключение
        worker.run()

    @pytest.mark.skipif(not OSC_AVAILABLE, reason="python-osc not installed")
    def test_setup_dispatcher(self, worker):
        """Тест настройки диспетчера"""
        from pythonosc.dispatcher import Dispatcher
        
        dispatcher = worker._setup_dispatcher()
        
        assert isinstance(dispatcher, Dispatcher)

    def test_debug_handler_vu(self, worker, caplog):
        """Тест отладочного обработчика (игнорирует VU)"""
        worker._debug_handler("/track/1/vu", 0.5)
        
        # Не должно логировать VU
        assert "OSC Message" not in caplog.text

    def test_stop(self, worker):
        """Тест остановки"""
        mock_server = MagicMock()
        worker.server = mock_server
        
        worker.stop()
        
        assert worker.running == False
        mock_server.server_close.assert_called()

    def test_stop_no_server(self, worker):
        """Тест остановки без сервера"""
        worker.server = None
        
        # Не должно вызывать исключение
        worker.stop()

    def test_stop_server_error(self, worker):
        """Тест ошибки при остановке сервера"""
        mock_server = MagicMock()
        mock_server.server_close.side_effect = Exception("Error")
        worker.server = mock_server
        
        # Не должно вызывать исключение
        worker.stop()

    def test_run_exception(self, worker, caplog):
        """Тест исключения в run"""
        with patch.object(worker, '_setup_dispatcher', side_effect=Exception("Error")):
            worker.run()
            
            assert "OSC server error" in caplog.text

    @pytest.mark.skipif(not OSC_AVAILABLE, reason="python-osc not installed")
    def test_start_server(self, worker):
        """Тест запуска сервера"""
        from pythonosc.dispatcher import Dispatcher
        
        dispatcher = Dispatcher()
        
        # Мокируем сервер
        mock_server = MagicMock()
        mock_server.timeout = 0.1
        
        def stop_after_call(*args):
            worker.running = False
            
        mock_server.handle_request.side_effect = stop_after_call
        
        with patch('services.osc_worker.BlockingOSCUDPServer', return_value=mock_server):
            worker._start_server(dispatcher)
            
            assert worker.server is not None


class TestOscWorkerNoOsc:
    """Тесты когда python-osc не установлен"""

    def test_osc_not_available(self):
        """Тест флага доступности"""
        if not OSC_AVAILABLE:
            worker = OscWorker()
            assert worker is not None
