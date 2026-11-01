"""共享测试辅助：所有临时仓库都创建在系统临时目录。"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def make_temp_dir(prefix: str = "prisk-test-") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=path, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()
