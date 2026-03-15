"""Тесты для core/models.py"""

import pytest
from core.models import (
    PrompterColors,
    PrompterConfig,
    ReplicaMergeConfig,
    ExportConfig,
    Actor,
    DialogueLine,
)


class TestPrompterColors:
    """Тесты для PrompterColors"""

    def test_default_values(self):
        """Тест значений по умолчанию"""
        colors = PrompterColors()
        
        assert colors.bg == "#000000"
        assert colors.active_text == "#FFFFFF"
        assert colors.inactive_text == "#444444"
        assert colors.tc == "#888888"
        assert colors.actor == "#AAAAAA"
        assert colors.header_bg == "#111111"
        assert colors.header_text == "#00FF00"

    def test_custom_values(self):
        """Тест пользовательских значений"""
        colors = PrompterColors(
            bg="#123456",
            active_text="#654321"
        )
        
        assert colors.bg == "#123456"
        assert colors.active_text == "#654321"

    def test_from_dict(self):
        """Тест создания из словаря"""
        data = {
            "bg": "#FFFFFF",
            "active_text": "#000000",
            "unknown_field": "ignored"
        }
        
        colors = PrompterColors.from_dict(data)
        
        assert colors.bg == "#FFFFFF"
        assert colors.active_text == "#000000"
        # Неизвестные поля игнорируются
        assert not hasattr(colors, "unknown_field")

    def test_from_dict_empty(self):
        """Тест создания из пустого словаря"""
        colors = PrompterColors.from_dict({})
        
        assert colors.bg == "#000000"  # Значение по умолчанию

    def test_to_dict(self):
        """Тест преобразования в словарь"""
        colors = PrompterColors(bg="#111111")
        result = colors.to_dict()
        
        assert isinstance(result, dict)
        assert result["bg"] == "#111111"
        assert "active_text" in result

    def test_post_init_invalid_color(self):
        """Тест валидации цвета"""
        with pytest.raises(ValueError) as exc_info:
            PrompterColors(bg="invalid")
        
        assert "Invalid hex color" in str(exc_info.value)

    def test_post_init_invalid_color_format(self):
        """Тест валидации формата цвета"""
        with pytest.raises(ValueError):
            PrompterColors(bg="#12345")  # Слишком короткий
        
        with pytest.raises(ValueError):
            PrompterColors(bg="123456")  # Без #


