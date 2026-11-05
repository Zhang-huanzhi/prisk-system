from __future__ import annotations

import unittest

from prisk.adapters.http_server import build_parser as build_web_parser
from prisk.cli.scoring_cli import build_parser as build_scoring_parser
from prisk.paths import demo_data_root, frozen_sample_data_root, project_root
from prisk.services.demo_service import DemoData


class CliDefaultPathTests(unittest.TestCase):
    def test_web_defaults_use_project_local_demo_data(self) -> None:
        stage03 = demo_data_root() / "stage03-change-objects.jsonl"
        stage04 = demo_data_root() / "stage04-structure-objects.jsonl"
        stage05 = demo_data_root() / "stage05-rule-results.jsonl"
        args = build_web_parser().parse_args([])
        self.assertEqual(args.stage03, stage03)
        self.assertEqual(args.stage04, stage04)
        self.assertEqual(args.stage05, stage05)
        self.assertNotEqual(args.stage04.parent, frozen_sample_data_root())
        self.assertTrue(all(path.is_file() for path in (args.stage03, args.stage04, args.stage05)))
        dataset = DemoData(args.stage03, args.stage04, args.stage05).dataset()
        self.assertGreaterEqual(dataset["counts"]["records"], 1)
        self.assertTrue(dataset["rules"])

    def test_frozen_netbox_sample_root_stays_available_for_explicit_use(self) -> None:
        frozen = frozen_sample_data_root()
        self.assertEqual(frozen, project_root() / "backend" / "data" / "frozen-netbox")
        stage04 = frozen / "stage04-structure-objects.jsonl"
        args = build_web_parser().parse_args([
            "--stage03", str(frozen / "stage03-change-objects.jsonl"),
            "--stage04", str(stage04),
            "--stage05", str(frozen / "stage05-rule-results.jsonl"),
        ])
        self.assertEqual(args.stage03, frozen / "stage03-change-objects.jsonl")
        self.assertEqual(args.stage04, stage04)
        self.assertEqual(args.stage05, frozen / "stage05-rule-results.jsonl")
        self.assertNotEqual(build_web_parser().parse_args([]).stage04, stage04)

    def test_scoring_defaults_use_project_local_demo_data(self) -> None:
        args = build_scoring_parser().parse_args(["--output", "report.jsonl", "--manifest", "manifest.json"])
        self.assertEqual(args.stage03, demo_data_root() / "stage03-change-objects.jsonl")
        self.assertEqual(args.stage04, demo_data_root() / "stage04-structure-objects.jsonl")
        self.assertEqual(args.stage05, demo_data_root() / "stage05-rule-results.jsonl")


if __name__ == "__main__":
    unittest.main()
