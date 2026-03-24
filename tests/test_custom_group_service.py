"""
Unit tests for CustomGroupService persistence and dedupe behavior.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api.services.custom_group_service import CustomGroupService
from src.xray_prism.models import ProxyNode, Protocol


class TestCustomGroupService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)

        self.data_patcher = patch.object(CustomGroupService, "DATA_DIR", self.data_dir)
        self.file_patcher = patch.object(
            CustomGroupService,
            "CUSTOM_GROUPS_FILE",
            self.data_dir / "custom_groups.json",
        )
        self.data_patcher.start()
        self.file_patcher.start()
        self.service = CustomGroupService()

    def tearDown(self):
        self.data_patcher.stop()
        self.file_patcher.stop()
        self.temp_dir.cleanup()

    def test_create_and_rename_and_delete_group(self):
        group = self.service.create_group("Favorites")
        self.assertEqual(group["name"], "Favorites")
        self.assertEqual(group["group_type"], "custom")

        renamed = self.service.rename_group(group["id"], "Favorites-2")
        self.assertIsNotNone(renamed)
        assert renamed is not None
        self.assertEqual(renamed["name"], "Favorites-2")

        deleted = self.service.delete_group(group["id"])
        self.assertTrue(deleted)
        self.assertIsNone(self.service.get_group(group["id"]))

    def test_group_name_is_trimmed_and_blank_name_is_rejected(self):
        group = self.service.create_group("  Favorites  ")
        self.assertEqual(group["name"], "Favorites")

        with self.assertRaises(ValueError):
            self.service.create_group("   ")

        with self.assertRaises(ValueError):
            self.service.rename_group(group["id"], "   ")

    def test_import_nodes_dedupes_within_group(self):
        group = self.service.create_group("Dedup")
        trojan_node = ProxyNode(
            name="TROJAN-1",
            protocol=Protocol.TROJAN,
            address="demo.example.com",
            port=443,
            password="secret",
            tls=True,
        )
        with patch("api.services.custom_group_service.parse_subscription", return_value=[trojan_node, trojan_node]):
            result = self.service.import_nodes(group["id"], "trojan://demo")

        self.assertEqual(result["imported_count"], 1)
        self.assertEqual(result["skipped_duplicates"], 1)
        self.assertEqual(result["total_parsed"], 2)
        self.assertEqual(result["ignored_unsupported_count"], 0)

        nodes = self.service.get_nodes_by_group(group["id"])
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["protocol"], "trojan")
        self.assertEqual(nodes[0]["group_id"], group["id"])

    def test_import_nodes_keeps_ssr_only_payload_for_display(self):
        group = self.service.create_group("SSR")
        ssr_node = ProxyNode(
            name="SSR-1",
            protocol=Protocol.SSR,
            address="ssr.example.com",
            port=443,
            password="secret",
            security="aes-256-cfb",
        )
        with patch("api.services.custom_group_service.parse_subscription", return_value=[ssr_node]):
            result = self.service.import_nodes(group["id"], "ssr://demo")

        self.assertEqual(result["imported_count"], 1)
        self.assertEqual(result["ignored_unsupported_count"], 0)
        nodes = self.service.get_nodes_by_group(group["id"])
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["protocol"], "ssr")

    def test_import_nodes_keeps_mixed_payload_without_ignoring_supported_schema(self):
        group = self.service.create_group("Mixed")
        trojan_node = ProxyNode(
            name="TROJAN-1",
            protocol=Protocol.TROJAN,
            address="demo.example.com",
            port=443,
            password="secret",
            tls=True,
        )
        ssr_node = ProxyNode(
            name="SSR-1",
            protocol=Protocol.SSR,
            address="ssr.example.com",
            port=443,
            password="secret",
            security="aes-256-cfb",
        )
        with patch("api.services.custom_group_service.parse_subscription", return_value=[trojan_node, ssr_node]):
            result = self.service.import_nodes(group["id"], "mixed://demo")

        self.assertEqual(result["imported_count"], 2)
        self.assertEqual(result["skipped_duplicates"], 0)
        self.assertEqual(result["total_parsed"], 2)
        self.assertEqual(result["ignored_unsupported_count"], 0)

    def test_groups_are_sorted_by_updated_at_desc(self):
        first = self.service.create_group("First")
        second = self.service.create_group("Second")
        renamed_first = self.service.rename_group(first["id"], "First Updated")
        assert renamed_first is not None

        groups = self.service.get_all_groups()
        self.assertEqual(groups[0]["id"], first["id"])
        self.assertEqual(groups[1]["id"], second["id"])

    def test_copy_nodes_copies_test_fields_and_dedupes(self):
        group = self.service.create_group("Copied")
        source = {
            "id": "node_sub_x_0001",
            "name": "HK-01",
            "protocol": "trojan",
            "address": "hk.example.com",
            "port": 443,
            "password": "secret",
            "network": "tcp",
            "tls": True,
            "test_status": "success",
            "latency_ms": 220,
            "exit_ip": "203.0.113.1",
            "exit_country": "Hong Kong",
        }
        first = self.service.copy_nodes(group["id"], [source], missing_node_ids=[])
        second = self.service.copy_nodes(group["id"], [source], missing_node_ids=["missing_1"])

        self.assertEqual(first["copied_count"], 1)
        self.assertEqual(second["copied_count"], 0)
        self.assertEqual(second["skipped_duplicates"], 1)
        self.assertEqual(second["missing_node_ids"], ["missing_1"])

        nodes = self.service.get_nodes_by_group(group["id"])
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["test_status"], "success")
        self.assertEqual(nodes[0]["latency_ms"], 220)
        self.assertEqual(nodes[0]["exit_ip"], "203.0.113.1")

    def test_delete_group_node_only_removes_target_node(self):
        group = self.service.create_group("Remove")
        first = self.service.copy_nodes(group["id"], [{
            "id": "source_1",
            "name": "Node 1",
            "protocol": "trojan",
            "address": "a.example.com",
            "port": 443,
        }])
        second = self.service.copy_nodes(group["id"], [{
            "id": "source_2",
            "name": "Node 2",
            "protocol": "trojan",
            "address": "b.example.com",
            "port": 443,
        }])
        self.assertEqual(first["copied_count"], 1)
        self.assertEqual(second["copied_count"], 1)

        nodes_before = self.service.get_nodes_by_group(group["id"])
        self.assertEqual(len(nodes_before), 2)
        remove_id = nodes_before[0]["id"]
        self.assertTrue(self.service.delete_group_node(group["id"], remove_id))
        self.assertFalse(self.service.delete_group_node(group["id"], remove_id))
        nodes_after = self.service.get_nodes_by_group(group["id"])
        self.assertEqual(len(nodes_after), 1)

        with open(self.service.CUSTOM_GROUPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["nodes"]), 1)


if __name__ == "__main__":
    unittest.main()
