import unittest

from runtime.capture import captura_por_evento, chave_dispositivo_por_tipo


class CaptureTest(unittest.TestCase):
    def test_keyboard_down_is_captured_with_device_data(self):
        captura = captura_por_evento(
            {
                "tipo": "TECLADO",
                "id": "keyboard-1",
                "dispositivo": "Teclado USB",
                "numero": 2,
                "entrada": "space",
                "acao": "DOWN",
            }
        )

        self.assertEqual(captura["entrada"], "SPACE")
        self.assertEqual(captura["tipo"], "TECLADO")
        self.assertEqual(captura["dispositivo_id"], "keyboard-1")
        self.assertEqual(captura["dispositivo"], "Teclado USB")

    def test_keyboard_up_is_ignored(self):
        self.assertIsNone(
            captura_por_evento(
                {
                    "tipo": "TECLADO",
                    "id": "keyboard-1",
                    "entrada": "SPACE",
                    "acao": "UP",
                }
            )
        )

    def test_mouse_button_down_is_captured(self):
        captura = captura_por_evento(
            {
                "tipo": "MOUSE",
                "id": "mouse-1",
                "entrada": "LEFT",
                "acao": "DOWN",
            }
        )

        self.assertEqual(captura["entrada"], "MOUSE_LEFT")
        self.assertEqual(captura["tipo"], "MOUSE")

    def test_mouse_button_mode_ignores_keyboard(self):
        self.assertIsNone(
            captura_por_evento(
                {
                    "tipo": "TECLADO",
                    "id": "keyboard-1",
                    "entrada": "SPACE",
                    "acao": "DOWN",
                },
                modo="botao_mouse",
            )
        )

    def test_mouse_button_mode_ignores_mouse_move(self):
        self.assertIsNone(
            captura_por_evento(
                {
                    "tipo": "MOUSE",
                    "id": "mouse-1",
                    "entrada": "MOVE",
                    "acao": "MOVE",
                    "detalhe": "X=  +9 Y=  +1",
                },
                modo="botao_mouse",
            )
        )

    def test_mouse_button_up_is_ignored(self):
        self.assertIsNone(
            captura_por_evento(
                {
                    "tipo": "MOUSE",
                    "id": "mouse-1",
                    "entrada": "LEFT",
                    "acao": "UP",
                }
            )
        )

    def test_mouse_move_uses_dominant_axis(self):
        captura = captura_por_evento(
            {
                "tipo": "MOUSE",
                "id": "mouse-1",
                "entrada": "MOVE",
                "acao": "MOVE",
                "detalhe": "X=  +2 Y=  -9",
            }
        )

        self.assertEqual(captura["entrada"], "MOUSE_UP")

    def test_mouse_move_mode_ignores_mouse_button(self):
        self.assertIsNone(
            captura_por_evento(
                {
                    "tipo": "MOUSE",
                    "id": "mouse-1",
                    "entrada": "LEFT",
                    "acao": "DOWN",
                },
                modo="movimento_mouse",
            )
        )

    def test_device_key_by_type(self):
        self.assertEqual(chave_dispositivo_por_tipo("TECLADO"), "teclado")
        self.assertEqual(chave_dispositivo_por_tipo("MOUSE"), "mouse")
        self.assertEqual(chave_dispositivo_por_tipo("GAMEPAD"), "")


if __name__ == "__main__":
    unittest.main()
