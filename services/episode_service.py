"""Сервис для управления эпизодами и парсинга ASS/SRT файлов"""

import os
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from utils.helpers import ass_time_to_seconds, srt_time_to_seconds

logger = logging.getLogger(__name__)


class EpisodeService:
    """Сервис для работы с эпизодами: парсинг ASS, загрузка, сохранение"""

    def __init__(self, merge_gap: int = 5, fps: float = 25.0):
        self.merge_gap = merge_gap
        self.fps = fps
        self._loaded_episodes: Dict[str, List[Dict[str, Any]]] = {}

    def set_merge_gap_from_config(self, replica_merge_config: Dict[str, Any]) -> None:
        """Установка зазора для слияния реплик из конфига"""
        self.merge_gap = replica_merge_config.get('merge_gap', 5)
        self.fps = replica_merge_config.get('fps', 25.0)

    def set_fps(self, fps: float) -> None:
        """Установка частоты кадров"""
        self.fps = fps

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
                # Конвертируем merge_gap из кадров в секунды
                merge_gap_seconds = self.merge_gap / self.fps

                stats = []
                for char, info in char_data.items():
                    rings = 1
                    words = 0
                    char_lines = info["raw"]

                    if char_lines:
                        words = len(char_lines[0]['text'].split())

                        for i in range(1, len(char_lines)):
                            if char_lines[i]['s'] - char_lines[i-1]['e'] >= merge_gap_seconds:
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

    def parse_srt_file(self, path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Парсинг SRT файла

        Формат реплики:
        Имя_персонажа: реплика

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
                content = f.read()

            # Разделяем на блоки (каждый блок - отдельная реплика)
            blocks = re.split(r'\n\s*\n', content.strip())
            lines_list = []

            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) < 3:
                    continue

                # Первая строка - номер, вторая - время, остальные - текст
                try:
                    time_line = lines[1]
                    time_parts = time_line.split(' --> ')
                    if len(time_parts) != 2:
                        continue

                    start_time = time_parts[0].strip()
                    end_time = time_parts[1].strip()

                    # Текст реплики (может быть несколько строк)
                    text_lines = lines[2:]
                    full_text = '\n'.join(text_lines).strip()

                    # Извлекаем имя персонажа из текста (формат: "Имя: реплика")
                    char_name = ""
                    replica_text = full_text

                    # Ищем первое двоеточие для извлечения имени
                    colon_match = re.match(r'^([^:]+):\s*(.*)', full_text, re.DOTALL)
                    if colon_match:
                        char_name = colon_match.group(1).strip()
                        replica_text = colon_match.group(2).strip()
                    else:
                        # Если двоеточия нет, используем пустое имя
                        char_name = ""
                        replica_text = full_text

                    if replica_text:
                        line_data = {
                            's': srt_time_to_seconds(start_time),
                            'e': srt_time_to_seconds(end_time),
                            'char': char_name,
                            'text': replica_text,
                            's_raw': start_time
                        }
                        lines_list.append(line_data)

                        char_data[char_name]["lines"] += 1
                        char_data[char_name]["raw"].append(line_data)

                except (IndexError, ValueError) as e:
                    logger.warning(f"Skipping invalid SRT block: {e}")
                    continue

            # Вычисление статистики
            # Конвертируем merge_gap из кадров в секунды
            merge_gap_seconds = self.merge_gap / self.fps

            stats = []
            for char, info in char_data.items():
                rings = 1
                words = 0
                char_lines = info["raw"]

                if char_lines:
                    words = len(char_lines[0]['text'].split())

                    for i in range(1, len(char_lines)):
                        # При слиянии реплик игнорируем префикс "Имя_персонажа:"
                        if char_lines[i]['s'] - char_lines[i-1]['e'] >= merge_gap_seconds:
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
            logger.error(f"Error parsing SRT: {e}")
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

    def load_srt_episode(
        self,
        ep_num: str,
        episodes: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Загрузка SRT эпизода в память

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
                content = f.read()

            # Разделяем на блоки
            blocks = re.split(r'\n\s*\n', content.strip())
            lines = []
            idx = 0

            for block in blocks:
                block_lines = block.strip().split('\n')
                if len(block_lines) < 3:
                    continue

                try:
                    time_line = block_lines[1]
                    time_parts = time_line.split(' --> ')
                    if len(time_parts) != 2:
                        continue

                    start_time = time_parts[0].strip()
                    end_time = time_parts[1].strip()

                    # Текст реплики
                    text_lines = block_lines[2:]
                    full_text = '\n'.join(text_lines).strip()

                    # Извлекаем имя персонажа
                    char_name = ""
                    replica_text = full_text

                    colon_match = re.match(r'^([^:]+):\s*(.*)', full_text, re.DOTALL)
                    if colon_match:
                        char_name = colon_match.group(1).strip()
                        replica_text = colon_match.group(2).strip()

                    if replica_text:
                        lines.append({
                            'id': idx,
                            's': srt_time_to_seconds(start_time),
                            'e': srt_time_to_seconds(end_time),
                            'char': char_name,
                            'text': replica_text,
                            's_raw': start_time
                        })
                        idx += 1

                except (IndexError, ValueError) as e:
                    logger.warning(f"Skipping invalid SRT block: {e}")
                    continue

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
        if not source_path:
            return False, "Файл не найден"

        # Для DOCX файлов (которые не существуют на диске) сохраняем в новый ASS файл
        if not os.path.exists(source_path) or source_path.lower().endswith('.docx'):
            # Сохраняем как новый ASS файл
            if target_path is None:
                target_path = source_path.replace('.docx', '.ass') if source_path.lower().endswith('.docx') else f"{ep_num}.ass"
            return self.save_episode_to_ass_new(ep_num, memory_lines, target_path)

        save_path = target_path or source_path

        # Определяем тип файла
        if source_path.lower().endswith('.srt'):
            return self.save_episode_to_srt(ep_num, episodes, memory_lines, target_path)

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

    def save_episode_to_ass_new(
        self,
        ep_num: str,
        memory_lines: List[Dict[str, Any]],
        save_path: str
    ) -> Tuple[bool, str]:
        """
        Сохранение эпизода в новый ASS файл (для DOCX импорта)

        Args:
            ep_num: номер эпизода
            memory_lines: реплики из памяти
            save_path: путь для сохранения

        Returns:
            Tuple[success, message]
        """
        if not memory_lines:
            return False, "Нет данных для сохранения"

        # Стандартный заголовок ASS файла
        ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(ass_header)

                for line in memory_lines:
                    # Конвертируем секунды обратно в ASS формат времени
                    start_time = self._seconds_to_ass_time(line.get('s', 0))
                    end_time = self._seconds_to_ass_time(line.get('e', 0))
                    char = line.get('char', '')
                    text = line.get('text', '')

                    # Формат ASS: Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
                    # Name (Actor) - это имя персонажа
                    dialogue_line = f"Dialogue: 0,{start_time},{end_time},,{char},0,0,0,,{text}\n"
                    f.write(dialogue_line)

            logger.info(f"New ASS saved to {save_path}")
            return True, f"Серия {ep_num} сохранена в {save_path}"

        except Exception as e:
            logger.error(f"Error saving new ASS: {e}")
            return False, f"Ошибка записи: {e}"

    def _seconds_to_ass_time(self, seconds: float) -> str:
        """
        Конвертация секунд в формат времени ASS (H:MM:SS.mm)

        Args:
            seconds: время в секундах

        Returns:
            Строка времени в формате ASS
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    def save_episode_to_srt(
        self,
        ep_num: str,
        episodes: Dict[str, str],
        memory_lines: List[Dict[str, Any]],
        target_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Сохранение эпизода в SRT файл

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

        try:
            # Читаем оригинальный SRT для сохранения таймингов
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Разделяем на блоки
            blocks = re.split(r'\n\s*\n', content.strip())
            new_file_content = []
            line_idx = 0

            for block in blocks:
                block_lines = block.strip().split('\n')
                if len(block_lines) < 2:
                    continue

                try:
                    # Первая строка - номер
                    block_num = block_lines[0].strip()
                    
                    # Вторая строка - время
                    time_line = block_lines[1].strip()
                    
                    # Если есть данные для этой реплики
                    if line_idx < len(memory_lines):
                        current_data = memory_lines[line_idx]
                        # Формируем текст: "Имя: реплика" или просто "реплика"
                        if current_data.get('char'):
                            full_text = f"{current_data['char']}: {current_data['text']}"
                        else:
                            full_text = current_data['text']
                        
                        new_block = f"{block_num}\n{time_line}\n{full_text}"
                        new_file_content.append(new_block)
                        line_idx += 1
                    else:
                        # Сохраняем оригинальный блок
                        new_file_content.append(block.strip())
                        
                except Exception:
                    # Сохраняем оригинальный блок при ошибке
                    new_file_content.append(block.strip())

            # Записываем файл
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(new_file_content) + '\n')

            logger.info(f"SRT saved to {save_path}")
            return True, f"Серия {ep_num} сохранена"

        except Exception as e:
            logger.error(f"Error saving SRT: {e}")
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
