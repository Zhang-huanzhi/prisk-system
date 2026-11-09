"""Constructed cases for the six high-value detectors landed in task 021."""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from prisk.domain.changes import parse_unified_diff, read_diff_text, read_name_status
from prisk.domain.rules import evaluate_rules
from prisk.domain.structure import extract_changed_structures
from tests.support import git, make_temp_dir


def init_repo() -> tuple[Path, Path]:
    root = make_temp_dir("prisk-021-")
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Prisk Test")
    git(repo, "config", "user.email", "prisk@example.invalid")
    return root, repo


def commit(repo: Path, relative: str, source: str, message: str) -> str:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    git(repo, "add", relative)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def evaluate_repo(repo: Path, base: str, head: str) -> dict:
    files = parse_unified_diff(read_diff_text(repo, base, head), read_name_status(repo, base, head))
    record = {
        "schema_version": "stage03.v1",
        "status": "ok",
        "repo": "example/example",
        "pr_number": 21,
        "base_sha": base,
        "head_sha": head,
        "files": files,
    }
    return evaluate_rules(extract_changed_structures(record, repo))


def findings(result: dict, rule_id: str) -> list[dict]:
    return [item for item in result["findings"] if item["rule_id"] == rule_id]


def outcome(result: dict, rule_id: str) -> dict:
    return next(item for item in result["rule_outcomes"] if item["rule_id"] == rule_id)


class CsrfExemptTests(unittest.TestCase):
    rule_id = "auth.django_csrf_exempt_added"

    def test_added_csrf_exempt_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/views.py"
        base = commit(repo, path, "def webhook(request):\n    return None\n", "base")
        head = commit(
            repo,
            path,
            "from django.views.decorators.csrf import csrf_exempt\n\n@csrf_exempt\ndef webhook(request):\n    return None\n",
            "add csrf",
        )
        result = evaluate_repo(repo, base, head)
        matched = findings(result, self.rule_id)
        self.assertEqual(len(matched), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_preexisting_csrf_exempt_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/views.py"
        source = "from django.views.decorators.csrf import csrf_exempt\n\n@csrf_exempt\ndef webhook(request):\n    return 1\n"
        base = commit(repo, path, source, "base")
        head = commit(
            repo,
            path,
            "from django.views.decorators.csrf import csrf_exempt\n\n@csrf_exempt\ndef webhook(request):\n    return 2\n",
            "body only",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")

    def test_alias_is_unanalyzed(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/views.py"
        base = commit(repo, path, "def webhook(request):\n    return None\n", "base")
        head = commit(
            repo,
            path,
            "from django.views.decorators.csrf import csrf_exempt as skip_csrf\n\n@skip_csrf\ndef webhook(request):\n    return None\n",
            "alias",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        item = outcome(result, self.rule_id)
        self.assertEqual(item["state"], "Unanalyzed")
        self.assertEqual(item["reasons"][0]["reason"], "missing_framework_context")


class ViewSetActionTests(unittest.TestCase):
    rule_id = "api.drf_viewset_action_changed"

    def test_destroy_removed_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/views.py"
        base = commit(
            repo,
            path,
            "from rest_framework.viewsets import ModelViewSet\n\nclass DeviceViewSet(ModelViewSet):\n    def destroy(self, request, *args, **kwargs):\n        pass\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from rest_framework.viewsets import ModelViewSet\n\nclass DeviceViewSet(ModelViewSet):\n    def list(self, request, *args, **kwargs):\n        pass\n",
            "swap",
        )
        result = evaluate_repo(repo, base, head)
        matched = findings(result, self.rule_id)
        self.assertTrue(matched)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_unlisted_base_unanalyzed(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/views.py"
        base = commit(
            repo,
            path,
            "class DeviceViewSet(BaseDeviceViewSet):\n    def destroy(self, request):\n        pass\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "class DeviceViewSet(BaseDeviceViewSet):\n    def list(self, request):\n        pass\n",
            "change",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "Unanalyzed")


class DestructiveMigrationTests(unittest.TestCase):
    rule_id = "data.django_destructive_migration"

    def test_delete_model_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/migrations/0004_drop.py"
        base = commit(repo, path, "operations = []\n", "base")
        head = commit(
            repo,
            path,
            'from django.db import migrations\n\noperations = [\n    migrations.DeleteModel(name="Asset"),\n]\n',
            "drop",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(len(findings(result, self.rule_id)), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_runsql_unanalyzed(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/migrations/0005_raw.py"
        base = commit(repo, path, "operations = []\n", "base")
        head = commit(
            repo,
            path,
            'from django.db import migrations\n\noperations = [\n    migrations.RunSQL("DROP TABLE dcim_device"),\n]\n',
            "runsql",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "Unanalyzed")


class PermissionDowngradeTests(unittest.TestCase):
    rule_id = "auth.drf_permission_policy_downgrade"

    def test_allowany_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/views.py"
        base = commit(
            repo,
            path,
            "from rest_framework.permissions import IsAuthenticated\nfrom rest_framework.viewsets import ModelViewSet\n\nclass V(ModelViewSet):\n    permission_classes = [IsAuthenticated]\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from rest_framework.permissions import AllowAny\nfrom rest_framework.viewsets import ModelViewSet\n\nclass V(ModelViewSet):\n    permission_classes = [AllowAny]\n",
            "down",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(len(findings(result, self.rule_id)), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_non_total_order_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/views.py"
        base = commit(
            repo,
            path,
            "from rest_framework.permissions import IsAuthenticated\nfrom rest_framework.viewsets import ModelViewSet\n\nclass V(ModelViewSet):\n    permission_classes = [IsAuthenticated]\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from rest_framework.permissions import IsAdminUser\nfrom rest_framework.viewsets import ModelViewSet\n\nclass V(ModelViewSet):\n    permission_classes = [IsAdminUser]\n",
            "swap",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")


class SensitiveSettingsTests(unittest.TestCase):
    rule_id = "config.django_sensitive_settings_changed"

    def test_debug_true_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/netbox/settings.py"
        base = commit(repo, path, "DEBUG = False\nALLOWED_HOSTS = ['x']\n", "base")
        head = commit(repo, path, "DEBUG = True\nALLOWED_HOSTS = ['x']\n", "loose")
        result = evaluate_repo(repo, base, head)
        self.assertEqual(len(findings(result, self.rule_id)), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_debug_tighten_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/netbox/settings.py"
        base = commit(repo, path, "DEBUG = True\n", "base")
        head = commit(repo, path, "DEBUG = False\n", "tight")
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")


class NonNullTests(unittest.TestCase):
    rule_id = "data.django_non_null_constraint_tightened"

    def test_null_true_removed_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/models.py"
        base = commit(
            repo,
            path,
            "from django.db import models\n\nclass Asset(models.Model):\n    tag = models.CharField(max_length=50, null=True)\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from django.db import models\n\nclass Asset(models.Model):\n    tag = models.CharField(max_length=50)\n",
            "tighten",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(len(findings(result, self.rule_id)), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_default_present_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/models.py"
        base = commit(
            repo,
            path,
            "from django.db import models\n\nclass Asset(models.Model):\n    tag = models.CharField(max_length=50, null=True)\n",
            "base",
        )
        head = commit(
            repo,
            path,
            'from django.db import models\n\nclass Asset(models.Model):\n    tag = models.CharField(max_length=50, default="")\n',
            "with default",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")


if __name__ == "__main__":
    unittest.main()
