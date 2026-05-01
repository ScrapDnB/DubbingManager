"""Тесты диагностики проекта."""

import json

from services.project_health_service import ProjectHealthService


def _write_working_text(path, lines):
    payload = {
        "format_version": "1.0",
        "episode": "1",
        "lines": lines,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8"
    )


class TestProjectHealthService:
    """Проверка ProjectHealthService."""

    def test_healthy_project_has_no_issues(self, tmp_path):
        source = tmp_path / "episode.ass"
        video = tmp_path / "episode.mp4"
        text = tmp_path / "episode.json"
        source.write_text("ass", encoding="utf-8")
        video.write_text("video", encoding="utf-8")
        _write_working_text(text, [{
            "start": 1.0,
            "end": 2.0,
            "character": "Hero",
            "text": "Hello",
        }])

        data = {
            "episodes": {"1": str(source)},
            "episode_texts": {"1": str(text)},
            "video_paths": {"1": str(video)},
            "actors": [{"id": "actor-1", "name": "Actor"}],
            "global_map": {"Hero": "actor-1"},
        }

        issues = ProjectHealthService().check_project(data)

        assert issues == []

    def test_reports_missing_files_and_broken_lines(self, tmp_path):
        text = tmp_path / "episode.json"
        _write_working_text(text, [
            {
                "start": 2.0,
                "end": 2.0,
                "character": "",
                "text": "",
            },
            {
                "start": 3.0,
                "end": 4.0,
                "character": "Villain",
                "text": "Line",
            },
        ])

        data = {
            "episodes": {"1": str(tmp_path / "missing.ass")},
            "episode_texts": {"1": str(text)},
            "video_paths": {"1": str(tmp_path / "missing.mp4")},
            "actors": [],
            "global_map": {},
        }

        issues = ProjectHealthService().check_project(data)
        messages = [issue.message for issue in issues]

        assert "Исходный файл серии не найден." in messages
        assert "Видео файл не найден." in messages
        assert "Реплика 1: пустой текст." in messages
        assert "Реплика 1: не указан персонаж." in messages
        assert "Реплика 1: конец фразы не позже начала." in messages
        assert "Персонаж без назначенного актёра: Villain" in messages

    def test_reports_invalid_working_json(self, tmp_path):
        text = tmp_path / "bad.json"
        text.write_text("{", encoding="utf-8")

        data = {
            "episodes": {},
            "episode_texts": {"pilot": str(text)},
        }

        issues = ProjectHealthService().check_project(data)

        assert len(issues) == 1
        assert issues[0].severity == ProjectHealthService.SEVERITY_ERROR
        assert issues[0].category == "Рабочий текст"
        assert "Не удалось прочитать рабочий JSON" in issues[0].message

    def test_summary_counts_severities(self):
        service = ProjectHealthService()
        issues = service.check_project({})

        summary = service.get_summary(issues)

        assert summary == {
            "errors": 0,
            "warnings": 1,
            "info": 0,
            "total": 1,
        }
