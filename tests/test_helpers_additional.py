"""Дополнительные тесты для helpers.py"""

import pytest
import json
from unittest.mock import patch, MagicMock

from utils.helpers import (
    log_exception,
    ass_time_to_seconds,
    srt_time_to_seconds,
    format_seconds_to_tc,
    format_seconds_to_full_tc,
    format_timing_range,
    hex_to_rgba_string,
    split_merged_text,
    get_video_fps,
    FPS,
)


class TestLogException:
    """Тесты для log_exception"""

    def test_log_exception(self, caplog):
        """Тест логирования исключения"""
        logger = MagicMock()
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            log_exception(logger, "Test message", e)
        
        logger.error.assert_called()
        assert "Test message" in logger.error.call_args[0][0]
        assert "Test error" in logger.error.call_args[0][0]
        assert "Traceback" in logger.error.call_args[0][0]


class TestAssTimeToSeconds:
    """Тесты для ass_time_to_seconds"""

    def test_valid_time(self):
        """Тест валидного времени"""
        result = ass_time_to_seconds("0:01:30.500")
        assert result == 90.5

    def test_zero_time(self):
        """Тест нулевого времени"""
        result = ass_time_to_seconds("0:00:00.000")
        assert result == 0.0

    def test_hour_time(self):
        """Тест времени с часами"""
        result = ass_time_to_seconds("1:30:00.000")
        assert result == 5400.0

    def test_invalid_format(self, caplog):
        """Тест невалидного формата"""
        result = ass_time_to_seconds("invalid")
        assert result == 0.0
        assert "Invalid time format" in caplog.text

    def test_empty_string(self, caplog):
        """Тест пустой строки"""
        result = ass_time_to_seconds("")
        assert result == 0.0

    def test_none_value(self, caplog):
        """Тест None значения"""
        result = ass_time_to_seconds(None)
        assert result == 0.0


class TestSrtTimeToSeconds:
    """Тесты для srt_time_to_seconds"""

    def test_valid_time(self):
        """Тест валидного времени"""
        result = srt_time_to_seconds("00:01:30,500")
        assert result == 90.5

    def test_zero_time(self):
        """Тест нулевого времени"""
        result = srt_time_to_seconds("00:00:00,000")
        assert result == 0.0

    def test_hour_time(self):
        """Тест времени с часами"""
        result = srt_time_to_seconds("01:30:00,000")
        assert result == 5400.0

    def test_invalid_format(self, caplog):
        """Тест невалидного формата"""
        result = srt_time_to_seconds("invalid")
        assert result == 0.0
        assert "Invalid SRT time format" in caplog.text

    def test_empty_string(self, caplog):
        """Тест пустой строки"""
        result = srt_time_to_seconds("")
        assert result == 0.0

    def test_none_value(self, caplog):
        """Тест None значения"""
        result = srt_time_to_seconds(None)
        assert result == 0.0


class TestFormatSecondsToTc:
    """Тесты для format_seconds_to_tc"""

    def test_basic_time(self):
        """Тест базового времени"""
        result = format_seconds_to_tc(90)
        assert result == "0:01:30"

    def test_zero_time(self):
        """Тест нулевого времени"""
        result = format_seconds_to_tc(0)
        assert result == "0:00:00"

    def test_hour_time(self):
        """Тест времени с часами"""
        result = format_seconds_to_tc(3661)
        assert result == "1:01:01"

    def test_round_flag(self):
        """Тест округления"""
        result = format_seconds_to_tc(90.7, round_flag=True)
        assert result == "0:01:31"

    def test_no_round_flag(self):
        """Тест без округления"""
        result = format_seconds_to_tc(90.7)
        assert result == "0:01:30"


class TestFormatSecondsToFullTc:
    """Тесты для format_seconds_to_full_tc"""

    def test_basic_time(self):
        """Тест базового времени"""
        result = format_seconds_to_full_tc(90.5)
        assert result == "0:01:30,500"

    def test_zero_time(self):
        """Тест нулевого времени"""
        result = format_seconds_to_full_tc(0)
        assert result == "0:00:00,000"

    def test_milliseconds(self):
        """Тест миллисекунд"""
        result = format_seconds_to_full_tc(1.123)
        assert result == "0:00:01,123"

    def test_hours(self):
        """Тест часов"""
        result = format_seconds_to_full_tc(3661.5)
        assert result == "1:01:01,500"


