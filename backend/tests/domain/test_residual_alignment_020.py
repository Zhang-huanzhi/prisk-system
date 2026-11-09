from __future__ import annotations

import unittest

from prisk.domain.framework_bases import resolve_class_bases, resolve_framework_base
from prisk.domain.gatekeeper import apply_gatekeeper_lift, gatekeeper_rules, structural_gatekeeper_hits
from prisk.domain.sensitive_settings import classify_sensitive_direction
from prisk.domain.structure import parse_python_source


class FrameworkBaseMappingTests(unittest.TestCase):
    def test_last_segment_equality_and_unlisted(self) -> None:
        self.assertEqual(resolve_framework_base("PrimaryModelSerializer")["native_base"], "ModelSerializer")
        self.assertEqual(resolve_framework_base("netbox.api.NetBoxModelViewSet")["native_base"], "ModelViewSet")
        self.assertEqual(resolve_framework_base("NetBoxModel")["status"], "mapped")
        self.assertEqual(resolve_framework_base("ModelSerializer")["status"], "native")
        unlisted = resolve_framework_base("RackBaseSerializer")
        self.assertEqual(unlisted["status"], "unlisted")
        self.assertIsNone(unlisted["native_base"])
        resolved = resolve_class_bases(["PrimaryModelSerializer", "RackBaseSerializer"])
        self.assertEqual(resolved["native_or_mapped_bases"], ["ModelSerializer"])
        self.assertEqual(resolved["unlisted_last_segments"], ["RackBaseSerializer"])

    def test_structure_records_mapped_bases(self) -> None:
        source = (
            "class DeviceSerializer(PrimaryModelSerializer):\n"
            "    class Meta:\n"
            '        fields = ("id", "name")\n'
        )
        parsed = parse_python_source(source, "api.py", "head")
        klass = next(node for node in parsed["nodes"] if node["kind"] == "class")
        self.assertIn("ModelSerializer", klass["details"]["native_or_mapped_bases"])
        meta_fields = next(
            node for node in parsed["nodes"]
            if node["kind"] == "field" and node["name"] == "fields"
        )
        self.assertEqual(meta_fields["details"]["meta_list_members"], ["id", "name"])
        self.assertTrue(meta_fields["details"]["meta_list_readable"])


class DefaultKeywordReadingTests(unittest.TestCase):
    def test_field_and_call_default_presence(self) -> None:
        source = (
            "class Asset(models.Model):\n"
            "    tag = models.CharField(max_length=50, null=True)\n"
            '    code = models.CharField(max_length=10, default="")\n'
        )
        parsed = parse_python_source(source, "models.py", "head")
        fields = {node["name"]: node for node in parsed["nodes"] if node["kind"] == "field"}
        self.assertTrue(fields["tag"]["details"]["has_null_keyword"])
        self.assertFalse(fields["tag"]["details"]["has_default_keyword"])
        self.assertEqual(fields["tag"]["details"]["null_literal"], True)
        self.assertTrue(fields["code"]["details"]["has_default_keyword"])
        self.assertEqual(fields["code"]["details"]["default_literal"]["literal_kind"], "str")
        calls = [node for node in parsed["nodes"] if node["kind"] == "call"]
        self.assertTrue(any(node["details"].get("has_default_keyword") for node in calls))


class SensitiveDirectionTests(unittest.TestCase):
    def test_debug_loosen_and_tighten(self) -> None:
        hit = classify_sensitive_direction("DEBUG", base_segment="DEBUG = False", head_segment="DEBUG = True")
        self.assertEqual(hit["direction"], "hit")
        tightened = classify_sensitive_direction("DEBUG", base_segment="DEBUG = True", head_segment="DEBUG = False")
        self.assertEqual(tightened["direction"], "not_found")
        unclear = classify_sensitive_direction("DEBUG", base_segment="DEBUG = flag", head_segment="DEBUG = other")
        self.assertEqual(unclear["direction"], "unanalyzed")


class GatekeeperLiftTests(unittest.TestCase):
    def test_registry_exposes_destructive_and_allowany(self) -> None:
        rules = gatekeeper_rules()
        self.assertIn("data.django_destructive_migration", rules)
        self.assertIn("auth.drf_permission_policy_downgrade", rules)

    def test_structural_delete_model_lifts_risk(self) -> None:
        stage = {
            "files": [{
                "path": "app/migrations/0002_drop.py",
                "nodes": [{
                    "kind": "call",
                    "side": "head",
                    "node_id": "head:call:1",
                    "changed_lines": [3],
                    "details": {"callee": "migrations.DeleteModel", "direct_callee_name": None},
                    "source_segment": 'migrations.DeleteModel(name="Asset")',
                }],
            }]
        }
        hits = structural_gatekeeper_hits(stage)
        self.assertEqual(hits[0]["rule_id"], "data.django_destructive_migration")
        level, basis = apply_gatekeeper_lift(risk_level="low", findings=[], stage_record=stage)
        self.assertEqual(level, "high")
        self.assertTrue(basis["gatekeeper_lift"])

    def test_allowany_segment_lifts_risk(self) -> None:
        stage = {
            "files": [{
                "path": "api/views.py",
                "nodes": [{
                    "kind": "field",
                    "side": "head",
                    "node_id": "head:field:1",
                    "changed_lines": [2],
                    "details": {},
                    "source_segment": "permission_classes = [AllowAny]",
                }],
            }]
        }
        level, basis = apply_gatekeeper_lift(risk_level="medium", findings=[], stage_record=stage)
        self.assertEqual(level, "high")
        self.assertIn("auth.drf_permission_policy_downgrade", basis["gatekeeper_structural_rule_ids"])


if __name__ == "__main__":
    unittest.main()
