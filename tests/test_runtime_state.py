import json
import logging
import os
import tempfile
import unittest

from src.runtime_state import RuntimeStateStore


class RuntimeStateStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.state_path = os.path.join(self.temp_dir.name, "runtime_state.json")
        self.logger = logging.getLogger("test.runtime_state")

    def test_missing_file_initializes_enabled_state(self):
        store = RuntimeStateStore(self.state_path, self.logger)

        state = store.get_state()

        self.assertTrue(state.enabled)
        self.assertIsNone(state.disabled_reason)
        self.assertTrue(os.path.exists(self.state_path))

    def test_disable_and_enable_persist_across_reloads(self):
        store = RuntimeStateStore(self.state_path, self.logger)
        store.disable("manual_disable")

        reloaded_store = RuntimeStateStore(self.state_path, self.logger)
        disabled_state = reloaded_store.get_state()
        self.assertFalse(disabled_state.enabled)
        self.assertEqual(disabled_state.disabled_reason, "manual_disable")

        reloaded_store.enable()
        enabled_state = RuntimeStateStore(self.state_path, self.logger).get_state()
        self.assertTrue(enabled_state.enabled)
        self.assertIsNone(enabled_state.disabled_reason)

    def test_invalid_json_fails_safe_as_disabled(self):
        with open(self.state_path, "w", encoding="utf-8") as handle:
            handle.write("{not-json")

        store = RuntimeStateStore(self.state_path, self.logger)
        state = store.get_state()

        self.assertFalse(state.enabled)
        self.assertEqual(state.disabled_reason, "state_load_error")

        with open(self.state_path, encoding="utf-8") as handle:
            payload = json.load(handle)

        self.assertFalse(payload["enabled"])
        self.assertEqual(payload["disabled_reason"], "state_load_error")


if __name__ == "__main__":
    unittest.main()
