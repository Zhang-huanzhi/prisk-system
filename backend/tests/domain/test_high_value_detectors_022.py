"""Constructed cases for the six high-value detectors landed in task 022."""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from prisk.domain.changes import parse_unified_diff, read_diff_text, read_name_status
from prisk.domain.rules import evaluate_rules
from prisk.domain.structure import extract_changed_structures
from tests.support import git, make_temp_dir


def init_repo() -> tuple[Path, Path]:
    root = make_temp_dir("prisk-022-")
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
        "pr_number": 22,
        "base_sha": base,
        "head_sha": head,
        "files": files,
    }
    return evaluate_rules(extract_changed_structures(record, repo))


def findings(result: dict, rule_id: str) -> list[dict]:
    return [item for item in result["findings"] if item["rule_id"] == rule_id]


def outcome(result: dict, rule_id: str) -> dict:
    return next(item for item in result["rule_outcomes"] if item["rule_id"] == rule_id)


class PermissionDecoratorRemovedTests(unittest.TestCase):
    rule_id = "auth.drf_permission_decorator_removed"

    def test_removed_permission_classes_decorator_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/views.py"
        base = commit(
            repo,
            path,
            "from rest_framework.decorators import permission_classes\n"
            "from rest_framework.permissions import IsAuthenticated\n\n"
            "@permission_classes([IsAuthenticated])\n"
            "def endpoint(request):\n"
            "    return 1\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "def endpoint(request):\n"
            "    return 2\n",
            "remove decorator",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(len(findings(result, self.rule_id)), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_action_decorator_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/views.py"
        base = commit(
            repo,
            path,
            "from rest_framework.decorators import action\n\n"
            "class V:\n"
            "    @action(detail=True)\n"
            "    def export(self, request):\n"
            "        return 1\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "class V:\n"
            "    def export(self, request):\n"
            "        return 2\n",
            "remove action",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")

    def test_same_file_permission_classes_assign_unanalyzed(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/views.py"
        base = commit(
            repo,
            path,
            "from rest_framework.decorators import permission_classes\n"
            "from rest_framework.permissions import IsAuthenticated\n"
            "from rest_framework.views import APIView\n\n"
            "@permission_classes([IsAuthenticated])\n"
            "def endpoint(request):\n"
            "    return 1\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from rest_framework.permissions import IsAuthenticated\n"
            "from rest_framework.views import APIView\n\n"
            "def endpoint(request):\n"
            "    return 2\n\n"
            "class OtherView(APIView):\n"
            "    permission_classes = [IsAuthenticated]\n",
            "suppress",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        item = outcome(result, self.rule_id)
        self.assertEqual(item["state"], "Unanalyzed")
        self.assertEqual(item["reasons"][0]["reason"], "missing_framework_context")


class QuerysetBypassTests(unittest.TestCase):
    rule_id = "auth.drf_queryset_scope_tighten_bypassed"

    def test_objects_all_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/views.py"
        base = commit(
            repo,
            path,
            "from rest_framework.viewsets import ModelViewSet\n\n"
            "class DeviceViewSet(ModelViewSet):\n"
            "    def get_queryset(self):\n"
            "        return super().get_queryset()\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from rest_framework.viewsets import ModelViewSet\n\n"
            "class DeviceViewSet(ModelViewSet):\n"
            "    def get_queryset(self):\n"
            "        return Device.objects.all()\n",
            "bypass",
        )
        result = evaluate_repo(repo, base, head)
        matched = findings(result, self.rule_id)
        self.assertEqual(len(matched), 1)
        self.assertTrue(matched[0]["evidence"][0].get("super_removed"))
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_accounts_all_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/views.py"
        base = commit(
            repo,
            path,
            "from rest_framework.viewsets import ModelViewSet\n\n"
            "class DeviceViewSet(ModelViewSet):\n"
            "    def get_queryset(self):\n"
            '        return Device.objects.filter(status="active")\n',
            "base",
        )
        head = commit(
            repo,
            path,
            "from rest_framework.viewsets import ModelViewSet\n\n"
            "class DeviceViewSet(ModelViewSet):\n"
            "    def get_queryset(self):\n"
            "        return request.user.accounts.all()\n",
            "accounts",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")

    def test_unlisted_base_unanalyzed(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/views.py"
        base = commit(
            repo,
            path,
            "class DeviceViewSet(ProjectViewSet):\n"
            "    def get_queryset(self):\n"
            "        return super().get_queryset()\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "class DeviceViewSet(ProjectViewSet):\n"
            "    def get_queryset(self):\n"
            "        return Device.objects.all()\n",
            "change",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "Unanalyzed")


class SignalLeakTests(unittest.TestCase):
    rule_id = "data.django_signal_receiver_leak"

    def test_connect_without_dispatch_uid_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/apps.py"
        base = commit(repo, path, "def ready():\n    x = 1\n", "base")
        head = commit(
            repo,
            path,
            "from django.db.models.signals import post_save\n\n"
            "def ready():\n"
            "    post_save.connect(on_save, sender=Device)\n",
            "connect",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(len(findings(result, self.rule_id)), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_dispatch_uid_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/apps.py"
        base = commit(repo, path, "def ready():\n    x = 1\n", "base")
        head = commit(
            repo,
            path,
            "from django.db.models.signals import post_save\n\n"
            "def ready():\n"
            '    post_save.connect(on_save, sender=Device, dispatch_uid="device-save")\n',
            "with uid",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")

    def test_request_finished_unanalyzed(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/apps.py"
        base = commit(repo, path, "def ready():\n    x = 1\n", "base")
        head = commit(
            repo,
            path,
            "from django.core.signals import request_finished\n\n"
            "def ready():\n"
            "    request_finished.connect(on_done)\n",
            "outside",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "Unanalyzed")


class FieldRenameTests(unittest.TestCase):
    rule_id = "data.django_field_rename_without_db_column"

    def test_rename_without_db_column_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/models.py"
        base = commit(
            repo,
            path,
            "from django.db import models\n\n"
            "class Device(models.Model):\n"
            "    asset_tag = models.CharField(max_length=50)\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from django.db import models\n\n"
            "class Device(models.Model):\n"
            "    tag = models.CharField(max_length=50)\n",
            "rename",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(len(findings(result, self.rule_id)), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_db_column_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/models.py"
        base = commit(
            repo,
            path,
            "from django.db import models\n\n"
            "class Device(models.Model):\n"
            "    asset_tag = models.CharField(max_length=50)\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from django.db import models\n\n"
            "class Device(models.Model):\n"
            '    tag = models.CharField(max_length=50, db_column="asset_tag")\n',
            "with column",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")


class ParameterAddedTests(unittest.TestCase):
    rule_id = "api.drf_public_parameter_added"

    def test_required_true_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/serializers.py"
        base = commit(
            repo,
            path,
            "from rest_framework import serializers\n\n"
            "class DeviceSerializer(serializers.Serializer):\n"
            "    name = serializers.CharField()\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from rest_framework import serializers\n\n"
            "class DeviceSerializer(serializers.Serializer):\n"
            "    name = serializers.CharField()\n"
            "    asset_tag = serializers.CharField(required=True)\n",
            "add required",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(len(findings(result, self.rule_id)), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_required_false_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/serializers.py"
        base = commit(
            repo,
            path,
            "from rest_framework import serializers\n\n"
            "class DeviceSerializer(serializers.Serializer):\n"
            "    name = serializers.CharField()\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from rest_framework import serializers\n\n"
            "class DeviceSerializer(serializers.Serializer):\n"
            "    name = serializers.CharField()\n"
            "    asset_tag = serializers.CharField(required=False)\n",
            "optional",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")

    def test_omitted_required_unanalyzed(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/serializers.py"
        base = commit(
            repo,
            path,
            "from rest_framework import serializers\n\n"
            "class DeviceSerializer(serializers.Serializer):\n"
            "    name = serializers.CharField()\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from rest_framework import serializers\n\n"
            "class DeviceSerializer(serializers.Serializer):\n"
            "    name = serializers.CharField()\n"
            "    asset_tag = serializers.CharField()\n",
            "omit",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "Unanalyzed")


class ParameterRemovedTests(unittest.TestCase):
    rule_id = "api.drf_public_parameter_removed"

    def test_field_removed_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/serializers.py"
        base = commit(
            repo,
            path,
            "from rest_framework import serializers\n\n"
            "class DeviceSerializer(serializers.Serializer):\n"
            "    name = serializers.CharField()\n"
            "    asset_tag = serializers.CharField(required=False)\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from rest_framework import serializers\n\n"
            "class DeviceSerializer(serializers.Serializer):\n"
            "    name = serializers.CharField()\n",
            "remove",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(len(findings(result, self.rule_id)), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_meta_fields_member_removed_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/api/serializers.py"
        base = commit(
            repo,
            path,
            "from rest_framework import serializers\n\n"
            "class DeviceSerializer(serializers.ModelSerializer):\n"
            "    class Meta:\n"
            "        model = Device\n"
            '        fields = ("id", "asset_tag")\n',
            "base",
        )
        head = commit(
            repo,
            path,
            "from rest_framework import serializers\n\n"
            "class DeviceSerializer(serializers.ModelSerializer):\n"
            "    class Meta:\n"
            "        model = Device\n"
            '        fields = ("id",)\n',
            "meta",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(len(findings(result, self.rule_id)), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_helper_without_decorator_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/dcim/utils.py"
        base = commit(
            repo,
            path,
            "def export(queryset, output=\"json\"):\n"
            "    return output\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "def export(queryset):\n"
            "    return \"json\"\n",
            "drop",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        # No applicable surface examined → Unanalyzed missing context is acceptable;
        # helper without decorator should not Hit.
        self.assertNotEqual(outcome(result, self.rule_id)["state"], "Hit")


if __name__ == "__main__":
    unittest.main()
