import unittest

from runtime.mapper import (
    dispositivo_permitido,
    mapear_evento_para_acoes,
    normalizar_entradas_evento,
)


class MapperTest(unittest.TestCase):
    def test_keyboard_event_maps_when_device_is_any(self):
        configuracao = {
            "dispositivos": {"teclado": "", "mouse": ""},
            "botoes": [{"nome": "A", "entrada": "space", "acao": "A"}],
        }
        evento = {
            "tipo": "TECLADO",
            "id": "keyboard-1",
            "entrada": "SPACE",
            "acao": "DOWN",
        }

        acoes = mapear_evento_para_acoes(configuracao, evento, "Padrao")

        self.assertEqual(len(acoes), 1)
        self.assertEqual(acoes[0]["configuracao"], "Padrao")
        self.assertEqual(acoes[0]["acao"], "A")
        self.assertEqual(acoes[0]["estado"], "DOWN")

    def test_keyboard_event_is_ignored_when_device_does_not_match(self):
        configuracao = {
            "dispositivos": {"teclado": "keyboard-2", "mouse": ""},
            "botoes": [{"nome": "A", "entrada": "SPACE", "acao": "A"}],
        }
        evento = {
            "tipo": "TECLADO",
            "id": "keyboard-1",
            "entrada": "SPACE",
            "acao": "DOWN",
        }

        self.assertFalse(dispositivo_permitido(configuracao, evento))
        self.assertEqual(mapear_evento_para_acoes(configuracao, evento), [])

    def test_background_hook_keyboard_event_ignores_device_filter(self):
        configuracao = {
            "dispositivos": {"teclado": "keyboard-2", "mouse": ""},
            "botoes": [{"nome": "A", "entrada": "SPACE", "acao": "A"}],
        }
        evento = {
            "tipo": "TECLADO",
            "id": "",
            "entrada": "SPACE",
            "acao": "DOWN",
            "_ignorar_dispositivo": True,
        }

        acoes = mapear_evento_para_acoes(configuracao, evento)

        self.assertEqual(len(acoes), 1)
        self.assertEqual(acoes[0]["acao"], "A")

    def test_mouse_button_is_normalized_to_saved_config_label(self):
        configuracao = {
            "dispositivos": {"teclado": "", "mouse": ""},
            "botoes": [{"nome": "LT", "entrada": "MOUSE_LEFT", "acao": "LT"}],
        }
        evento = {
            "tipo": "MOUSE",
            "id": "mouse-1",
            "entrada": "LEFT",
            "acao": "DOWN",
        }

        acoes = mapear_evento_para_acoes(configuracao, evento)

        self.assertEqual(len(acoes), 1)
        self.assertEqual(acoes[0]["entrada"], "MOUSE_LEFT")
        self.assertEqual(acoes[0]["acao"], "LT")

    def test_mouse_move_can_emit_two_directional_entries(self):
        evento = {
            "tipo": "MOUSE",
            "id": "mouse-1",
            "entrada": "MOVE",
            "acao": "MOVE",
            "detalhe": "X=   -4 Y=   +6",
        }

        self.assertEqual(
            normalizar_entradas_evento(evento),
            ["MOUSE_DOWN", "MOUSE_LEFT_MOVE"],
        )

    def test_mouse_move_respects_deadzone(self):
        evento = {
            "tipo": "MOUSE",
            "id": "mouse-1",
            "entrada": "MOVE",
            "acao": "MOVE",
            "detalhe": "X=   +3 Y=   -2",
        }

        self.assertEqual(normalizar_entradas_evento(evento, mouse_deadzone=5), [])

    def test_mouse_move_stick_mapping_keeps_analog_delta(self):
        configuracao = {
            "dispositivos": {"teclado": "", "mouse": ""},
            "botoes": [
                {"nome": "RS Up", "entrada": "MOUSE_UP", "acao": "Right Stick Up"},
                {"nome": "RS Down", "entrada": "MOUSE_DOWN", "acao": "Right Stick Down"},
                {
                    "nome": "RS Left",
                    "entrada": "MOUSE_LEFT_MOVE",
                    "acao": "Right Stick Left",
                },
                {
                    "nome": "RS Right",
                    "entrada": "MOUSE_RIGHT_MOVE",
                    "acao": "Right Stick Right",
                },
            ],
        }
        evento = {
            "tipo": "MOUSE",
            "id": "mouse-1",
            "entrada": "MOVE",
            "acao": "MOVE",
            "x": 12,
            "y": -6,
        }

        acoes = mapear_evento_para_acoes(configuracao, evento)

        self.assertEqual(len(acoes), 1)
        self.assertEqual(acoes[0]["entrada"], "MOUSE_UP + MOUSE_RIGHT_MOVE")
        self.assertEqual(acoes[0]["acao"], "Right Stick")
        self.assertEqual(
            acoes[0]["stick_analog"],
            {"stick": "right", "x": 12, "y": -6, "axes": ["x", "y"]},
        )

    def test_button_can_have_multiple_inputs(self):
        configuracao = {
            "dispositivos": {"teclado": "", "mouse": ""},
            "botoes": [
                {
                    "nome": "A",
                    "entrada": "SPACE",
                    "entradas": ["SPACE", "ENTER"],
                    "acao": "A",
                }
            ],
        }
        evento = {
            "tipo": "TECLADO",
            "id": "keyboard-1",
            "entrada": "ENTER",
            "acao": "DOWN",
        }

        acoes = mapear_evento_para_acoes(configuracao, evento)

        self.assertEqual(len(acoes), 1)
        self.assertEqual(acoes[0]["entrada"], "ENTER")

    def test_unknown_event_type_is_ignored(self):
        configuracao = {
            "dispositivos": {"teclado": "", "mouse": ""},
            "botoes": [{"nome": "A", "entrada": "SPACE", "acao": "A"}],
        }

        self.assertEqual(
            mapear_evento_para_acoes(configuracao, {"tipo": "GAMEPAD"}),
            [],
        )


if __name__ == "__main__":
    unittest.main()
