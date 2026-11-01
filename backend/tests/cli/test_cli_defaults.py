from __future__ import annotations

import unittest

from prisk.adapters.http_server import build_parser as build_web_parser
from prisk.cli.scoring_cli import build_parser as build_scoring_parser
from prisk.paths import demo_data_root, frozen_sample_data_root


class CliDefaultPathTests(unittest.TestCase):
    def test_web_defaults_use_project_local_demo_data(self) -> None:
        args = build_web_parser().parse_args([])
        self.assertEqual(args.stage03, frozen_sample_data_root() / "stage03-change-objects.jsonl")
        self.assertEqual(args.stage04, frozen_sample_data_root() / "stage04-structure-objects.jsonl")
        self.assertEqual(args.stage05, frozen_sample_data_root() / "stage05-rule-results.jsonl")
        self.assertTrue(all(path.is_file() for path in (args.stage03, args.stage04, args.stage05)))

    def test_scoring_defaults_use_project_local_demo_data(self) -> None:
        args = build_scoring_parser().parse_args(["--output", "report.jsonl", "--manifest", "manifest.json"])
        self.assertEqual(args.stage03, demo_data_root() / "stage03-change-objects.jsonl")
        self.assertEqual(args.stage04, demo_data_root() / "stage04-structure-objects.jsonl")
        self.assertEqual(args.stage05, demo_data_root() / "stage05-rule-results.jsonl")


if __name__ == "__main__":
    unittest.main()
