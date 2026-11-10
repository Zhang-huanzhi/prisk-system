from __future__ import annotations

import unittest

from prisk.domain.rules import RULE_CATALOG, evaluate_rules, validate_rule_catalog


def change(kind: str, change_type: str, node_id: str = "head:function:example:1", name: str = "example") -> dict:
    node = {
        "kind": kind,
        "node_id": node_id,
        "name": name,
        "qualified_name": "Example.example",
        "changed_lines": [12],
        "details": {"callee": name, "expression": name},
    }
    return {"type": change_type, "kind": kind, "node_id": node_id, "evidence_lines": [12], "after": node, "before": None}


def stage04(files: list[dict], **summary: bool) -> dict:
    return {
        "schema_version": "stage04.v1",
        "status": "ok",
        "repo": "netbox-community/netbox",
        "pr_number": 19,
        "files": files,
        "summary": {"business_changed": True, "test_changed": False, **summary},
    }


class RuleTests(unittest.TestCase):
    def test_catalog_has_structural_and_code_smell_rules(self) -> None:
        self.assertEqual(len(RULE_CATALOG), 29)
        self.assertEqual(
            {item["rule_id"] for item in RULE_CATALOG},
            {
                "api.signature_changed",
                "auth.permission_structure_changed",
                "data.transaction_structure_changed",
                "config.configuration_structure_changed",
                "code.exception_structure_changed",
                "code.swallowed_exception",
                "code.bare_exception",
                "code.dynamic_execution",
                "code.unmanaged_open",
                "code.deep_control_flow",
                "code.hardcoded_secret",
                "code.global_mutable_state",
                "data.django_raw_sql_execution",
                "workflow.test_collaboration_gap",
                "auth.django_csrf_exempt_added",
                "api.drf_viewset_action_changed",
                "data.django_destructive_migration",
                "auth.drf_permission_policy_downgrade",
                "config.django_sensitive_settings_changed",
                "data.django_non_null_constraint_tightened",
                "auth.drf_permission_decorator_removed",
                "auth.drf_queryset_scope_tighten_bypassed",
                "data.django_signal_receiver_leak",
                "data.django_field_rename_without_db_column",
                "api.drf_public_parameter_added",
                "api.drf_public_parameter_removed",
                "api.django_url_pattern_changed",
                "code.assert_in_production",
                "code.mutable_default_argument",
            },
        )
        self.assertTrue(all("scene" not in item for item in RULE_CATALOG))
        validate_rule_catalog()

    def test_interface_signature_rule_has_traceable_evidence(self) -> None:
        result = evaluate_rules(stage04([{
            "path": "netbox/dcim/api/views.py",
            "role": "business",
            "parse_status": {"file": "ok"},
            "structural_changes": [change("function", "signature_changed")],
        }]))
        finding = next(item for item in result["findings"] if item["rule_id"] == "api.signature_changed")
        self.assertEqual(finding["evidence"][0]["path"], "netbox/dcim/api/views.py")
        self.assertEqual(finding["evidence"][0]["lines"], [12])
        self.assertEqual(finding["confidence"], "structural")
        self.assertNotIn("scene", finding)
        self.assertEqual(result["summary"]["domains"], ["api"])

    def test_auth_data_and_config_rules(self) -> None:
        result = evaluate_rules(stage04([
            {"path": "netbox/users/permissions.py", "role": "business", "structural_changes": [change("function", "function_touched")]},
            {"path": "netbox/dcim/models.py", "role": "business", "structural_changes": [change("call", "call_touched", name="transaction.atomic")]},
            {"path": "netbox/netbox/settings.py", "role": "business", "structural_changes": [change("field", "field_modified")]},
            {"path": "netbox/core/handlers.py", "role": "business", "structural_changes": [change("except_handler", "exception_handler_changed")]},
        ]))
        ids = {item["rule_id"] for item in result["findings"]}
        self.assertIn("auth.permission_structure_changed", ids)
        self.assertIn("data.transaction_structure_changed", ids)
        self.assertIn("config.configuration_structure_changed", ids)
        self.assertIn("code.exception_structure_changed", ids)
        self.assertEqual(result["summary"]["domains"], ["auth", "code", "config", "data"])

    def test_collaboration_claim_without_file_stats_is_unanalyzed(self) -> None:
        result = evaluate_rules(stage04([]))
        self.assertFalse(result["summary"]["test_collaboration"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["summary"]["unanalyzed"], [{"path": "", "reason": "diff_stats_unavailable"}])

    def test_ast_only_stage04_does_not_award_collaboration(self) -> None:
        record = stage04([{"path": "netbox/core/models.py", "role": "business"}])
        record["summary"] = {}
        result = evaluate_rules(record)
        self.assertFalse(result["summary"]["test_collaboration"])
        self.assertEqual(result["summary"]["unanalyzed"], [])
        self.assertEqual(result["findings"], [])

    def test_excluded_and_error_records_propagate(self) -> None:
        excluded = evaluate_rules({"status": "excluded", "pr_number": 1})
        failed = evaluate_rules({"status": "error", "pr_number": 2, "errors": [{"code": "bad_input"}]})
        self.assertEqual(excluded["status"], "excluded")
        self.assertEqual(failed["status"], "error")
        self.assertEqual(failed["errors"][0]["code"], "bad_input")


if __name__ == "__main__":
    unittest.main()
