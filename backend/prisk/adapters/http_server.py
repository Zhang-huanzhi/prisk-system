"""Local read-only HTTP API for the Prisk teacher demo."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ..services.branch_analysis import analyze_branches
from ..services.demo_service import DemoData
from ..services.project_service import ProjectError, ProjectRegistry
from ..paths import frozen_sample_data_root


def build_parser() -> argparse.ArgumentParser:
    current = frozen_sample_data_root()
    parser = argparse.ArgumentParser(description="启动本地 Prisk 演示 API")
    parser.add_argument("--stage03", type=Path, default=current / "stage03-change-objects.jsonl")
    parser.add_argument("--stage04", type=Path, default=current / "stage04-structure-objects.jsonl")
    parser.add_argument("--stage05", type=Path, default=current / "stage05-rule-results.jsonl")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser


def create_handler(data: DemoData, projects: ProjectRegistry | None = None) -> type[BaseHTTPRequestHandler]:
    registry = projects or ProjectRegistry()

    class Handler(BaseHTTPRequestHandler):
        server_version = "PriskDemo/0.1"

        def _send(self, status: int, payload: dict) -> None:
            content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/health":
                self._send(200, {"status": "ok"})
            elif parsed.path == "/api/dataset":
                self._send(200, data.dataset())
            elif parsed.path.startswith("/api/pr/"):
                try:
                    number = int(parsed.path.rsplit("/", 1)[-1])
                    self._send(200, data.analyze(number))
                except (ValueError, KeyError) as exc:
                    self._send(404, {"error": str(exc)})
            elif parsed.path.startswith("/api/projects/") and parsed.path.endswith("/branches"):
                key = parsed.path.split("/")[3]
                try:
                    self._send(200, {"status": "ok", "project": registry.refresh(key)})
                except ProjectError as exc:
                    self._send(404, {"error": {"code": exc.code, "message": str(exc)}})
            else:
                self._send(404, {"error": "not_found"})

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 64_000:
                    raise ValueError("请求大小无效")
                body = json.loads(self.rfile.read(length))
                path = urlparse(self.path).path
                if path == "/api/projects/load":
                    project = registry.load(body["path"])
                    self._send(200, {"status": "ok", "project": project, "errors": []})
                    return
                if path == "/api/branch-analysis":
                    project = registry.get(str(body["project_id"]))
                    report = analyze_branches(
                        Path(project["path"]), str(body["base_ref"]), str(body["head_ref"]),
                        project=project, config=body.get("config"),
                    )
                    self._send(200, report)
                    return
                if path != "/api/analyze":
                    self._send(404, {"error": "not_found"})
                    return
                report = data.analyze(int(body["pr_number"]), body.get("config"))
            except KeyError as exc:
                self._send(400 if urlparse(self.path).path in {"/api/projects/load", "/api/branch-analysis"} else 404, {"error": str(exc)})
            except ProjectError as exc:
                status = 404 if exc.code in {"project_not_loaded", "ref_not_found"} else 400
                self._send(status, {"error": {"code": exc.code, "message": str(exc)}})
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self._send(400, {"error": str(exc)})
            else:
                self._send(200, report)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for path in (args.stage03, args.stage04, args.stage05):
        if not path.is_file():
            raise SystemExit(f"输入文件不存在: {path}")
    data = DemoData(args.stage03, args.stage04, args.stage05)
    server = ThreadingHTTPServer((args.host, args.port), create_handler(data, ProjectRegistry()))
    print(f"Prisk Demo API: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