class TestFormatTimingRange:
    """Тесты для format_timing_range"""

    def test_basic_range(self):
        """Тест базового диапазона"""
        result = format_timing_range(0.0, 2.5)
        assert result == "0:00:00,000-0:00:02,500"

    def test_hour_range(self):
        """Тест диапазона с часами"""
        result = format_timing_range(3600.0, 3602.5)
        assert result == "1:00:00,000-1:00:02,500"


class TestHexToRgbaString:
    """Тесты для hex_to_rgba_string"""

    def test_valid_hex(self):
        """Тест валидного HEX"""
        result = hex_to_rgba_string("#FF0000", 0.5)
        assert "rgba(255, 0, 0, 0.5)" == result

    def test_invalid_hex(self):
        """Тест невалидного HEX"""
        result = hex_to_rgba_string("invalid", 0.5)
        assert "rgba(255, 255, 255, 0.5)" == result

    def test_lowercase_hex(self):
        """Тест HEX в нижнем регистре"""
        result = hex_to_rgba_string("#ff0000", 0.5)
        assert "rgba(255, 0, 0, 0.5)" == result


class TestSplitMergedText:
    """Тесты для split_merged_text"""

    def test_split_with_double_slash(self):
        """Тест разделения с //"""
        result = split_merged_text("First // Second", [1, 2])
        assert result == ["First", "Second"]

    def test_split_with_single_slash(self):
        """Тест разделения с /"""
        result = split_merged_text("First / Second", [1, 2])
        assert result == ["First", "Second"]

    def test_split_no_separator(self):
        """Тест без разделителя"""
        result = split_merged_text("First Second", [1, 2])
        assert result == []

    def test_split_empty_text(self):
        """Тест пустого текста"""
        result = split_merged_text("", [1, 2])
        assert result == []

    def test_split_single_id(self):
        """Тест с одним ID"""
        result = split_merged_text("First // Second", [1])
        assert result == []

    def test_split_mismatch_count(self):
        """Тест несовпадения количества"""
        result = split_merged_text("First // Second // Third", [1, 2])
        assert result == []


class TestGetVideoFpsAdditional:
    """Дополнительные тесты для get_video_fps"""

    @patch('utils.helpers.subprocess.run')
    def test_r_frame_rate_fallback(self, mock_run):
        """Тест fallback на r_frame_rate"""
        mock_data = {
            'streams': [{
                'codec_type': 'video',
                'r_frame_rate': '30/1'
            }]
        }
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_data))
        
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = True
        mock_path_instance.resolve.return_value = mock_path_instance
        
        with patch('utils.helpers.Path', return_value=mock_path_instance):
            result = get_video_fps("/path/to/video.mp4")
        
        assert result == 30.0

    @patch('utils.helpers.subprocess.run')
    def test_avg_fps_fallback(self, mock_run):
        """Тест fallback на avg_fps"""
        mock_data = {
            'streams': [{
                'codec_type': 'video',
                'avg_frame_rate': '25/1'
            }]
        }
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_data))
        
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = True
        mock_path_instance.resolve.return_value = mock_path_instance
        
        with patch('utils.helpers.Path', return_value=mock_path_instance):
            result = get_video_fps("/path/to/video.mp4")
        
        assert result == 25.0

    @patch('utils.helpers.subprocess.run')
    def test_returncode_nonzero(self, mock_run):
        """Тест ненулевого returncode"""
        mock_run.return_value = MagicMock(returncode=1)
        
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = True
        mock_path_instance.resolve.return_value = mock_path_instance
        
        with patch('utils.helpers.Path', return_value=mock_path_instance):
            result = get_video_fps("/path/to/video.mp4")
        
        assert result == 25.0

    @patch('utils.helpers.subprocess.run')
    def test_no_streams(self, mock_run):
        """Тест без потоков"""
        mock_data = {'streams': []}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_data))
        
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_file.return_value = True
        mock_path_instance.resolve.return_value = mock_path_instance
        
        with patch('utils.helpers.Path', return_value=mock_path_instance):
            result = get_video_fps("/path/to/video.mp4")
        
        assert result == 25.0

    @patch('utils.helpers.subprocess.run')
    def test_exception_handling(self, mock_run):
        """Тест обработки исключений"""
        mock_run.side_effect = Exception("Unexpected error")
        
        result = get_video_fps("/path/to/video.mp4")
        
        assert result == 25.0
