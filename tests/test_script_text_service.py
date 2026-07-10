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

    def test_create_episode_text_embeds_payload_in_project(self):
        """Рабочий текст сохраняется внутри проекта."""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        project_path = os.path.join(self.test_dir, "My Project.json")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {
            "project_name": "Test",
            "actors": {},
            "global_map": {},
            "episode_texts": {},
            "episode_working_texts": {}
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

        result = self.service.create_episode_text(
            data,
            "1",
            source_path,
            lines,
            {"merge": False},
            project_path
        )

        assert result == "1"
        assert data["episode_texts"] == {}

        payload = data["episode_working_texts"]["1"]
        assert payload["episode"] == "1"
        assert payload["source"]["path"] == source_path
        assert payload["characters"]["Hero"]["display_name"] == "Hero"
        assert payload["lines"][0]["text"] == "Hello"
        assert payload["lines"][0]["source_ids"] == [0]
        assert payload["format_version"] == "1.1"
        assert payload["source_lines"][0]["text"] == "Hello"
        assert payload["source_lines"][0]["character"] == "Hero"
        assert payload["source_ass"]["raw_content"] == "test"

    def test_save_source_ass_exports_original_snapshot(self):
        """Исходный ASS сохраняется из снимка в проекте без рабочих правок."""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        save_path = os.path.join(self.test_dir, "Original.ass")
        ass_content = (
            "[Script Info]\n"
            "Title: Test\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:01.00,0:00:02.00,Default,Hero,0,0,0,,Hello\n"
        )
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        data = {
            "project_name": "Test",
            "actors": {},
            "global_map": {},
            "episode_texts": {},
            "episode_working_texts": {}
        }

        self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{
                "id": 0,
                "s": 1.0,
                "e": 2.0,
                "char": "Hero",
                "text": "Hello",
                "s_raw": "0:00:01.00"
            }],
            {"merge": False},
            None
        )
        data["episode_working_texts"]["1"]["lines"][0]["text"] = "Edited"

        assert self.service.has_source_ass(data, "1") is True
        assert self.service.save_source_ass(data, "1", save_path) is True
        assert open(save_path, encoding="utf-8").read() == ass_content

    def test_get_source_lines_returns_original_unmerged_lines(self):
        """Исходные строки доступны отдельно от объединённых рабочих реплик."""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {
            "project_name": "Test",
            "actors": {},
            "global_map": {},
            "episode_texts": {},
            "episode_working_texts": {}
        }

        self.service.create_episode_text(
            data,
            "1",
            source_path,
            [
                {"id": 0, "s": 1.0, "e": 2.0, "char": "Hero", "text": "One"},
                {"id": 1, "s": 2.1, "e": 3.0, "char": "Hero", "text": "Two"},
            ],
            {"merge": True, "merge_gap": 10, "fps": 25},
            None
        )

        payload = data["episode_working_texts"]["1"]
        source_lines = self.service.get_source_lines(data, "1")

        assert len(payload["lines"]) == 1
        assert [line["text"] for line in source_lines] == ["One", "Two"]

    def test_create_episode_text_ignores_project_folder_for_storage(self):
        """Рабочий текст не создаёт внешний файл в рабочей папке."""
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
            "episode_working_texts": {},
            "project_folder": project_folder
        }

        result = self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{"id": 0, "s": 1.0, "e": 2.0, "char": "Hero", "text": "Hello"}],
            {"merge": False},
            project_path
        )

        assert result == "1"
        assert "1" in data["episode_working_texts"]
        assert data["episode_texts"] == {}

    def test_create_episode_text_uses_merge_config(self):
        """Рабочий текст сохраняет уже объединённые реплики"""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {
            "actors": {},
            "global_map": {},
            "episode_texts": {},
            "episode_working_texts": {}
        }
        lines = [
            {"id": 0, "s": 1.0, "e": 2.0, "char": "Hero", "text": "One", "s_raw": "0:00:01.00"},
            {"id": 1, "s": 2.1, "e": 3.0, "char": "Hero", "text": "Two", "s_raw": "0:00:02.10"},
        ]

        self.service.create_episode_text(
            data,
            "1",
            source_path,
            lines,
            {"merge": True, "merge_gap": 10, "fps": 25, "p_short": 0.5, "p_long": 2.0},
            None
        )

        payload = data["episode_working_texts"]["1"]

        assert len(payload["lines"]) == 1
        assert payload["lines"][0]["text"] == "One  Two"
        assert payload["lines"][0]["source_ids"] == [0, 1]
        assert payload["merge_config"]["merge"] is True

    def test_load_episode_lines_returns_app_format(self):
        """Рабочий текст загружается в формате реплик приложения"""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {
            "actors": {},
            "global_map": {},
            "episode_texts": {},
            "episode_working_texts": {}
        }
        self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{"id": 7, "s": 1.0, "e": 2.0, "char": "Hero", "text": "Edited", "s_raw": "0:00:01.00"}],
            {"merge": False},
            None
        )

        payload = data["episode_working_texts"]["1"]
        payload["lines"][0]["display_character"] = "Renamed Hero"
        payload["lines"][0]["text"] = "Edited text"

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

        data = {
            "actors": {},
            "global_map": {},
            "episode_texts": {},
            "episode_working_texts": {}
        }
        self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{"id": 0, "s": 1.0, "e": 2.0, "char": "Hero", "text": "Old", "s_raw": "0:00:01.00"}],
            {"merge": False},
            None
        )

        updated = self.service.update_line_text(data, "1", 0, "New")

        payload = data["episode_working_texts"]["1"]
        assert updated is True
        assert payload["lines"][0]["text"] == "New"
        assert payload["lines"][0]["dirty"] is True
        assert "modified_at" in payload

    def test_update_line_character_updates_display_character(self):
        """Смена персонажа реплики сохраняется в рабочий JSON."""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {
            "actors": {},
            "global_map": {},
            "episode_texts": {},
            "episode_working_texts": {}
        }
        self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{"id": 0, "s": 1.0, "e": 2.0, "char": "Hero", "text": "Line"}],
            {"merge": False},
            None
        )

        updated = self.service.update_line_character(data, "1", 0, "Villain")

        payload = data["episode_working_texts"]["1"]
        assert updated is True
        assert payload["lines"][0]["character"] == "Hero"
        assert payload["lines"][0]["display_character"] == "Villain"
        assert payload["lines"][0]["dirty"] is True
        assert payload["characters"]["Villain"]["display_name"] == "Villain"
        assert "modified_at" in payload

    def test_split_line_to_character_inserts_new_dirty_line(self):
        """Выделенный текст переносится в новую реплику другого персонажа."""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {
            "actors": {},
            "global_map": {},
            "episode_texts": {},
            "episode_working_texts": {}
        }
        self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{
                "id": 0,
                "s": 1.0,
                "e": 2.0,
                "char": "Hero",
                "text": "Hero text. Villain text."
            }],
            {"merge": False},
            None
        )

        updated = self.service.split_line_to_character(
            data,
            "1",
            0,
            "Hero text.",
            "Villain text.",
            "Villain"
        )

        payload = data["episode_working_texts"]["1"]
        assert updated is True
        assert len(payload["lines"]) == 2
        assert payload["lines"][0]["text"] == "Hero text."
        assert payload["lines"][0]["display_character"] == "Hero"
        assert payload["lines"][1]["text"] == "Villain text."
        assert payload["lines"][1]["display_character"] == "Villain"
        assert payload["lines"][1]["start"] == payload["lines"][0]["start"]
        assert payload["lines"][1]["dirty"] is True
        assert payload["characters"]["Villain"]["display_name"] == "Villain"
        assert "modified_at" in payload

    def test_rename_character_updates_display_names_only(self):
        """Переименование меняет display-поля, но не исходного персонажа"""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {
            "actors": {},
            "global_map": {},
            "episode_texts": {},
            "episode_working_texts": {}
        }
        self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{"id": 0, "s": 1.0, "e": 2.0, "char": "Hero", "text": "Line", "s_raw": "0:00:01.00"}],
            {"merge": False},
            None
        )

        updated = self.service.rename_character(data, "Hero", "Renamed Hero", "1")

        payload = data["episode_working_texts"]["1"]
        assert updated == 1
        assert payload["characters"]["Hero"]["display_name"] == "Renamed Hero"
        assert payload["lines"][0]["character"] == "Hero"
        assert payload["lines"][0]["display_character"] == "Renamed Hero"
        assert "modified_at" in payload

    def test_create_episode_text_replaces_embedded_working_text(self):
        """Пересоздание рабочего текста заменяет embedded payload."""
        source_path = os.path.join(self.test_dir, "Episode_01.ass")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("test")

        data = {
            "actors": {},
            "global_map": {},
            "episode_texts": {},
            "episode_working_texts": {}
        }
        self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{"id": 0, "s": 1.0, "e": 2.0, "char": "Hero", "text": "Old"}],
            {"merge": False},
            None
        )
        self.service.create_episode_text(
            data,
            "1",
            source_path,
            [{"id": 1, "s": 3.0, "e": 4.0, "char": "Hero", "text": "New"}],
            {"merge": False},
            None
        )

        payload = data["episode_working_texts"]["1"]
        assert payload["lines"][0]["text"] == "New"
        assert data["episode_texts"] == {}
