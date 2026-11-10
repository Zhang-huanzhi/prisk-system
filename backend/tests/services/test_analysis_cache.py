import shutil
import unittest
from pathlib import Path

from prisk.domain.config import normalize_audit_config
from prisk.services.analysis_cache import (
    AnalysisSnapshotCache,
    CachedSnapshot,
    clear_analysis_cache,
    get_analysis_cache,
)
from prisk.services.branch_analysis import analyze_branches
from prisk.services.project_service import inspect_project
from tests.support import git, make_temp_dir


class AnalysisSnapshotCacheUnitTests(unittest.TestCase):
    def test_lru_eviction(self):
        cache = AnalysisSnapshotCache(capacity=3)
        cache.put("k1", {"diff": 1}, {"ast": 1}, {"rules": 1}, {})
        cache.put("k2", {"diff": 2}, {"ast": 2}, {"rules": 2}, {})
        cache.put("k3", {"diff": 3}, {"ast": 3}, {"rules": 3}, {})

        # Access k1 to make k2 the least recently used
        item1 = cache.get("k1")
        self.assertIsNotNone(item1)
        self.assertEqual(item1.change, {"diff": 1})

        # Insert k4, should evict k2
        cache.put("k4", {"diff": 4}, {"ast": 4}, {"rules": 4}, {})

        self.assertIsNone(cache.get("k2"))
        self.assertIsNotNone(cache.get("k1"))
        self.assertIsNotNone(cache.get("k3"))
        self.assertIsNotNone(cache.get("k4"))
        self.assertEqual(cache.size(), 3)

    def test_update_rules(self):
        cache = AnalysisSnapshotCache(capacity=10)
        cache.put("key1", {"diff": 1}, {"ast": 1}, {"rules": 1}, {"preset": "a"})
        updated = cache.update_rules("key1", {"rules": 2}, {"preset": "b"})
        self.assertTrue(updated)
        cached = cache.get("key1")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.rule_record, {"rules": 2})
        self.assertEqual(cached.config, {"preset": "b"})

        # Updating non-existent key returns False
        self.assertFalse(cache.update_rules("non_existent", {}, {}))

    def test_stats_and_counters(self):
        cache = AnalysisSnapshotCache(capacity=10)
        cache.put("k1", {}, {}, {}, {})
        self.assertIsNotNone(cache.get("k1"))  # hit
        self.assertIsNone(cache.get("k2"))  # miss

        cache.record_tier1()
        cache.record_tier2()
        cache.record_tier2()

        stats = cache.stats()
        self.assertEqual(stats["size"], 1)
        self.assertEqual(stats["capacity"], 10)
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["tier1_reruns"], 1)
        self.assertEqual(stats["tier2_rescores"], 2)

        cache.invalidate("k1")
        self.assertEqual(cache.size(), 0)

        cache.put("k2", {}, {}, {}, {})
        cache.clear()
        self.assertEqual(cache.size(), 0)


class BranchAnalysisCacheIntegrationTests(unittest.TestCase):
    def setUp(self):
        clear_analysis_cache()
        self.repo = make_temp_dir("prisk-cache-")
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "netbox").mkdir()
        (self.repo / "netbox" / "models.py").write_text("class Device:\n    name = 'old'\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "base")
        git(self.repo, "checkout", "-b", "feature/cache-demo")
        (self.repo / "netbox" / "models.py").write_text(
            "class Device:\n"
            "    name = 'new'\n"
            "    def check(self, a, b, c, d, e):\n"
            "        if a:\n"
            "            if b:\n"
            "                if c:\n"
            "                    if d:\n"
            "                        if e:\n"
            "                            return True\n",
            encoding="utf-8",
        )
        git(self.repo, "commit", "-am", "feature with deep nesting")
        git(self.repo, "checkout", "main")
        self.project = inspect_project(self.repo)

    def tearDown(self):
        clear_analysis_cache()
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_three_tier_partial_rerun_lifecycle(self):
        # 1. Initial call: Tier 0 (full run)
        report1 = analyze_branches(self.repo, "main", "feature/cache-demo", project=self.project)
        meta1 = report1.get("snapshot_meta", {})
        self.assertFalse(meta1["cache_hit"])
        self.assertEqual(meta1["rerun_tier"], "full_run")
        self.assertFalse(meta1["diff_reused"])
        self.assertFalse(meta1["ast_reused"])
        self.assertFalse(meta1["rules_reused"])
        score1 = report1["score"]

        # 2. Rescore only: Tier 2 (weight change only)
        custom_weights = {"code.deep_control_flow": 5}
        report2 = analyze_branches(
            self.repo, "main", "feature/cache-demo",
            project=self.project,
            config={"rule_weights": custom_weights},
        )
        meta2 = report2.get("snapshot_meta", {})
        self.assertTrue(meta2["cache_hit"])
        self.assertEqual(meta2["rerun_tier"], "stage07_rescore_only")
        self.assertTrue(meta2["diff_reused"])
        self.assertTrue(meta2["ast_reused"])
        self.assertTrue(meta2["rules_reused"])
        self.assertEqual(meta1["cache_key"], meta2["cache_key"])

        # 3. Rules rerun: Tier 1 (enabled_rules changed)
        report3 = analyze_branches(
            self.repo, "main", "feature/cache-demo",
            project=self.project,
            config={"enabled_rules": ["code.hardcoded_secret"]},
        )
        meta3 = report3.get("snapshot_meta", {})
        self.assertTrue(meta3["cache_hit"])
        self.assertEqual(meta3["rerun_tier"], "stage05_rules_rerun")
        self.assertTrue(meta3["diff_reused"])
        self.assertTrue(meta3["ast_reused"])
        self.assertFalse(meta3["rules_reused"])

        # 4. Explicit refresh=True: Tier 0
        report4 = analyze_branches(
            self.repo, "main", "feature/cache-demo",
            project=self.project,
            refresh=True,
        )
        meta4 = report4.get("snapshot_meta", {})
        self.assertFalse(meta4["cache_hit"])
        self.assertEqual(meta4["rerun_tier"], "full_run")
        self.assertFalse(meta4["diff_reused"])

        # 5. Commit change on branch: invalidation via new head_sha
        git(self.repo, "checkout", "feature/cache-demo")
        (self.repo / "netbox" / "models.py").write_text("class Device:\n    name = 'newest'\n", encoding="utf-8")
        git(self.repo, "commit", "-am", "new commit")
        git(self.repo, "checkout", "main")

        report5 = analyze_branches(self.repo, "main", "feature/cache-demo", project=self.project)
        meta5 = report5.get("snapshot_meta", {})
        self.assertFalse(meta5["cache_hit"])
        self.assertEqual(meta5["rerun_tier"], "full_run")
        self.assertNotEqual(meta1["cache_key"], meta5["cache_key"])