class TestPrompterConfig:
    """Тесты для PrompterConfig"""

    def test_default_values(self):
        """Тест значений по умолчанию"""
        config = PrompterConfig()
        
        assert config.f_tc == 20
        assert config.f_char == 24
        assert config.f_actor == 18
        assert config.f_text == 36
        assert config.focus_ratio == 0.5
        assert config.is_mirrored == False
        assert config.port_in == 8000
        assert config.port_out == 9000

    def test_from_dict(self):
        """Тест создания из словаря"""
        data = {
            "f_tc": 30,
            "f_char": 40,
            "is_mirrored": True
        }
        
        config = PrompterConfig.from_dict(data)
        
        assert config.f_tc == 30
        assert config.f_char == 40
        assert config.is_mirrored == True

    def test_from_dict_with_colors(self):
        """Тест создания из словаря с цветами"""
        data = {
            "f_tc": 25,
            "colors": {"bg": "#FFFFFF"}
        }
        
        config = PrompterConfig.from_dict(data)
        
        assert config.f_tc == 25
        assert config.colors.bg == "#FFFFFF"

    def test_from_dict_empty(self):
        """Тест создания из пустого словаря"""
        config = PrompterConfig.from_dict({})
        
        assert config.f_tc == 20  # Значение по умолчанию

    def test_from_dict_none(self):
        """Тест создания из None"""
        config = PrompterConfig.from_dict(None)
        
        assert config.f_tc == 20

    def test_to_dict(self):
        """Тест преобразования в словарь"""
        config = PrompterConfig(f_tc=35)
        result = config.to_dict()
        
        assert isinstance(result, dict)
        assert result["f_tc"] == 35
        assert "colors" in result

    def test_ensure_defaults(self):
        """Тест обеспечения значений по умолчанию"""
        config = PrompterConfig()
        # Удаляем атрибут
        delattr(config, 'f_tc')
        
        config.ensure_defaults()
        
        assert config.f_tc == 20

    def test_post_init_invalid_f_tc(self):
        """Тест валидации f_tc"""
        with pytest.raises(ValueError) as exc_info:
            PrompterConfig(f_tc=5)
        
        assert "f_tc must be 10-150" in str(exc_info.value)
        
        with pytest.raises(ValueError):
            PrompterConfig(f_tc=200)

    def test_post_init_invalid_f_char(self):
        """Тест валидации f_char"""
        with pytest.raises(ValueError):
            PrompterConfig(f_char=5)
        
        with pytest.raises(ValueError):
            PrompterConfig(f_char=200)

    def test_post_init_invalid_f_actor(self):
        """Тест валидации f_actor"""
        with pytest.raises(ValueError):
            PrompterConfig(f_actor=5)
        
        with pytest.raises(ValueError):
            PrompterConfig(f_actor=200)

    def test_post_init_invalid_f_text(self):
        """Тест валидации f_text"""
        with pytest.raises(ValueError):
            PrompterConfig(f_text=5)
        
        with pytest.raises(ValueError):
            PrompterConfig(f_text=350)

    def test_post_init_invalid_focus_ratio(self):
        """Тест валидации focus_ratio"""
        with pytest.raises(ValueError):
            PrompterConfig(focus_ratio=-0.1)
        
        with pytest.raises(ValueError):
            PrompterConfig(focus_ratio=1.1)

    def test_post_init_invalid_port_in(self):
        """Тест валидации port_in"""
        with pytest.raises(ValueError):
            PrompterConfig(port_in=100)
        
        with pytest.raises(ValueError):
            PrompterConfig(port_in=70000)

    def test_post_init_invalid_port_out(self):
        """Тест валидации port_out"""
        with pytest.raises(ValueError):
            PrompterConfig(port_out=500)
        
        with pytest.raises(ValueError):
            PrompterConfig(port_out=70000)

    def test_post_init_invalid_scroll_smoothness(self):
        """Тест валидации scroll_smoothness_slider"""
        with pytest.raises(ValueError):
            PrompterConfig(scroll_smoothness_slider=-1)
        
        with pytest.raises(ValueError):
            PrompterConfig(scroll_smoothness_slider=101)


class TestReplicaMergeConfig:
    """Тесты для ReplicaMergeConfig"""

    def test_default_values(self):
        """Тест значений по умолчанию"""
        config = ReplicaMergeConfig()
        
        assert config.merge == True
        assert config.merge_gap == 5
        assert config.p_short == 0.5
        assert config.p_long == 2.0
        assert config.fps == 25.0

    def test_from_dict(self):
        """Тест создания из словаря"""
        data = {
            "merge": False,
            "merge_gap": 10,
            "fps": 30.0
        }
        
        config = ReplicaMergeConfig.from_dict(data)
        
        assert config.merge == False
        assert config.merge_gap == 10
        assert config.fps == 30.0

    def test_from_dict_empty(self):
        """Тест создания из пустого словаря"""
        config = ReplicaMergeConfig.from_dict({})
        
        assert config.merge == True

    def test_to_dict(self):
        """Тест преобразования в словарь"""
        config = ReplicaMergeConfig(merge_gap=20)
        result = config.to_dict()
        
        assert isinstance(result, dict)
        assert result["merge_gap"] == 20

    def test_post_init_invalid_merge_gap(self):
        """Тест валидации merge_gap"""
        with pytest.raises(ValueError):
            ReplicaMergeConfig(merge_gap=0)
        
        with pytest.raises(ValueError):
            ReplicaMergeConfig(merge_gap=1001)

    def test_post_init_invalid_p_short(self):
        """Тест валидации p_short"""
        with pytest.raises(ValueError):
            ReplicaMergeConfig(p_short=-0.1)
        
        with pytest.raises(ValueError):
            ReplicaMergeConfig(p_short=10.1)

    def test_post_init_invalid_p_long(self):
        """Тест валидации p_long"""
        with pytest.raises(ValueError):
            ReplicaMergeConfig(p_long=-0.1)
        
        with pytest.raises(ValueError):
            ReplicaMergeConfig(p_long=10.1)

    def test_post_init_invalid_fps(self):
        """Тест валидации fps"""
        with pytest.raises(ValueError):
            ReplicaMergeConfig(fps=0.5)
        
        with pytest.raises(ValueError):
            ReplicaMergeConfig(fps=120.1)


