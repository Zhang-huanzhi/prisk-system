import json
import shutil
import subprocess
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from prisk.adapters.http_server import create_handler
from tests.support import git, make_temp_dir


class BranchApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = make_temp_dir("prisk-api-")
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "config", "user.email", "test@example.com")
        (self.repo / "netbox").mkdir()
        (self.repo / "netbox" / "views.py").write_text("def list_items():\n    return []\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "base")
        git(self.repo, "checkout", "-b", "feature/api")
        (self.repo / "netbox" / "views.py").write_text("def list_items(limit=10):\n    return []\n", encoding="utf-8")
        git(self.repo, "commit", "-am", "feature")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(None))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = HTTPConnection("127.0.0.1", self.server.server_port)

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        shutil.rmtree(self.repo, ignore_errors=True)

    def request(self, method, path, body=None):
        encoded = json.dumps(body).encode("utf-8") if body is not None else None
        self.connection.request(method, path, body=encoded, headers={"Content-Type": "application/json"} if encoded else {})
        response = self.connection.getresponse()
        return response.status, json.loads(response.read())

    def test_project_branch_analysis_and_refresh(self):
        status, loaded = self.request("POST", "/api/projects/load", {"path": str(self.repo)})
        self.assertEqual(status, 200)
        key = loaded["project"]["project_id"]
        status, branches = self.request("GET", f"/api/projects/{key}/branches")
        self.assertEqual(status, 200)
        self.assertEqual({item["ref"] for item in branches["project"]["branches"]}, {"main", "feature/api"})
        status, report = self.request("POST", "/api/branch-analysis", {"project_id": key, "base_ref": "main", "head_ref": "feature/api"})
        self.assertEqual(status, 200)
        self.assertEqual(report["schema_version"], "stage08.branch-report.v1")
        self.assertEqual(report["status"], "ok")
        self.assertTrue(report["files"][0]["hunks"])

    def test_missing_fields_return_client_error(self):
        status, _ = self.request("POST", "/api/projects/load", {})
        self.assertIn(status, {400, 404})
        status, _ = self.request("POST", "/api/branch-analysis", {})
        self.assertIn(status, {400, 404})

