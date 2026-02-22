"""Сервис для управления эпизодами и парсинга ASS файлов"""

import os
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from utils.helpers import ass_time_to_seconds

logger = logging.getLogger(__name__)


class EpisodeService:
    """Сервис для работы с эпизодами: парсинг ASS, загрузка, сохранение"""

    def __init__(self, merge_gap: int = 5):
        self.merge_gap = merge_gap
        self._loaded_episodes: Dict[str, List[Dict[str, Any]]] = {}

    def parse_ass_file(self, path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Парсинг ASS файла

        Returns:
            Tuple containing:
            - char_data: статистика по персонажам (name, lines, rings, words)
            - lines_list: список всех реплик
        """
        char_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"lines": 0, "raw": []}
        )

        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines_list = []

                for line in f:
                    if line.startswith("Dialogue:"):
                        parts = line.split(',', 9)
                        if len(parts) < 10:
                            continue

                        char = parts[4].strip()
                        text = re.sub(r'\{.*?\}', '', parts[9]).strip()

                        if text:
                            line_data = {
                                's': ass_time_to_seconds(parts[1]),
                                'e': ass_time_to_seconds(parts[2]),
                                'char': char,
                                'text': text,
                                's_raw': parts[1]
                            }
                            lines_list.append(line_data)

                            char_data[char]["lines"] += 1
                            char_data[char]["raw"].append(line_data)

                # Вычисление статистики
                stats = []
                for char, info in char_data.items():
                    rings = 1
                    words = 0
                    char_lines = info["raw"]

                    if char_lines:
                        words = len(char_lines[0]['text'].split())

                        for i in range(1, len(char_lines)):
                            if char_lines[i]['s'] - char_lines[i-1]['e'] >= self.merge_gap:
                                rings += 1
                            words += len(char_lines[i]['text'].split())

                    stats.append({
                        "name": char,
                        "lines": info["lines"],
                        "rings": rings,
                        "words": words
                    })

                return stats, lines_list

        except Exception as e:
            logger.error(f"Error parsing ASS: {e}")
            return [], []

    def load_episode(
        self,
        ep_num: str,
        episodes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Загрузка эпизода в память

        Args:
            ep_num: номер эпизода
            episodes: словарь эпизодов {ep_num: path}

        Returns:
            Список реплик эпизода
        """
        # Проверяем кэш
        if ep_num in self._loaded_episodes:
            return self._loaded_episodes[ep_num]

        path = episodes.get(ep_num)
        if not path or not os.path.exists(path):
            return []

        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = []
                idx = 0

                for line in f:
                    if line.startswith("Dialogue:"):
                        parts = line.split(',', 9)
                        if len(parts) >= 10:
                            lines.append({
                                'id': idx,
                                's': ass_time_to_seconds(parts[1]),
                                'e': ass_time_to_seconds(parts[2]),
                                'char': parts[4].strip(),
                                'text': re.sub(r'\{.*?\}', '', parts[9]).strip(),
                                's_raw': parts[1]
                            })
                            idx += 1

                self._loaded_episodes[ep_num] = lines
                return lines

        except Exception as e:
            logger.error(f"Read error: {e}")
            return []

    def get_episode_lines(
        self,
        ep_num: str,
        episodes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Получение реплик эпизода (с загрузкой если нужно)"""
        return self.load_episode(ep_num, episodes)

    def save_episode_to_ass(
        self,
        ep_num: str,
        episodes: Dict[str, str],
        memory_lines: List[Dict[str, Any]],
        target_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Сохранение эпизода в ASS файл

        Args:
            ep_num: номер эпизода
            episodes: словарь эпизодов
            memory_lines: реплики из памяти
            target_path: путь для сохранения (если None - сохраняется в оригинал)

        Returns:
            Tuple[success, message]
        """
        if not memory_lines:
            return False, "Нет данных для сохранения"

        source_path = episodes.get(ep_num)
        if not source_path or not os.path.exists(source_path):
            return False, "Файл не найден"

        save_path = target_path or source_path
        new_file_content = []

        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                dia_idx = 0

                for line in f:
                    if line.startswith("Dialogue:"):
                        if dia_idx < len(memory_lines):
                            current_data = memory_lines[dia_idx]
                            parts = line.strip().split(',', 9)

                            if len(parts) > 9:
                                parts[4] = current_data['char']
                                new_line = (
                                    f"{','.join(parts[:9])},"
                                    f"{current_data['text']}\n"
                                )
                                new_file_content.append(new_line)
                            else:
                                new_file_content.append(line)
                        else:
                            new_file_content.append(line)

                        dia_idx += 1
                    else:
                        new_file_content.append(line)

            with open(save_path, 'w', encoding='utf-8') as f:
                f.writelines(new_file_content)

            logger.info(f"ASS saved to {save_path}")
            return True, f"Серия {ep_num} сохранена"

        except Exception as e:
            logger.error(f"Error saving ASS: {e}")
            return False, f"Ошибка записи: {e}"

    def clear_cache(self, ep_num: Optional[str] = None) -> None:
        """
        Очистка кэша загруженных эпизодов

        Args:
            ep_num: номер эпизода для очистки (если None - очистка всего кэша)
        """
        if ep_num:
            self._loaded_episodes.pop(ep_num, None)
        else:
            self._loaded_episodes.clear()

    def invalidate_episode(self, ep_num: str) -> None:
        """Инвалидация кэша эпизода после изменений"""
        if ep_num in self._loaded_episodes:
            del self._loaded_episodes[ep_num]

    def set_merge_gap(self, gap: int) -> None:
        """Установка зазора для слияния реплик"""
        self.merge_gap = gap
