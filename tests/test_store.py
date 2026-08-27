import tempfile
import unittest
from pathlib import Path

from config.store import load_config, normalize_execution_config, save_config


class ConfigStoreTest(unittest.TestCase):
    def test_normalizes_execution_bounds(self):
        execucao = normalize_execution_config(
            {
                "controles": ["A"],
                "stick_intensity": 500,
                "mouse_pulse_ms": 1,
                "mouse_deadzone": -10,
            }
        )

        self.assertEqual(execucao["controles"], ["A"])
        self.assertEqual(execucao["stick_intensity"], 100)
        self.assertEqual(execucao["mouse_pulse_ms"], 10)
        self.assertEqual(execucao["mouse_deadzone"], 0)

    def test_load_and_save_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "button_configs.json"

            save_config(
                path,
                {"Padrao": {"padrao": "Xbox"}},
                {"controles": ["Padrao"]},
            )
            data = load_config(path)

        self.assertIn("Padrao", data["configuracoes"])
        self.assertEqual(data["execucao"]["controles"], ["Padrao"])


if __name__ == "__main__":
    unittest.main()
