"""Constructed cases for the three high-value detectors landed in task 024:
- api.django_url_pattern_changed (backend_contract)
- code.assert_in_production (code_smell)
- code.mutable_default_argument (code_smell)
"""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from prisk.domain import third_batch_detectors as tbd
from prisk.domain.changes import parse_unified_diff, read_diff_text, read_name_status
from prisk.domain.rules import evaluate_rules
from prisk.domain.structure import extract_changed_structures
from tests.support import git, make_temp_dir


def init_repo() -> tuple[Path, Path]:
    root = make_temp_dir("prisk-024-")
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
        "pr_number": 24,
        "base_sha": base,
        "head_sha": head,
        "files": files,
    }
    return evaluate_rules(extract_changed_structures(record, repo))


def findings(result: dict, rule_id: str) -> list[dict]:
    return [item for item in result["findings"] if item["rule_id"] == rule_id]


def outcome(result: dict, rule_id: str) -> dict:
    return next(item for item in result["rule_outcomes"] if item["rule_id"] == rule_id)


# ==============================================================================
# 1. api.django_url_pattern_changed
# ==============================================================================

class DjangoUrlPatternChangedTests(unittest.TestCase):
    rule_id = tbd.URL_PATTERN_ID

    def test_url_pattern_changed_route_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/urls.py"
        base = commit(
            repo,
            path,
            "from django.urls import path\n"
            "from . import views\n\n"
            "urlpatterns = [\n"
            "    path('users/', views.UserView.as_view(), name='user-list'),\n"
            "]\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from django.urls import path\n"
            "from . import views\n\n"
            "urlpatterns = [\n"
            "    path('v2/users/', views.UserView.as_view(), name='user-list'),\n"
            "]\n",
            "change route",
        )
        result = evaluate_repo(repo, base, head)
        items = findings(result, self.rule_id)
        self.assertEqual(len(items), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")
        ev = items[0]["evidence"][0]
        self.assertEqual(ev.get("old_route"), "users/")
        self.assertEqual(ev.get("new_route"), "v2/users/")
        self.assertEqual(ev.get("change_kind"), "route_changed")

    def test_url_pattern_changed_view_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/urls.py"
        base = commit(
            repo,
            path,
            "from django.urls import path\n"
            "from . import views\n\n"
            "urlpatterns = [\n"
            "    path('items/', views.OldView.as_view(), name='items'),\n"
            "]\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from django.urls import path\n"
            "from . import views\n\n"
            "urlpatterns = [\n"
            "    path('items/', views.NewView.as_view(), name='items'),\n"
            "]\n",
            "change view",
        )
        result = evaluate_repo(repo, base, head)
        items = findings(result, self.rule_id)
        self.assertEqual(len(items), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")
        ev = items[0]["evidence"][0]
        self.assertEqual(ev.get("change_kind"), "view_changed")

    def test_url_pattern_changed_name_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/urls.py"
        base = commit(
            repo,
            path,
            "from django.urls import path\n"
            "from . import views\n\n"
            "urlpatterns = [\n"
            "    path('items/', views.ItemView.as_view(), name='old-items'),\n"
            "]\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from django.urls import path\n"
            "from . import views\n\n"
            "urlpatterns = [\n"
            "    path('items/', views.ItemView.as_view(), name='new-items'),\n"
            "]\n",
            "change name",
        )
        result = evaluate_repo(repo, base, head)
        items = findings(result, self.rule_id)
        self.assertEqual(len(items), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")
        ev = items[0]["evidence"][0]
        self.assertEqual(ev.get("old_name"), "old-items")
        self.assertEqual(ev.get("new_name"), "new-items")
        self.assertEqual(ev.get("change_kind"), "name_changed")

    def test_url_pattern_added_and_deleted_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/urls.py"
        base = commit(
            repo,
            path,
            "from rest_framework.routers import DefaultRouter\n"
            "router = DefaultRouter()\n"
            "router.register('roles', RoleViewSet, basename='roles')\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from django.urls import re_path\n"
            "urlpatterns = [\n"
            "    re_path(r'^devices/$', DeviceView.as_view(), name='devices'),\n"
            "]\n",
            "delete register and add re_path",
        )
        result = evaluate_repo(repo, base, head)
        items = findings(result, self.rule_id)
        self.assertEqual(len(items), 2)
        kinds = {item["evidence"][0].get("change_kind") for item in items}
        self.assertEqual(kinds, {"route_removed", "route_added"})
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")

    def test_url_pattern_formatting_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/urls.py"
        base = commit(
            repo,
            path,
            "from django.urls import path\n"
            "urlpatterns = [\n"
            "    path('users/', views.UserView.as_view(), name='users')\n"
            "]\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from django.urls import path\n"
            "urlpatterns = [\n"
            "    path('users/', views.UserView.as_view(), name='users'),  # added comma and comment\n"
            "]\n",
            "format only",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")

    def test_url_pattern_unanalyzed_on_url_callee(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/urls.py"
        base = commit(repo, path, "# empty\n", "base")
        head = commit(
            repo,
            path,
            "from django.conf.urls import url\n"
            "urlpatterns = [\n"
            "    url(r'^legacy/$', LegacyView.as_view()),\n"
            "]\n",
            "legacy url",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        item = outcome(result, self.rule_id)
        self.assertEqual(item["state"], "Unanalyzed")
        self.assertEqual(
            {r["reason"] for r in item["reasons"]},
            {"missing_framework_context"},
        )

    def test_url_pattern_unanalyzed_on_dynamic_route(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/urls.py"
        base = commit(repo, path, "# empty\n", "base")
        head = commit(
            repo,
            path,
            "from django.urls import path\n"
            "urlpatterns = [\n"
            "    path(get_prefix(), views.UserView.as_view()),\n"
            "]\n",
            "dynamic route",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        item = outcome(result, self.rule_id)
        self.assertEqual(item["state"], "Unanalyzed")
        self.assertEqual(
            {r["reason"] for r in item["reasons"]},
            {"unsupported_stage04_details"},
        )

    def test_url_pattern_unanalyzed_on_include_view_changed(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/urls.py"
        base = commit(
            repo,
            path,
            "from django.urls import path, include\n"
            "urlpatterns = [\n"
            "    path('api/', include('v1.urls')),\n"
            "]\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "from django.urls import path, include\n"
            "urlpatterns = [\n"
            "    path('api/', include('v2.urls')),\n"
            "]\n",
            "include changed",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        item = outcome(result, self.rule_id)
        self.assertEqual(item["state"], "Unanalyzed")
        self.assertEqual(
            {r["reason"] for r in item["reasons"]},
            {"missing_framework_context"},
        )


# ==============================================================================
# 2. code.assert_in_production
# ==============================================================================

class AssertInProductionTests(unittest.TestCase):
    rule_id = tbd.ASSERT_PROD_ID

    def test_assert_in_production_hits(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/views.py"
        base = commit(
            repo,
            path,
            "def handle_request(request):\n"
            "    return True\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "def handle_request(request):\n"
            "    assert request.user.is_authenticated, 'User not authenticated'\n"
            "    return True\n",
            "add assert",
        )
        result = evaluate_repo(repo, base, head)
        items = findings(result, self.rule_id)
        self.assertEqual(len(items), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")
        ev = items[0]["evidence"][0]
        self.assertEqual(ev.get("path_class"), "production")
        self.assertEqual(ev.get("test_expression"), "request.user.is_authenticated")
        self.assertEqual(ev.get("msg_expression"), "'User not authenticated'")

    def test_assert_in_tests_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/tests/test_views.py"
        base = commit(repo, path, "# empty\n", "base")
        head = commit(
            repo,
            path,
            "def test_view():\n"
            "    assert 1 == 1\n",
            "add assert in test",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")

    def test_assert_in_migrations_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/migrations/0002_auto.py"
        base = commit(repo, path, "# empty\n", "base")
        head = commit(
            repo,
            path,
            "def check_migration():\n"
            "    assert True\n",
            "add assert in migration",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")

    def test_assert_in_settings_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/settings.py"
        base = commit(repo, path, "# empty\n", "base")
        head = commit(
            repo,
            path,
            "DEBUG = True\n"
            "assert DEBUG, 'Debug must be enabled'\n",
            "add assert in settings",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")

    def test_assert_unchanged_not_hit(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/views.py"
        base = commit(
            repo,
            path,
            "assert True\n"
            "def foo():\n"
            "    return 1\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "assert True\n"
            "def foo():\n"
            "    return 2\n",
            "body changed only",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        item = outcome(result, self.rule_id)
        self.assertEqual(item["state"], "Unanalyzed")
        self.assertEqual({r["reason"] for r in item["reasons"]}, {"context_not_established"})


# ==============================================================================
# 3. code.mutable_default_argument
# ==============================================================================

class MutableDefaultArgumentTests(unittest.TestCase):
    rule_id = tbd.MUTABLE_DEFAULT_ID

    def test_mutable_default_function_displays_hit(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/helpers.py"
        base = commit(repo, path, "# empty\n", "base")
        head = commit(
            repo,
            path,
            "def append_item(val, items=[]):\n"
            "    items.append(val)\n"
            "    return items\n\n"
            "def config_map(cfg={}):\n"
            "    return cfg\n\n"
            "def set_tags(tags={1, 2}):\n"
            "    return tags\n",
            "mutable display defaults",
        )
        result = evaluate_repo(repo, base, head)
        items = findings(result, self.rule_id)
        self.assertEqual(len(items), 3)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")
        kinds = {item["evidence"][0].get("default_kind") for item in items}
        self.assertEqual(kinds, {"list_display", "dict_display", "set_display"})

    def test_mutable_default_calls_hit(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/helpers.py"
        base = commit(repo, path, "# empty\n", "base")
        head = commit(
            repo,
            path,
            "def with_list(items=list()):\n"
            "    return items\n\n"
            "def with_dict(data=dict()):\n"
            "    return data\n\n"
            "def with_set(tags=set()):\n"
            "    return tags\n",
            "mutable call defaults",
        )
        result = evaluate_repo(repo, base, head)
        items = findings(result, self.rule_id)
        self.assertEqual(len(items), 3)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")
        kinds = {item["evidence"][0].get("default_kind") for item in items}
        self.assertEqual(kinds, {"list_call", "dict_call", "set_call"})

    def test_mutable_default_async_function_hit(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/helpers.py"
        base = commit(repo, path, "# empty\n", "base")
        head = commit(
            repo,
            path,
            "async def fetch_all(headers={}):\n"
            "    return headers\n",
            "async function mutable default",
        )
        result = evaluate_repo(repo, base, head)
        items = findings(result, self.rule_id)
        self.assertEqual(len(items), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")
        self.assertEqual(items[0]["evidence"][0].get("default_kind"), "dict_display")

    def test_mutable_default_lambda_hit(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/helpers.py"
        base = commit(repo, path, "# empty\n", "base")
        head = commit(
            repo,
            path,
            "fn = lambda x, acc=[]: acc.append(x)\n",
            "lambda mutable default",
        )
        result = evaluate_repo(repo, base, head)
        items = findings(result, self.rule_id)
        self.assertEqual(len(items), 1)
        self.assertEqual(outcome(result, self.rule_id)["state"], "Hit")
        self.assertEqual(items[0]["evidence"][0].get("default_kind"), "list_display")

    def test_non_mutable_defaults_not_found(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/helpers.py"
        base = commit(repo, path, "# empty\n", "base")
        head = commit(
            repo,
            path,
            "def safe_fn(x=None, y=100, z='str', t=(1, 2)):\n"
            "    local_list = []\n"
            "    return local_list\n",
            "safe defaults",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        self.assertEqual(outcome(result, self.rule_id)["state"], "NotFound")

    def test_mutable_default_unchanged_not_hit(self) -> None:
        root, repo = init_repo()
        self.addCleanup(shutil.rmtree, root, True)
        path = "netbox/core/helpers.py"
        base = commit(
            repo,
            path,
            "def foo(items=[]):\n"
            "    return 1\n",
            "base",
        )
        head = commit(
            repo,
            path,
            "def foo(items=[]):\n"
            "    return 2\n",
            "body changed only",
        )
        result = evaluate_repo(repo, base, head)
        self.assertEqual(findings(result, self.rule_id), [])
        item = outcome(result, self.rule_id)
        self.assertEqual(item["state"], "Unanalyzed")
        self.assertEqual({r["reason"] for r in item["reasons"]}, {"context_not_established"})
