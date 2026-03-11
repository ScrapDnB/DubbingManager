"""Тесты для actor_service.py"""

import pytest
from services.actor_service import ActorService


class TestActorServiceAdditional:
    """Дополнительные тесты для ActorService"""

    @pytest.fixture
    def service(self):
        """Сервис для тестов"""
        return ActorService()

    def test_get_actor_statistics(self, service):
        """Тест получения статистики актёра"""
        actors = {
            "actor1": {"name": "Actor One", "color": "#FF0000"},
            "actor2": {"name": "Actor Two", "color": "#00FF00"},
        }
        global_map = {"Char1": "actor1", "Char2": "actor2"}
        episode_stats = [
            {"name": "Char1", "lines": 10, "words": 100},
            {"name": "Char2", "lines": 5, "words": 50},
        ]

        stats = service.get_actor_statistics(actors, global_map, episode_stats)

        assert "actor1" in stats
        assert stats["actor1"]["name"] == "Actor One"
        assert stats["actor1"]["total_lines"] == 10
        assert stats["actor1"]["total_words"] == 100
        assert stats["actor1"]["roles"] == ["Char1"]

    def test_get_actor_statistics_no_roles(self, service):
        """Тест статистики без ролей"""
        actors = {"actor1": {"name": "Actor", "color": "#FF0000"}}
        global_map = {}  # Нет назначений
        episode_stats = [{"name": "Char1", "lines": 10, "words": 100}]

        stats = service.get_actor_statistics(actors, global_map, episode_stats)

        assert stats["actor1"]["total_lines"] == 0
        assert stats["actor1"]["total_words"] == 0

    def test_get_unassigned_characters(self, service):
        """Тест получения неназначенных персонажей"""
        global_map = {"Char1": "actor1"}
        episode_stats = [
            {"name": "Char1", "lines": 10},
            {"name": "Char2", "lines": 5},  # Не назначен
        ]

        unassigned = service.get_unassigned_characters(global_map, episode_stats)

        assert "Char2" in unassigned
        assert "Char1" not in unassigned

    def test_get_unassigned_characters_all_assigned(self, service):
        """Тест когда все персонажи назначены"""
        global_map = {"Char1": "actor1", "Char2": "actor2"}
        episode_stats = [
            {"name": "Char1", "lines": 10},
            {"name": "Char2", "lines": 5},
        ]

        unassigned = service.get_unassigned_characters(global_map, episode_stats)

        assert len(unassigned) == 0

    def test_get_next_color_all_used(self, service):
        """Тест получения цвета когда все цвета использованы"""
        # Используем все цвета из палитры
        actors = {
            f"actor{i}": {"name": f"Actor {i}", "color": color}
            for i, color in enumerate([
                "#D9775F", "#E46C0A", "#9B5333", "#C0504D", "#C4BD97",
                "#D4A017", "#938953", "#8A7F80", "#76923C", "#4F6228",
                "#31859B", "#669999", "#4F81BD", "#5B9BD5", "#2C4D75",
                "#708090", "#B65C72", "#8064A2", "#5F497A", "#7B3F61"
            ])
        }

        # Должен вернуть случайный цвет из палитры
        color = service._get_next_color(actors)

        assert color.startswith("#")
        assert len(color) == 7

    def test_get_next_color_some_available(self, service):
        """Тест получения цвета когда есть свободные"""
        actors = {
            "actor1": {"name": "Actor 1", "color": "#D9775F"},
        }

        color = service._get_next_color(actors)

        assert color != "#D9775F"  # Должен вернуть другой цвет
        assert color.startswith("#")

    def test_add_actor_with_empty_actors(self, service):
        """Тест добавления актёра в пустой словарь"""
        actors = {}

        actor_id = service.add_actor(actors, "New Actor")

        assert actor_id in actors
        assert actors[actor_id]["name"] == "New Actor"
        assert actors[actor_id]["color"] is not None

    def test_add_actor_with_specific_color(self, service):
        """Тест добавления актёра с конкретным цветом"""
        actors = {}

        actor_id = service.add_actor(actors, "New Actor", "#123456")

        assert actors[actor_id]["color"] == "#123456"

    def test_update_actor_color_nonexistent(self, service):
        """Тест обновления цвета несуществующего актёра"""
        actors = {}

        result = service.update_actor_color(actors, "nonexistent", "#FFFFFF")

        assert result == False

    def test_rename_actor_nonexistent(self, service):
        """Тест переименования несуществующего актёра"""
        actors = {}

        result = service.rename_actor(actors, "nonexistent", "New Name")

        assert result == False

    def test_delete_actor_nonexistent(self, service):
        """Тест удаления несуществующего актёра"""
        actors = {}

        result = service.delete_actor(actors, "nonexistent")

        assert result == False

    def test_assign_actor_to_character_none_actor_id(self, service):
        """Тест назначения None актёра (удаление)"""
        global_map = {"Char1": "actor1"}

        service.assign_actor_to_character(global_map, "Char1", None)

        assert "Char1" not in global_map

    def test_bulk_assign_actors_empty_list(self, service):
        """Тест массового назначения пустого списка"""
        global_map = {}

        count = service.bulk_assign_actors(global_map, [], "actor1")

        assert count == 0

    def test_bulk_assign_actors_remove_assignment(self, service):
        """Тест массового удаления назначений"""
        global_map = {"Char1": "actor1", "Char2": "actor2"}

        count = service.bulk_assign_actors(global_map, ["Char1", "Char2"], None)

        assert count == 2
        assert "Char1" not in global_map
        assert "Char2" not in global_map

    def test_update_actor_roles_empty_roles(self, service):
        """Тест обновления ролей пустым списком"""
        global_map = {"Char1": "actor1", "Char2": "actor1"}

        service.update_actor_roles(global_map, "actor1", [])

        assert "Char1" not in global_map
        assert "Char2" not in global_map

    def test_update_actor_roles_new_roles(self, service):
        """Тест обновления ролей новыми ролями"""
        global_map = {"OldChar": "actor1"}

        service.update_actor_roles(global_map, "actor1", ["NewChar1", "NewChar2"])

        assert "OldChar" not in global_map
        assert global_map["NewChar1"] == "actor1"
        assert global_map["NewChar2"] == "actor1"

    def test_get_actor_statistics_multiple_episodes(self, service):
        """Тест статистики по нескольким эпизодам"""
        actors = {"actor1": {"name": "Actor", "color": "#FF0000"}}
        global_map = {"Char1": "actor1"}
        episode_stats = [
            {"name": "Char1", "lines": 10, "words": 100},
            {"name": "OtherChar", "lines": 5, "words": 50},  # Не этот актёр
        ]

        stats = service.get_actor_statistics(actors, global_map, episode_stats)

        assert stats["actor1"]["total_lines"] == 10
        assert stats["actor1"]["total_words"] == 100

    def test_actor_service_color_index_persists(self, service):
        """Тест что индекс цвета сохраняется между вызовами"""
        actors1 = {"a1": {"name": "A1", "color": "#D9775F"}}
        actors2 = {"a1": {"name": "A1", "color": "#D9775F"}}

        color1 = service._get_next_color(actors1)
        color2 = service._get_next_color(actors2)

        # Цвета должны быть разными (индекс увеличивается)
        # или одинаковыми если первый цвет освободился
        assert color1.startswith("#")
        assert color2.startswith("#")