class TestExportConfig:
    """Тесты для ExportConfig"""

    def test_default_values(self):
        """Тест значений по умолчанию"""
        config = ExportConfig()
        
        assert config.layout_type == 'Таблица'
        assert config.col_tc == True
        assert config.col_char == True
        assert config.col_actor == True
        assert config.col_text == True
        assert config.use_color == True
        assert config.open_auto == True

    def test_from_dict(self):
        """Тест создания из словаря"""
        data = {
            "layout_type": "Сценарий",
            "col_tc": False,
            "f_text": 50
        }
        
        config = ExportConfig.from_dict(data)
        
        assert config.layout_type == "Сценарий"
        assert config.col_tc == False
        assert config.f_text == 50

    def test_from_dict_empty(self):
        """Тест создания из пустого словаря"""
        config = ExportConfig.from_dict({})
        
        assert config.layout_type == 'Таблица'

    def test_to_dict(self):
        """Тест преобразования в словарь"""
        config = ExportConfig(layout_type="Сценарий")
        result = config.to_dict()
        
        assert isinstance(result, dict)
        assert result["layout_type"] == "Сценарий"

    def test_post_init_invalid_layout_type(self):
        """Тест валидации layout_type"""
        with pytest.raises(ValueError) as exc_info:
            ExportConfig(layout_type="Invalid")
        
        assert "layout_type must be 'Таблица' or 'Сценарий'" in str(exc_info.value)

    def test_post_init_invalid_f_time(self):
        """Тест валидации f_time"""
        with pytest.raises(ValueError):
            ExportConfig(f_time=5)
        
        with pytest.raises(ValueError):
            ExportConfig(f_time=200)

    def test_post_init_invalid_f_char(self):
        """Тест валидации f_char"""
        with pytest.raises(ValueError):
            ExportConfig(f_char=5)

    def test_post_init_invalid_f_actor(self):
        """Тест валидации f_actor"""
        with pytest.raises(ValueError):
            ExportConfig(f_actor=5)

    def test_post_init_invalid_f_text(self):
        """Тест валидации f_text"""
        with pytest.raises(ValueError):
            ExportConfig(f_text=5)


class TestActor:
    """Тесты для Actor"""

    def test_default_values(self):
        """Тест значений по умолчанию"""
        actor = Actor(name="Test Actor")
        
        assert actor.name == "Test Actor"
        assert actor.color == "#FFFFFF"
        assert actor.roles == []

    def test_custom_values(self):
        """Тест пользовательских значений"""
        actor = Actor(
            name="John Doe",
            color="#FF0000",
            roles=["Hero", "Villain"]
        )
        
        assert actor.name == "John Doe"
        assert actor.color == "#FF0000"
        assert len(actor.roles) == 2


class TestDialogueLine:
    """Тесты для DialogueLine"""

    def test_default_values(self):
        """Тест значений по умолчанию"""
        line = DialogueLine(
            id=1,
            s=0.0,
            e=2.0,
            char="Character",
            text="Hello"
        )
        
        assert line.id == 1
        assert line.s == 0.0
        assert line.e == 2.0
        assert line.char == "Character"
        assert line.text == "Hello"
        assert line.s_raw == ""
        assert line.source_ids == []
        assert line.source_texts == []
        assert line.parts == []

    def test_with_all_fields(self):
        """Тест со всеми полями"""
        line = DialogueLine(
            id=1,
            s=0.0,
            e=2.0,
            char="Character",
            text="Hello",
            s_raw="00:00:00.00",
            source_ids=[1, 2],
            source_texts=["Hi", "There"],
            parts=[{"id": 1, "text": "Hi"}]
        )
        
        assert line.s_raw == "00:00:00.00"
        assert len(line.source_ids) == 2
        assert len(line.parts) == 1

    def test_to_dict(self):
        """Тест преобразования в словарь"""
        line = DialogueLine(id=1, s=0, e=2, char="C", text="T")
        result = line.to_dict()
        
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["text"] == "T"

    def test_from_dict(self):
        """Тест создания из словаря"""
        data = {
            "id": 5,
            "s": 1.5,
            "e": 3.5,
            "char": "Char",
            "text": "Text",
            "extra_field": "ignored"
        }
        
        line = DialogueLine.from_dict(data)
        
        assert line.id == 5
        assert line.s == 1.5
        # Лишние поля игнорируются
        assert not hasattr(line, "extra_field")
