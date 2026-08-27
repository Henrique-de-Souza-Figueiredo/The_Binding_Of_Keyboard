import unittest

from runtime.activity import RuntimeActivityLog, activity_from_action, activity_message


class RuntimeActivityLogTest(unittest.TestCase):
    def test_log_keeps_newest_first(self):
        log = RuntimeActivityLog(limit=3)

        log.add({"entrada": "A"})
        log.add({"entrada": "B"})

        self.assertEqual(
            [entry["entrada"] for entry in log.list()],
            ["B", "A"],
        )

    def test_log_respects_limit(self):
        log = RuntimeActivityLog(limit=2)

        log.add({"entrada": "A"})
        log.add({"entrada": "B"})
        log.add({"entrada": "C"})

        self.assertEqual(
            [entry["entrada"] for entry in log.list()],
            ["C", "B"],
        )

    def test_activity_from_action_copies_fields(self):
        activity = activity_from_action(
            {
                "configuracao": "Padrao",
                "tipo": "TECLADO",
                "dispositivo_id": "keyboard-1",
                "slot": "Controle 1",
                "entrada": "SPACE",
                "estado": "DOWN",
                "acao": "A",
            }
        )

        self.assertTrue(activity["applied"])
        self.assertEqual(activity["kind"], "ACTION")
        self.assertEqual(activity["acao"], "A")
        self.assertEqual(activity["slot"], "Controle 1")

    def test_message_activity(self):
        activity = activity_message("ERROR", "falha")

        self.assertEqual(activity["kind"], "ERROR")
        self.assertEqual(activity["message"], "falha")


if __name__ == "__main__":
    unittest.main()
