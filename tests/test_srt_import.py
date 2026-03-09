"""Tests for SRT file import functionality"""

import os
import tempfile
import pytest
from services.episode_service import EpisodeService
from utils.helpers import get_video_fps


class TestSrtImport:
    """Tests for SRT file parsing and loading"""

    def setup_method(self):
        """Setup test fixtures"""
        self.episode_service = EpisodeService(merge_gap=5, fps=25.0)

    def test_parse_srt_file_basic(self):
        """Test parsing basic SRT file"""
        srt_content = """1
00:00:01,000 --> 00:00:04,000
John: Hello, how are you?

2
00:00:05,000 --> 00:00:08,000
Mary: I'm fine, thank you!

3
00:00:09,000 --> 00:00:12,000
John: That's good to hear.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            stats, lines = self.episode_service.parse_srt_file(temp_path)
            
            # Check lines
            assert len(lines) == 3
            
            # Check first line
            assert lines[0]['char'] == 'John'
            assert lines[0]['text'] == 'Hello, how are you?'
            assert lines[0]['s'] == 1.0
            assert lines[0]['e'] == 4.0
            
            # Check second line
            assert lines[1]['char'] == 'Mary'
            assert lines[1]['text'] == "I'm fine, thank you!"
            
            # Check stats
            assert len(stats) == 2  # John and Mary
            
            john_stats = next(s for s in stats if s['name'] == 'John')
            assert john_stats['lines'] == 2
            
            mary_stats = next(s for s in stats if s['name'] == 'Mary')
            assert mary_stats['lines'] == 1
            
        finally:
            os.unlink(temp_path)

    def test_parse_srt_file_without_character_name(self):
        """Test parsing SRT file without character name prefix"""
        srt_content = """1
00:00:01,000 --> 00:00:04,000
Hello, how are you?

2
00:00:05,000 --> 00:00:08,000
I'm fine, thank you!
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            stats, lines = self.episode_service.parse_srt_file(temp_path)
            
            # Check lines - character should be empty
            assert len(lines) == 2
            assert lines[0]['char'] == ''
            assert lines[0]['text'] == 'Hello, how are you?'
            
        finally:
            os.unlink(temp_path)

    def test_parse_srt_file_multiline_text(self):
        """Test parsing SRT file with multiline text"""
        srt_content = """1
00:00:01,000 --> 00:00:04,000
John: This is a multiline
replica that spans
multiple lines.

2
00:00:05,000 --> 00:00:08,000
Mary: Single line response.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            stats, lines = self.episode_service.parse_srt_file(temp_path)
            
            assert len(lines) == 2
            # Multiline text should be preserved
            assert 'multiline' in lines[0]['text']
            assert lines[0]['char'] == 'John'
            
        finally:
            os.unlink(temp_path)

    def test_parse_srt_file_rings_calculation(self):
        """Test that rings are calculated correctly for SRT files"""
        # Create SRT with gaps that should trigger ring splits
        # merge_gap = 5 frames / 25 fps = 0.2 seconds
        srt_content = """1
00:00:01,000 --> 00:00:02,000
John: First line.

2
00:00:02,100 --> 00:00:03,000
John: Second line (close gap - 0.1s).

3
00:00:10,000 --> 00:00:11,000
John: Third line (large gap - new ring).
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            stats, lines = self.episode_service.parse_srt_file(temp_path)
            
            assert len(lines) == 3
            john_stats = next(s for s in stats if s['name'] == 'John')
            
            # Gap between 1 and 2 is 0.1s (< 0.2s merge_gap) - same ring
            # Gap between 2 and 3 is 7s (> 0.2s merge_gap) - new ring
            # So we should have 2 rings: (1,2) and (3)
            assert john_stats['rings'] == 2
            
        finally:
            os.unlink(temp_path)

    def test_load_srt_episode(self):
        """Test loading SRT episode"""
        srt_content = """1
00:00:01,000 --> 00:00:04,000
John: Hello.

2
00:00:05,000 --> 00:00:08,000
Mary: Hi there.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            episodes = {"1": temp_path}
            lines = self.episode_service.load_srt_episode("1", episodes)
            
            assert len(lines) == 2
            assert lines[0]['id'] == 0
            assert lines[0]['char'] == 'John'
            assert lines[1]['char'] == 'Mary'
            
            # Test caching
            cached_lines = self.episode_service.load_srt_episode("1", episodes)
            assert cached_lines is lines  # Same object from cache
            
        finally:
            os.unlink(temp_path)

    def test_srt_time_conversion(self):
        """Test SRT time conversion to seconds"""
        from utils.helpers import srt_time_to_seconds
        
        # Test various time formats
        assert srt_time_to_seconds("00:00:01,000") == 1.0
        assert srt_time_to_seconds("00:01:30,500") == 90.5
        assert srt_time_to_seconds("01:00:00,000") == 3600.0
        assert srt_time_to_seconds("00:00:00,000") == 0.0
        
        # Test invalid format
        assert srt_time_to_seconds("invalid") == 0.0

    def test_parse_srt_with_colon_in_text(self):
        """Test parsing SRT where text contains colons"""
        srt_content = """1
