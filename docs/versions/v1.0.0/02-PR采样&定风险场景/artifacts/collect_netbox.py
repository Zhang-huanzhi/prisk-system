"""NetBox 规模调研：120 条分层样本，沿用 Saleor 试采样的记录格式。"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "Saleor"))
import collect_trial as ct

ct.REPO = HERE / "repos" / "netbox"
ct.CACHE = HERE / "repos" / "api-cache"
ct.JSONL_PATH = HERE / "netbox-survey.jsonl"
ct.TABLE_PATH = HERE / "NetBox场景表.md"
ct.SUMMARY_PATH = HERE / "netbox-summary.json"
ct.SELECTION_PATH = ct.CACHE / "selection.json"
ct.TABLE_HEADING = "# NetBox 试采样场景表"
ct.SAMPLE_LINE_COUNT = 120
ct.REPO_NAME = "netbox-community/netbox"
ct.SEED = 20261028
ct.TARGET = 120
ct.POOL_PER_WINDOW = 60
ct.WINDOWS = (
    ("2016-01-01", "2018-12-31"),
    ("2019-01-01", "2020-12-31"),
    ("2021-01-01", "2022-12-31"),
    ("2023-01-01", "2024-12-31"),
    ("2025-01-01", "2026-10-28"),
)
ct.SCENE_TEXT = {
    "api": ("接口行为", "REST API、GraphQL、serializer 或 API view 变化"),
    "auth": ("认证与权限", "users 应用、权限模块或 ObjectPermission 变化"),
    "data_transaction": ("数据与事务", "模型、迁移、事务或回滚变化"),
    "config_exception": ("配置与异常", "settings、configuration 或异常模块变化"),
}
ct.PERMISSION_RE = re.compile(
    r"ObjectPermission|PermissionRequired|has_perm\(|restrict_queryset|get_extra_permissions"
)

MERGED_TOTAL = 4287


def is_sample_bot(login: str) -> bool:
    name = (login or "").lower()
    if name.endswith("[bot]") or name.endswith("-bot"):
        return True
    return "dependabot" in name or "renovate" in name


def file_role(path: str) -> str:
    name = path.replace("\\", "/").lower()
    base = name.rsplit("/", 1)[-1]
    padded = f"/{name}"
    if "/tests/" in padded or "/test/" in padded or base.startswith("test_") or base.endswith("_test.py"):
        return "test"
    if name.startswith("netbox/") and name.endswith(".py") and "/static/" not in padded:
        return "business"
    return "other"


def tag_path(scenes: dict[str, dict[str, object]], path: str) -> None:
    lowered = path.lower()
    padded = f"/{lowered}"
    base = lowered.rsplit("/", 1)[-1]
    if "/api/" in padded or base in {"serializers.py", "viewsets.py"} or (base == "views.py" and "/api/" in padded):
        ct.add_signal(scenes, "api", path, "rest_api_path")
    if "/graphql/" in padded:
        ct.add_signal(scenes, "api", path, "graphql_path")
    if "/users/" in padded or "/authentication/" in padded:
        ct.add_signal(scenes, "auth", path, "users_path" if "/users/" in padded else "auth_path")
    if "permission" in base or "authentication" in base:
        ct.add_signal(scenes, "auth", path, "permission_path")
    if "/migrations/" in padded:
        ct.add_signal(scenes, "data_transaction", path, "migration_path")
    if lowered.endswith("/models.py") or lowered.endswith("/managers.py"):
        ct.add_signal(scenes, "data_transaction", path, "model_path")
    if lowered.endswith("/settings.py") or "/settings/" in padded:
        ct.add_signal(scenes, "config_exception", path, "settings_path")
    if "configuration" in base:
        ct.add_signal(scenes, "config_exception", path, "configuration_path")
    if "exception" in base:
        ct.add_signal(scenes, "config_exception", path, "exception_path")


def gh_json(args: list[str], cache_name: str | None = None, retries: int = 6) -> object:
    if cache_name:
        path = ct.CACHE / cache_name
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    last_error = ""
    for attempt in range(retries):
        result = ct.run(["gh", *args], timeout=180)
        if result.returncode == 0 and result.stdout.strip():
            payload = json.loads(result.stdout)
            if cache_name:
                ct.CACHE.mkdir(parents=True, exist_ok=True)
                (ct.CACHE / cache_name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            time.sleep(0.4)
            return payload
        last_error = (result.stderr or result.stdout or "gh 调用失败").strip()
        time.sleep(25 * (attempt + 1) if "rate limit" in last_error.lower() else 3)
    raise RuntimeError(last_error)


def self_test() -> None:
    assert file_role("netbox/dcim/api/serializers.py") == "business"
    assert file_role("netbox/dcim/tests/test_models.py") == "test"
    assert file_role("docs/release-notes.md") == "other"
    scenes = ct.empty_scenes()
    tag_path(scenes, "netbox/dcim/api/serializers.py")
    tag_path(scenes, "netbox/users/models.py")
    tag_path(scenes, "netbox/dcim/models.py")
    tag_path(scenes, "netbox/dcim/migrations/0001_initial.py")
    tag_path(scenes, "netbox/netbox/settings.py")
    tag_path(scenes, "netbox/netbox/configuration_example.py")
    assert scenes["api"]["hit"] is True
    assert "users_path" in scenes["auth"]["signals"]
    assert "model_path" in scenes["data_transaction"]["signals"]
    assert "migration_path" in scenes["data_transaction"]["signals"]
    assert "settings_path" in scenes["config_exception"]["signals"]
    assert "configuration_path" in scenes["config_exception"]["signals"]
    print("netbox self-test ok")


def main() -> None:
    ct.is_sample_bot = is_sample_bot
    ct.file_role = file_role
    ct.tag_path = tag_path
    ct.gh_json = gh_json
    if "--self-test" in __import__("sys").argv:
        self_test()
        return
    ct.main()
    if ct.SUMMARY_PATH.exists():
        summary = json.loads(ct.SUMMARY_PATH.read_text(encoding="utf-8"))
        selected = int(summary.get("selected_count") or 0)
        analyzable = int(summary.get("analyzable_count") or 0)
        rate = (analyzable / selected) if selected else 0
        summary["merged_total"] = MERGED_TOTAL
        summary["analyzable_rate"] = rate
        summary["estimated_analyzable"] = round(rate * MERGED_TOTAL)
        ct.SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {"estimated_analyzable": summary["estimated_analyzable"], "rate": round(rate, 3)},
                ensure_ascii=False,
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
