"""Replica merge logic for exports."""

import re
from typing import Any, Dict, List

from utils.helpers import format_seconds_to_tc


class ReplicaMergeService:
    """Apply replica merge rules to episode lines."""

    PARALLEL_TIMECODE_MIN_PAUSE_SECONDS = 5.0

    def process(
        self,
        lines: List[Dict[str, Any]],
        cfg: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply replica merge rules."""
        if lines and all(line.get("_working_text") for line in lines):
            return [line.copy() for line in lines]

        p_short = cfg.get('p_short', 0.5)
        p_long = cfg.get('p_long', 2.0)
        fps = cfg.get('fps', 25.0)
        try:
            gap_seconds = float(cfg['merge_gap_seconds'])
        except (KeyError, TypeError, ValueError):
            gap_seconds = cfg.get('merge_gap', 5) / fps

        parallel_mode = bool(
            cfg.get('merge', True)
            and cfg.get('merge_parallel_replicas', False)
        )
        if parallel_mode:
            res = self._merge_parallel_sequences(
                lines, cfg, gap_seconds, p_short, p_long
            )
        else:
            res = self._merge_sequence(
                lines, cfg, gap_seconds, p_short, p_long
            )

        for item in res:
            if 'parts' in item:
                item['source_ids'] = [p['id'] for p in item['parts']]
                item['source_texts'] = [
                    p.get('source_text', p['text']) for p in item['parts']
                ]
            else:
                item['source_ids'] = [item.get('id')]
                item['source_texts'] = [item.get('text', '')]
            self._apply_inline_timecodes(item, cfg)

        if parallel_mode:
            self._apply_parallel_part_timecodes(res, cfg)
            for item in res:
                item.pop('_parallel_source_order', None)
                item.pop('_parallel_last_order', None)
                item.pop('_parallel_cross_merged', None)

        return res

    def _merge_parallel_sequences(
        self,
        lines: List[Dict[str, Any]],
        cfg: Dict[str, Any],
        gap_seconds: float,
        p_short: float,
        p_long: float,
    ) -> List[Dict[str, Any]]:
        """Merge per-character chains across genuinely overlapping events."""
        decorated = []
        by_character: Dict[str, List[Dict[str, Any]]] = {}
        for order, line in enumerate(lines):
            item = line.copy()
            item['_parallel_source_order'] = order
            decorated.append(item)
            character = str(item.get('char', '') or '')
            by_character.setdefault(character, []).append(item)

        result = []
        for character_lines in by_character.values():
            result.extend(self._merge_sequence(
                character_lines,
                cfg,
                gap_seconds,
                p_short,
                p_long,
                parallel_source=decorated,
            ))
        result.sort(key=lambda item: (
            float(item.get('s', 0.0) or 0.0),
            int(item.get('_parallel_source_order', 0) or 0),
        ))
        return result

    def _merge_sequence(
        self,
        lines: List[Dict[str, Any]],
        cfg: Dict[str, Any],
        gap_seconds: float,
        p_short: float,
        p_long: float,
        parallel_source: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        if not lines:
            return []

        result = []
        curr = self._start_merged_line(lines[0])
        for nxt in lines[1:]:
            diff = float(nxt['s']) - float(curr['e'])
            crosses_parallel_lines = False
            can_merge = bool(
                cfg.get('merge', True)
                and nxt.get('char') == curr.get('char')
                and diff < gap_seconds
            )
            if can_merge and parallel_source is not None:
                crosses_parallel_lines = self._crosses_source_lines(
                    curr, nxt
                )
                can_merge = self._parallel_gap_is_overlapped(
                    curr, nxt, parallel_source
                )

            if can_merge:
                if diff >= p_long:
                    separator = " //  "
                elif diff >= p_short:
                    separator = " /  "
                else:
                    separator = "  "
                next_text = str(nxt.get('text', '') or '')
                next_part = {
                    'id': nxt['id'],
                    'text': next_text,
                    'sep': separator,
                    'start': nxt.get('s', 0.0),
                    'end': nxt.get('e', nxt.get('s', 0.0)),
                    's_raw': nxt.get('s_raw', ''),
                }
                previous_part = curr['parts'][-1]
                previous_text = str(previous_part.get('text', '') or '')
                display_previous, display_next, separator = (
                    self._separator_aware_boundary(
                        previous_text,
                        next_text,
                        separator,
                        respect_existing=bool(
                            cfg.get('respect_existing_separators', False)
                        ),
                    )
                )
                if display_previous != previous_text:
                    previous_part.setdefault('source_text', previous_text)
                    previous_part['text'] = display_previous
                if display_next != next_text:
                    next_part['source_text'] = next_text
                    next_part['text'] = display_next
                next_part['sep'] = separator
                curr['parts'].append(next_part)
                curr['text'] = self._text_from_parts(curr['parts'])
                curr['e'] = max(float(curr['e']), float(nxt['e']))
                if crosses_parallel_lines:
                    curr['_parallel_cross_merged'] = True
                if '_parallel_source_order' in nxt:
                    curr['_parallel_last_order'] = int(
                        nxt['_parallel_source_order']
                    )
                continue

            result.append(curr)
            curr = self._start_merged_line(nxt)

        result.append(curr)
        return result

    @classmethod
    def _separator_aware_boundary(
        cls,
        previous_text: str,
        next_text: str,
        automatic_separator: str,
        respect_existing: bool,
    ) -> tuple[str, str, str]:
        """Format pause marks at a merged source boundary."""
        previous = cls._normalize_separator_runs(str(previous_text or ''))
        following = cls._normalize_separator_runs(str(next_text or ''))

        # Some prepared dubbing ASS files split the parenthetical ``(з/к)`` or
        # ``(в/к)`` marker itself between two Dialogue rows. It is one token,
        # not a pause boundary, so no generated divider belongs inside it.
        if respect_existing and ((
            re.search(r'\(\s*$', previous, flags=re.IGNORECASE)
            and re.match(r'^\s*[зв]/к\)', following, flags=re.IGNORECASE)
        ) or (
            re.search(r'\([зв]/\s*$', previous, flags=re.IGNORECASE)
            and re.match(r'^\s*к\)', following, flags=re.IGNORECASE)
        )):
            return previous.rstrip(), following.lstrip(), ''

        previous_body, trailing_level = cls._take_trailing_separators(previous)
        following_body, leading_level = cls._take_leading_separators(following)
        existing_level = (
            max(trailing_level, leading_level)
            if respect_existing
            else min(2, trailing_level + leading_level)
        )
        if not existing_level:
            return previous, following, automatic_separator
        automatic_level = cls._separator_level(automatic_separator)
        effective_level = (
            existing_level
            if respect_existing
            else min(2, existing_level + automatic_level)
        )
        return (
            previous_body,
            following_body,
            cls._pause_separator(effective_level),
        )

    @staticmethod
    def _normalize_separator_runs(text: str) -> str:
        """Render adjacent standalone pause marks as one compact ``//``."""
        return re.sub(
            r'(?<!\S)/{1,2}(?:[ \t]+/{1,2})+(?!\S)',
            '//',
            text,
        )

    @classmethod
    def _take_trailing_separators(cls, text: str) -> tuple[str, int]:
        match = re.search(
            r'(?P<markers>(?<!\S)/{1,2}(?:[ \t]+/{1,2})*)[ \t]*$',
            text,
        )
        if not match:
            return text, 0
        return text[:match.start()].rstrip(), cls._separator_level(
            match.group('markers')
        )

    @classmethod
    def _take_leading_separators(cls, text: str) -> tuple[str, int]:
        match = re.match(
            r'^[ \t]*(?P<markers>/{1,2}(?:[ \t]+/{1,2})*)(?!\S)[ \t]*',
            text,
        )
        if not match:
            return text, 0
        return text[match.end():].lstrip(), cls._separator_level(
            match.group('markers')
        )

    @staticmethod
    def _separator_level(markers: str) -> int:
        tokens = re.findall(r'/{1,2}', markers)
        if any(token == '//' for token in tokens) or len(tokens) > 1:
            return 2
        return 1 if tokens else 0

    @staticmethod
    def _pause_separator(level: int) -> str:
        # In particular, a long pause is always ``//`` rather than ``/ /``.
        return " //  " if level >= 2 else " /  "

    @staticmethod
    def _text_from_parts(parts: List[Dict[str, Any]]) -> str:
        return ''.join(
            f"{part.get('sep', '')}{part.get('text', '')}"
            for part in parts
            if isinstance(part, dict)
        )

    @staticmethod
    def _start_merged_line(line: Dict[str, Any]) -> Dict[str, Any]:
        item = line.copy()
        item['parts'] = [{
            'id': line['id'],
            'text': line['text'],
            'sep': '',
            'start': line.get('s', 0.0),
            'end': line.get('e', line.get('s', 0.0)),
            's_raw': line.get('s_raw', ''),
        }]
        if '_parallel_source_order' in line:
            item['_parallel_last_order'] = int(
                line['_parallel_source_order']
            )
        return item

    @staticmethod
    def _crosses_source_lines(
        current: Dict[str, Any],
        next_line: Dict[str, Any],
    ) -> bool:
        try:
            return int(next_line['_parallel_source_order']) > (
                int(current['_parallel_last_order']) + 1
            )
        except (KeyError, TypeError, ValueError):
            return False

    @staticmethod
    def _parallel_gap_is_overlapped(
        current: Dict[str, Any],
        next_line: Dict[str, Any],
        source_lines: List[Dict[str, Any]],
    ) -> bool:
        """Allow crossing only events that overlap the current/next replica."""
        try:
            previous_order = int(current['_parallel_last_order'])
            next_order = int(next_line['_parallel_source_order'])
            current_start = float(current.get('s', 0.0) or 0.0)
            current_end = float(current.get('e', current_start) or current_start)
            next_start = float(next_line.get('s', 0.0) or 0.0)
            next_end = float(next_line.get('e', next_start) or next_start)
        except (KeyError, TypeError, ValueError):
            return False
        if next_order <= previous_order + 1:
            return True

        for line in source_lines[previous_order + 1:next_order]:
            try:
                start = float(line.get('s', 0.0) or 0.0)
                end = float(line.get('e', start) or start)
            except (TypeError, ValueError):
                return False
            overlaps_current = start < current_end and end > current_start
            overlaps_next = start < next_end and end > next_start
            if not overlaps_current and not overlaps_next:
                return False
        return True

    @classmethod
    def _apply_parallel_part_timecodes(
        cls,
        lines: List[Dict[str, Any]],
        cfg: Dict[str, Any],
    ) -> None:
        """Add time cues before later parts of parallel-merged replicas."""
        cluster: List[Dict[str, Any]] = []
        cluster_end = 0.0
        for line in lines:
            try:
                start = float(line.get('s', 0.0) or 0.0)
                end = float(line.get('e', start) or start)
            except (TypeError, ValueError):
                start = 0.0
                end = 0.0
            if cluster and start >= cluster_end:
                cls._timecode_parallel_cluster(cluster, cfg)
                cluster = []
            cluster.append(line)
            cluster_end = max(cluster_end, end) if len(cluster) > 1 else end
        cls._timecode_parallel_cluster(cluster, cfg)

    @classmethod
    def _timecode_parallel_cluster(
        cls,
        cluster: List[Dict[str, Any]],
        cfg: Dict[str, Any],
    ) -> None:
        if not any(item.get('_parallel_cross_merged') for item in cluster):
            return
        for item in cluster:
            parts = item.get('parts')
            if isinstance(parts, list) and len(parts) > 1:
                # Derived display metadata. It deliberately stays out of the
                # project and lets consumers distinguish a parallel merge
                # from an ordinary same-character merge.
                item['parallel_merged'] = True
            cls._apply_parallel_item_timecodes(item, cfg)

    @classmethod
    def _apply_parallel_item_timecodes(
        cls,
        item: Dict[str, Any],
        cfg: Dict[str, Any],
    ) -> None:
        parts = item.get('parts')
        if not isinstance(parts, list) or len(parts) < 2:
            return
        inline_indices = {
            marker.get('part_index')
            for marker in item.get('inline_timecodes', [])
            if isinstance(marker, dict)
        }
        markers = []
        for index, part in enumerate(parts[1:], start=1):
            previous_part = parts[index - 1]
            if not isinstance(part, dict) or not isinstance(previous_part, dict):
                continue
            try:
                start = float(part.get('start', 0.0) or 0.0)
                previous_end = float(
                    previous_part.get('end', start) or start
                )
            except (TypeError, ValueError):
                continue
            pause = start - previous_end
            if pause <= cls.PARALLEL_TIMECODE_MIN_PAUSE_SECONDS:
                continue
            label, marker = cls._formatted_timecode_marker(start, cfg)
            if index not in inline_indices:
                separator = str(part.get('sep', '') or '')
                part['sep'] = f"{separator}{marker} "
            markers.append({
                'part_index': index,
                'source_id': part.get('id'),
                'start': start,
                'pause': pause,
                'label': label,
            })
        if markers:
            item.setdefault('content_text', str(item.get('text', '') or ''))
            item['text'] = cls._text_from_parts(parts)
            item['parallel_timecodes'] = markers

    @staticmethod
    def _formatted_timecode_marker(
        start: float,
        cfg: Dict[str, Any],
    ) -> tuple[str, str]:
        label = format_seconds_to_tc(start)
        if (
            cfg.get('hide_leading_timecode_zeros', False)
            and label.startswith('0:')
        ):
            label = label[2:]
        brackets = {
            'square': ('[', ']'),
            'round': ('(', ')'),
            'curly': ('{', '}'),
        }.get(
            str(cfg.get('inline_timecode_brackets', 'square')),
            ('[', ']'),
        )
        return label, f"{brackets[0]}{label}{brackets[1]}"

    @staticmethod
    def _apply_inline_timecodes(
        item: Dict[str, Any],
        cfg: Dict[str, Any],
    ) -> None:
        """Add derived timing cues between parts of a long merged replica."""
        if not cfg.get('inline_timecodes_enabled', False):
            return
        parts = item.get('parts')
        if not isinstance(parts, list):
            return
        try:
            minimum_duration = max(
                0.0, float(cfg.get('inline_timecode_min_duration', 30.0))
            )
            every = max(1, int(cfg.get('inline_timecode_every', 3)))
            duration = float(item.get('e', 0.0)) - float(item.get('s', 0.0))
        except (TypeError, ValueError):
            return
        if duration <= minimum_duration or len(parts) <= every:
            return

        chunks: List[str] = []
        markers = []
        for index, part in enumerate(parts):
            if not isinstance(part, dict):
                continue
            separator = str(part.get('sep', '') or '') if index else ''
            if index and index % every == 0:
                try:
                    start = float(part.get('start', 0.0) or 0.0)
                except (TypeError, ValueError):
                    start = 0.0
                label, marker = ReplicaMergeService._formatted_timecode_marker(
                    start, cfg
                )
                separator += f"{marker} "
                part['sep'] = separator
                markers.append({
                    'part_index': index,
                    'source_id': part.get('id'),
                    'start': start,
                    'label': label,
                })
            if separator:
                chunks.append(separator)
            chunks.append(str(part.get('text', '') or ''))
        if markers:
            item['content_text'] = str(item.get('text', '') or '')
            item['text'] = ''.join(chunks)
            item['inline_timecodes'] = markers
