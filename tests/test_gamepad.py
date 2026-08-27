import unittest
from types import SimpleNamespace

from runtime.gamepad import DebugGamepadBackend, XboxGamepadBackend, normalizar_acao_controle


class FakeButtons:
    XUSB_GAMEPAD_A = "A"
    XUSB_GAMEPAD_B = "B"
    XUSB_GAMEPAD_X = "X"
    XUSB_GAMEPAD_Y = "Y"
    XUSB_GAMEPAD_LEFT_SHOULDER = "LB"
    XUSB_GAMEPAD_RIGHT_SHOULDER = "RB"
    XUSB_GAMEPAD_LEFT_THUMB = "LS"
    XUSB_GAMEPAD_RIGHT_THUMB = "RS"
    XUSB_GAMEPAD_DPAD_UP = "DU"
    XUSB_GAMEPAD_DPAD_DOWN = "DD"
    XUSB_GAMEPAD_DPAD_LEFT = "DL"
    XUSB_GAMEPAD_DPAD_RIGHT = "DR"
    XUSB_GAMEPAD_START = "START"
    XUSB_GAMEPAD_BACK = "BACK"
    XUSB_GAMEPAD_GUIDE = "GUIDE"


class FakeGamepad:
    def __init__(self):
        self.calls = []

    def press_button(self, button):
        self.calls.append(("press", button))

    def release_button(self, button):
        self.calls.append(("release", button))

    def left_trigger(self, value):
        self.calls.append(("lt", value))

    def right_trigger(self, value):
        self.calls.append(("rt", value))

    def left_joystick_float(self, x_value_float, y_value_float):
        self.calls.append(("left_stick", x_value_float, y_value_float))

    def right_joystick_float(self, x_value_float, y_value_float):
        self.calls.append(("right_stick", x_value_float, y_value_float))

    def update(self):
        self.calls.append(("update",))

    def reset(self):
        self.calls.append(("reset",))


class GamepadTest(unittest.TestCase):
    def make_backend(self, time_value=1.0):
        clock = SimpleNamespace(value=time_value)
        backend = XboxGamepadBackend(
            vgamepad_module=SimpleNamespace(XUSB_BUTTON=FakeButtons),
            gamepad=FakeGamepad(),
            time_func=lambda: clock.value,
        )
        return backend, clock

    def test_button_down_and_up(self):
        backend, _clock = self.make_backend()

        self.assertTrue(backend.aplicar_acao({"acao": "A", "estado": "DOWN"}))
        self.assertTrue(backend.aplicar_acao({"acao": "A", "estado": "UP"}))

        self.assertIn(("press", "A"), backend.gamepad.calls)
        self.assertIn(("release", "A"), backend.gamepad.calls)

    def test_trigger_down_and_up(self):
        backend, _clock = self.make_backend()

        backend.aplicar_acao({"acao": "LT", "estado": "DOWN"})
        backend.aplicar_acao({"acao": "LT", "estado": "UP"})

        self.assertIn(("lt", 255), backend.gamepad.calls)
        self.assertIn(("lt", 0), backend.gamepad.calls)

    def test_left_stick_uses_key_state(self):
        backend, _clock = self.make_backend()

        backend.aplicar_acao({"acao": "Left Stick Up", "estado": "DOWN"})
        backend.aplicar_acao({"acao": "Left Stick Up", "estado": "UP"})

        self.assertIn(("left_stick", 0.0, 1.0), backend.gamepad.calls)
        self.assertIn(("left_stick", 0.0, 0.0), backend.gamepad.calls)

    def test_mouse_move_stick_direction_expires(self):
        backend, clock = self.make_backend()

        backend.aplicar_acao({"acao": "Right Stick Left", "estado": "MOVE"})
        clock.value += 1.0
        self.assertTrue(backend.atualizar_temporarios())

        self.assertIn(("right_stick", -1.0, 0.0), backend.gamepad.calls)
        self.assertIn(("right_stick", 0.0, 0.0), backend.gamepad.calls)

    def test_mouse_move_can_drive_stick_analogically(self):
        backend, clock = self.make_backend()

        backend.aplicar_acao(
            {
                "acao": "Right Stick",
                "estado": "MOVE",
                "stick_analog": {
                    "stick": "right",
                    "x": 12,
                    "y": -6,
                    "axes": ["x", "y"],
                },
            }
        )
        clock.value += 1.0
        self.assertTrue(backend.atualizar_temporarios())

        self.assertIn(("right_stick", 0.5, 0.25), backend.gamepad.calls)
        self.assertIn(("right_stick", 0.0, 0.0), backend.gamepad.calls)

    def test_playstation_and_nintendo_aliases(self):
        self.assertEqual(normalizar_acao_controle("Cross"), "A")
        self.assertEqual(normalizar_acao_controle("ZL"), "LT")
        self.assertEqual(normalizar_acao_controle("Plus"), "START")

    def test_debug_backend_records_actions(self):
        backend = DebugGamepadBackend()

        self.assertTrue(backend.aplicar_acao({"acao": "A", "estado": "DOWN"}))
        backend.close()

        self.assertEqual(backend.actions[0]["acao"], "A")
        self.assertTrue(backend.closed)


if __name__ == "__main__":
    unittest.main()
