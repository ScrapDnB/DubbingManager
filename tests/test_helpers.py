"""
Тесты для вспомогательных функций (helpers)

Запуск:
    pytest tests/test_helpers.py -v

Запуск с покрытием:
    pytest tests/test_helpers.py -v --cov=utils/helpers --cov-report=html
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
import json

from utils.helpers import (
    log_exception,
    ass_time_to_seconds,
    srt_time_to_seconds,
    format_seconds_to_tc,
    hex_to_rgba_string,
    split_merged_text,
    get_video_fps,
)


# =============================================================================
# Tests for log_exception
# =============================================================================

class TestLogException:
    """Тесты для функции логирования исключений"""

    def test_log_exception(self, caplog):
        """Тест логирования исключения"""
        logger = logging.getLogger("test_logger")
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            log_exception(logger, "Test message", e)

        assert "Test message" in caplog.text
        assert "Test error" in caplog.text
        assert "Traceback" in caplog.text


# =============================================================================
# Tests for ass_time_to_seconds
# =============================================================================

class TestAssTimeToSeconds:
    """Тесты для конвертации ASS времени в секунды"""

    def test_standard_format(self):
        """Тест стандартного формата времени"""
        assert ass_time_to_seconds("0:00:00.00") == 0.0
        assert ass_time_to_seconds("0:00:01.00") == 1.0
        assert ass_time_to_seconds("0:01:00.00") == 60.0
        assert ass_time_to_seconds("1:00:00.00") == 3600.0

    def test_complex_format(self):
        """Тест сложного формата времени"""
        assert ass_time_to_seconds("1:23:45.67") == 3600 + 23 * 60 + 45.67

    def test_invalid_format(self, caplog):
        """Тест невалидного формата"""
        result = ass_time_to_seconds("invalid")
        assert result == 0.0
        assert "Invalid time format" in caplog.text

    def test_none_input(self, caplog):
        """Тест None входа"""
        result = ass_time_to_seconds(None)
        assert result == 0.0


# =============================================================================
# Tests for srt_time_to_seconds
# =============================================================================

class TestSrtTimeToSeconds:
    """Тесты для конвертации SRT времени в секунды"""

    def test_standard_format(self):
        """Тест стандартного формата SRT"""
        assert srt_time_to_seconds("00:00:00,000") == 0.0
        assert srt_time_to_seconds("00:00:01,000") == 1.0
        assert srt_time_to_seconds("00:01:00,000") == 60.0
        assert srt_time_to_seconds("01:00:00,000") == 3600.0

    def test_complex_format(self):
        """Тест сложного формата"""
        expected = 3600 + 23 * 60 + 45.123
        assert srt_time_to_seconds("01:23:45,123") == expected

    def test_dot_separator(self):
        """Тест формата с точкой вместо запятой"""
        assert srt_time_to_seconds("00:00:01.500") == 1.5

    def test_invalid_format(self, caplog):
        """Тест невалидного формата"""
        result = srt_time_to_seconds("invalid")
        assert result == 0.0
        assert "Invalid SRT time format" in caplog.text


# =============================================================================
# Tests for format_seconds_to_tc
# =============================================================================

class TestFormatSecondsToTc:
    """Тесты для форматирования секунд в таймкод"""

    def test_zero_seconds(self):
        """Тест нуля секунд"""
        assert format_seconds_to_tc(0.0) == "0:00:00"

    def test_simple_seconds(self):
        """Тест простых секунд"""
        assert format_seconds_to_tc(1.0) == "0:00:01"
        assert format_seconds_to_tc(59.0) == "0:00:59"
        assert format_seconds_to_tc(60.0) == "0:01:00"
        assert format_seconds_to_tc(3600.0) == "1:00:00"

    def test_complex_time(self):
        """Тест сложного времени"""
        assert format_seconds_to_tc(3661.0) == "1:01:01"

    def test_round_flag(self):
        """Тест флага округления"""
        assert format_seconds_to_tc(1.4, round_flag=True) == "0:00:01"
        assert format_seconds_to_tc(1.6, round_flag=True) == "0:00:02"

    def test_no_round_flag(self):
        """Тест без флага округления"""
        assert format_seconds_to_tc(1.9) == "0:00:01"


# =============================================================================
# Tests for hex_to_rgba_string
# =============================================================================

class TestHexToRgbaString:
    """Тесты для конвертации HEX цвета в RGBA строку"""

    def test_valid_hex(self):
        """Тест валидного HEX цвета"""
        result = hex_to_rgba_string("#FF0000", 1.0)
        assert result == "rgba(255, 0, 0, 1.0)"

    def test_with_alpha(self):
        """Тест с прозрачностью"""
        result = hex_to_rgba_string("#00FF00", 0.5)
        assert result == "rgba(0, 255, 0, 0.5)"

    def test_invalid_hex(self):
        """Тест невалидного HEX"""
        result = hex_to_rgba_string("invalid", 1.0)
        assert result == "rgba(255, 255, 255, 1.0)"

    def test_without_hash(self):
        """Тест без символа решётки"""
        # QColor не принимает хеш без символа #, поэтому возвращается дефолтный белый
        result = hex_to_rgba_string("FF0000", 1.0)
        assert result == "rgba(255, 255, 255, 1.0)"  # Дефолтное значение для невалидного


# =============================================================================
# Tests for split_merged_text
# =============================================================================

class TestSplitMergedText:
    """Тесты для разделения объединённого текста"""

    def test_split_by_double_slash(self):
        """Тест разделения по ' // '"""
        text = "Part 1 // Part 2 // Part 3"
        ids = [1, 2, 3]
        result = split_merged_text(text, ids)
        assert result == ["Part 1", "Part 2", "Part 3"]

    def test_split_by_single_slash(self):
        """Тест разделения по ' / '"""
        text = "Part 1 / Part 2 / Part 3"
        ids = [1, 2, 3]
        result = split_merged_text(text, ids)
        assert result == ["Part 1", "Part 2", "Part 3"]

    def test_empty_text(self):
        """Тест пустого текста"""
        result = split_merged_text("", [1, 2])
        assert result == []

    def test_none_text(self):
        """Тест None текста"""
        result = split_merged_text(None, [1, 2])
        assert result == []

    def test_mismatch_count(self):
        """Тест несовпадения количества частей"""
        text = "Part 1 // Part 2"
        ids = [1, 2, 3]
        result = split_merged_text(text, ids)
        assert result == []

    def test_single_part(self):
        """Тест одной части"""
        text = "Single part"
        ids = [1]
        result = split_merged_text(text, ids)
        assert result == []


# =============================================================================
# Tests for get_video_fps
# =============================================================================

class TestGetVideoFps:
    """Тесты для получения FPS из видео"""

    @patch('utils.helpers.subprocess.run')
    def test_valid_video(self, mock_run):
        """Тест валидного видео"""
        mock_data = {
            'streams': [{
                'codec_type': 'video',
                'avg_frame_rate': '30000/1001'
            }]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_data)
        )

        # Тест с моком Path.exists и Path.is_file
        def mock_path_factory(path_str):
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.is_file.return_value = True
            mock_path.stat.return_value.st_mtime = 12345
            mock_path.resolve.return_value = mock_path
            mock_path.__str__ = lambda self: path_str
            return mock_path
            
        with patch('utils.helpers.Path', side_effect=mock_path_factory):
            result = get_video_fps("/path/to/video.mp4")
        assert abs(result - 29.97) < 0.01

    @patch('utils.helpers.subprocess.run')
    def test_r_frame_rate(self, mock_run):
        """Тест r_frame_rate"""
        mock_data = {
            'streams': [{
                'codec_type': 'video',
                'r_frame_rate': '25/1'
            }]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_data)
        )

        def mock_path_factory(path_str):
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.is_file.return_value = True
            mock_path.resolve.return_value = mock_path
            mock_path.__str__ = lambda self: path_str
            return mock_path
            
        with patch('utils.helpers.Path', side_effect=mock_path_factory):
            result = get_video_fps("/path/to/video.mp4")
        assert result == 25.0

    @patch('utils.helpers.subprocess.run')
    def test_ffprobe_not_found(self, mock_run):
        """Тест отсутствия ffprobe"""
        mock_run.side_effect = FileNotFoundError("ffprobe not found")
        
        result = get_video_fps("/path/to/video.mp4")
        assert result == 25.0

    @patch('utils.helpers.subprocess.run')
    def test_ffprobe_error(self, mock_run):
        """Тест ошибки ffprobe"""
        mock_run.return_value = MagicMock(returncode=1)
        
        result = get_video_fps("/path/to/video.mp4")
        assert result == 25.0

    @patch('utils.helpers.subprocess.run')
    def test_timeout(self, mock_run):
        """Тест таймаута"""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("ffprobe", 10)
        
        result = get_video_fps("/path/to/video.mp4")
        assert result == 25.0

    @patch('utils.helpers.subprocess.run')
    def test_invalid_json(self, mock_run):
        """Тест невалидного JSON"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="invalid json"
        )
        
        result = get_video_fps("/path/to/video.mp4")
        assert result == 25.0

    @patch('utils.helpers.subprocess.run')
    def test_no_video_stream(self, mock_run):
        """Тест отсутствия видеопотока"""
        mock_data = {
            'streams': [{
                'codec_type': 'audio'
            }]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_data)
        )
        
        result = get_video_fps("/path/to/video.mp4")
        assert result == 25.0

    @patch('utils.helpers.subprocess.run')
    def test_zero_denominator(self, mock_run):
        """Тест нулевого знаменателя"""
        mock_data = {
            'streams': [{
                'codec_type': 'video',
                'avg_frame_rate': '30/0'
            }]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_data)
        )

        result = get_video_fps("/path/to/video.mp4")
        assert result == 25.0

    @patch('utils.helpers.subprocess.run')
    def test_path_traversal_blocked(self, mock_run):
        """Тест блокировки path traversal"""
        result = get_video_fps("../etc/passwd")
        
        assert result == 25.0
        mock_run.assert_not_called()

    @patch('utils.helpers.subprocess.run')
    def test_file_not_exists(self, mock_run):
        """Тест несуществующего файла"""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_instance.is_file.return_value = False
        mock_path_instance.resolve.return_value = mock_path_instance
        
        with patch('utils.helpers.Path', return_value=mock_path_instance):
            result = get_video_fps("/nonexistent.mp4")
        
        assert result == 25.0
        mock_run.assert_not_called()

    @patch('utils.helpers.subprocess.run')
    def test_is_file_false(self, mock_run):
        """Тест когда путь не файл"""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = False
        mock_path_instance.resolve.return_value = mock_path_instance
        
        with patch('utils.helpers.Path', return_value=mock_path_instance):
            result = get_video_fps("/directory/")
        
        assert result == 25.0
        mock_run.assert_not_called()
