"""prisk.services.analysis_cache: 线程安全的分析快照缓存与三级局部重跑管理。"""

from __future__ import annotations

import copy
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
import threading
from typing import Any


@dataclass
class CachedSnapshot:
    """保存某次分析的 Git Diff (Stage03)、AST 结构 (Stage04) 及规则计算结果 (Stage05)。"""
    key: str
    change: dict[str, Any]
    structure: dict[str, Any]
    rule_record: dict[str, Any]
    config: dict[str, Any]
    created_at: str


class AnalysisSnapshotCache:
    """基于 LRU 淘汰策略的线程安全分析快照缓存。"""

    def __init__(self, max_size: int = 50, capacity: int | None = None) -> None:
        self.max_size = capacity if capacity is not None else max_size
        self._cache: OrderedDict[str, CachedSnapshot] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._tier1_reruns = 0
        self._tier2_rescores = 0

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def get(self, key: str) -> CachedSnapshot | None:
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            self._hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]

    def put(
        self,
        key: str,
        change: dict[str, Any],
        structure: dict[str, Any],
        rule_record: dict[str, Any],
        config: dict[str, Any],
    ) -> CachedSnapshot:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            snapshot = CachedSnapshot(
                key=key,
                change=change,
                structure=structure,
                rule_record=rule_record,
                config=copy.deepcopy(config),
                created_at=self._now_iso(),
            )
            self._cache[key] = snapshot
            return snapshot

    def update_rules(
        self,
        key: str,
        rule_record: dict[str, Any],
        config: dict[str, Any],
    ) -> bool:
        """当发生 Tier 1 重跑时，复用既有 Diff 与 AST，仅更新规则快照与配置。"""
        with self._lock:
            snapshot = self._cache.get(key)
            if snapshot is None:
                return False
            snapshot.rule_record = rule_record
            snapshot.config = copy.deepcopy(config)
            self._cache.move_to_end(key)
            return True

    def record_tier1(self) -> None:
        with self._lock:
            self._tier1_reruns += 1

    def record_tier2(self) -> None:
        with self._lock:
            self._tier2_rescores += 1

    def invalidate(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._tier1_reruns = 0
            self._tier2_rescores = 0

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = round(self._hits / total, 4) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "capacity": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": hit_ratio,
                "tier1_reruns": self._tier1_reruns,
                "tier2_rescores": self._tier2_rescores,
            }


_GLOBAL_CACHE = AnalysisSnapshotCache()


def get_analysis_cache() -> AnalysisSnapshotCache:
    return _GLOBAL_CACHE


def clear_analysis_cache() -> None:
    _GLOBAL_CACHE.clear()