00:00:01,000 --> 00:00:04,000
John: Time is: 10:30 AM.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            stats, lines = self.episode_service.parse_srt_file(temp_path)
            
            assert len(lines) == 1
            assert lines[0]['char'] == 'John'
            # Text after first colon should be preserved
            assert lines[0]['text'] == 'Time is: 10:30 AM.'

        finally:
            os.unlink(temp_path)


class TestEpisodeServiceFps:
    """Tests for EpisodeService FPS functionality"""

    def test_episode_service_default_fps(self):
        """Test EpisodeService uses default FPS of 25.0"""
        service = EpisodeService()
        assert service.fps == 25.0

    def test_episode_service_custom_fps(self):
        """Test EpisodeService accepts custom FPS"""
        service = EpisodeService(merge_gap=5, fps=30.0)
        assert service.fps == 30.0

    def test_episode_service_set_fps(self):
        """Test EpisodeService.set_fps() method"""
        service = EpisodeService()
        service.set_fps(23.976)
        assert service.fps == 23.976

    def test_episode_service_rings_with_different_fps(self):
        """Test ring calculation with different FPS values"""
        # With 25 FPS, merge_gap=5 means 0.2 seconds
        service_25 = EpisodeService(merge_gap=5, fps=25.0)
        
        # With 50 FPS, merge_gap=5 means 0.1 seconds
        service_50 = EpisodeService(merge_gap=5, fps=50.0)
        
        srt_content = """1
00:00:01,000 --> 00:00:02,000
John: First line.

2
00:00:02,150 --> 00:00:03,000
John: Second line (0.15s gap).
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            # With 25 FPS (0.2s threshold), gap of 0.15s should be same ring
            stats_25, _ = service_25.parse_srt_file(temp_path)
            john_25 = next(s for s in stats_25 if s['name'] == 'John')
            assert john_25['rings'] == 1
            
            # With 50 FPS (0.1s threshold), gap of 0.15s should be different ring
            stats_50, _ = service_50.parse_srt_file(temp_path)
            john_50 = next(s for s in stats_50 if s['name'] == 'John')
            assert john_50['rings'] == 2
            
        finally:
            os.unlink(temp_path)

    def test_set_merge_gap_from_config_with_fps(self):
        """Test set_merge_gap_from_config updates FPS"""
        service = EpisodeService()
        config = {'merge_gap': 10, 'fps': 30.0}
        service.set_merge_gap_from_config(config)
        assert service.merge_gap == 10
        assert service.fps == 30.0

    def test_get_video_fps_default_fallback(self):
        """Test get_video_fps returns default FPS for non-existent file"""
        fps = get_video_fps("/nonexistent/path/video.mp4")
        assert fps == 25  # Default FPS from constants


class TestSrtSave:
    """Tests for SRT file saving functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.episode_service = EpisodeService(merge_gap=5, fps=25.0)

    def test_save_episode_to_srt(self):
        """Test saving edited SRT episode"""
        srt_content = """1
00:00:01,000 --> 00:00:04,000
John: Hello, how are you?

2
00:00:05,000 --> 00:00:08,000
Mary: I'm fine, thank you!
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            # Загружаем эпизод
            episodes = {"1": temp_path}
            lines = self.episode_service.load_srt_episode("1", episodes)
            
            # Редактируем текст
            lines[0]['text'] = 'Hello, edited!'
            lines[1]['text'] = "I'm great now!"
            
            # Сохраняем
            success, message = self.episode_service.save_episode_to_srt(
                "1", episodes, lines
            )
            
            assert success is True
            
            # Проверяем сохранённый файл
            with open(temp_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            
            assert 'John: Hello, edited!' in saved_content
            assert "Mary: I'm great now!" in saved_content
            # Тайминги должны сохраниться
            assert '00:00:01,000 --> 00:00:04,000' in saved_content
            assert '00:00:05,000 --> 00:00:08,000' in saved_content
            
        finally:
            os.unlink(temp_path)

    def test_save_episode_to_srt_without_character(self):
        """Test saving SRT without character name"""
        srt_content = """1
00:00:01,000 --> 00:00:04,000
Hello.

2
00:00:05,000 --> 00:00:08,000
World.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            episodes = {"1": temp_path}
            lines = self.episode_service.load_srt_episode("1", episodes)
            
            # Редактируем текст
            lines[0]['text'] = 'Edited hello.'
            lines[0]['char'] = ''  # Без имени
            lines[1]['text'] = 'Edited world.'
            
            success, message = self.episode_service.save_episode_to_srt(
                "1", episodes, lines
            )
            
            assert success is True
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            
            assert 'Edited hello.' in saved_content
            assert 'Edited world.' in saved_content
            
        finally:
            os.unlink(temp_path)

    def test_save_episode_to_srt_via_save_episode_to_ass(self):
        """Test that save_episode_to_ass routes to SRT save for .srt files"""
        srt_content = """1
00:00:01,000 --> 00:00:04,000
John: Original text.
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as f:
            f.write(srt_content)
            temp_path = f.name

        try:
            episodes = {"1": temp_path}
            lines = self.episode_service.load_srt_episode("1", episodes)
            lines[0]['text'] = 'Edited via route!'
            
            # Вызываем save_episode_to_ass (должен определить .srt и вызвать save_episode_to_srt)
            success, message = self.episode_service.save_episode_to_ass(
                "1", episodes, lines
            )
            
            assert success is True
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            
            assert 'Edited via route!' in saved_content
            
        finally:
            os.unlink(temp_path)
