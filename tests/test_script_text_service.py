"""Тесты для ScriptTextService"""

import os
import tempfile
import shutil

from services import ScriptTextService


class TestScriptTextService:
    """Тесты сервиса рабочих текстов эпизодов"""

    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()
        self.service = ScriptTextService()

    def teardown_method(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_episode_text_next_to_project(self):
        """Рабочий текст создаётся рядом с файлом проекта"""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        project_path = os.path.join(self.test_dir, "My Project.json")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {
            "project_name": "Test",
            "actors": {},
            "global_map": {},
            "episode_texts": {}
        }
        lines = [
            {
                "id": 0,
                "s": 1.0,
                "e": 2.0,
                "char": "Hero",
                "text": "Hello",
                "s_raw": "0:00:01.00"
            }
        ]

        text_path = self.service.create_episode_text(
            data,
            "1",
            source_path,
            lines,
            {"merge": False},
            project_path
        )

        assert text_path == os.path.join(self.test_dir, "My Project_texts_dm", "episode_1.json")
        assert data["episode_texts"]["1"] == text_path
        assert os.path.exists(text_path)

        payload = self.service.load_episode_text(text_path)
        assert payload["episode"] == "1"
        assert payload["source"]["path"] == source_path
        assert payload["characters"]["Hero"]["display_name"] == "Hero"
        assert payload["lines"][0]["text"] == "Hello"
        assert payload["lines"][0]["source_ids"] == [0]

    def test_create_episode_text_prefers_project_folder(self):
        """Рабочий текст создаётся в рабочей папке, если она указана."""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        project_path = os.path.join(self.test_dir, "My Project.json")
        project_folder = os.path.join(self.test_dir, "Work")
        os.makedirs(project_folder)
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {
            "project_name": "Test",
            "actors": {},
            "global_map": {},
            "episode_texts": {},
            "project_folder": project_folder
        }

        text_path = self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{"id": 0, "s": 1.0, "e": 2.0, "char": "Hero", "text": "Hello"}],
            {"merge": False},
            project_path
        )

        assert text_path == os.path.join(project_folder, "texts_dm", "episode_1.json")
        assert os.path.exists(text_path)

    def test_create_episode_text_uses_merge_config(self):
        """Рабочий текст сохраняет уже объединённые реплики"""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {"actors": {}, "global_map": {}, "episode_texts": {}}
        lines = [
            {"id": 0, "s": 1.0, "e": 2.0, "char": "Hero", "text": "One", "s_raw": "0:00:01.00"},
            {"id": 1, "s": 2.1, "e": 3.0, "char": "Hero", "text": "Two", "s_raw": "0:00:02.10"},
        ]

        text_path = self.service.create_episode_text(
            data,
            "1",
            source_path,
            lines,
            {"merge": True, "merge_gap": 10, "fps": 25, "p_short": 0.5, "p_long": 2.0},
            None
        )

        payload = self.service.load_episode_text(text_path)

        assert len(payload["lines"]) == 1
        assert payload["lines"][0]["text"] == "One  Two"
        assert payload["lines"][0]["source_ids"] == [0, 1]
        assert payload["merge_config"]["merge"] is True

    def test_load_episode_lines_returns_app_format(self):
        """Рабочий текст загружается в формате реплик приложения"""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {"actors": {}, "global_map": {}, "episode_texts": {}}
        text_path = self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{"id": 7, "s": 1.0, "e": 2.0, "char": "Hero", "text": "Edited", "s_raw": "0:00:01.00"}],
            {"merge": False},
            None
        )

        payload = self.service.load_episode_text(text_path)
        payload["lines"][0]["display_character"] = "Renamed Hero"
        payload["lines"][0]["text"] = "Edited text"
        with open(text_path, "w", encoding="utf-8") as f:
            import json
            json.dump(payload, f, ensure_ascii=False)

        lines = self.service.load_episode_lines(data, "1")

        assert lines[0]["_working_text"] is True
        assert lines[0]["char"] == "Renamed Hero"
        assert lines[0]["source_char"] == "Hero"
        assert lines[0]["text"] == "Edited text"
        assert lines[0]["source_ids"] == [7]

    def test_update_line_text_marks_dirty_and_saves(self):
        """Обновление текста сохраняется в рабочий JSON"""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {"actors": {}, "global_map": {}, "episode_texts": {}}
        text_path = self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{"id": 0, "s": 1.0, "e": 2.0, "char": "Hero", "text": "Old", "s_raw": "0:00:01.00"}],
            {"merge": False},
            None
        )

        updated = self.service.update_line_text(data, "1", 0, "New")

        payload = self.service.load_episode_text(text_path)
        assert updated is True
        assert payload["lines"][0]["text"] == "New"
        assert payload["lines"][0]["dirty"] is True
        assert "modified_at" in payload

    def test_rename_character_updates_display_names_only(self):
        """Переименование меняет display-поля, но не исходного персонажа"""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {"actors": {}, "global_map": {}, "episode_texts": {}}
        text_path = self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{"id": 0, "s": 1.0, "e": 2.0, "char": "Hero", "text": "Line", "s_raw": "0:00:01.00"}],
            {"merge": False},
            None
        )

        updated = self.service.rename_character(data, "Hero", "Renamed Hero", "1")

        payload = self.service.load_episode_text(text_path)
        assert updated == 1
        assert payload["characters"]["Hero"]["display_name"] == "Renamed Hero"
        assert payload["lines"][0]["character"] == "Hero"
        assert payload["lines"][0]["display_character"] == "Renamed Hero"
        assert "modified_at" in payload
