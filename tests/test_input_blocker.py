import unittest

from runtime.input_blocker import criar_especificacao_bloqueio, entrada_por_vk, vks_por_entrada


class InputBlockerTest(unittest.TestCase):
    def test_keyboard_entries_are_converted_to_virtual_keys(self):
        self.assertEqual(vks_por_entrada("space"), {0x20})
        self.assertEqual(vks_por_entrada("VK_41"), {0x41})
        self.assertEqual(vks_por_entrada("SHIFT"), {0x10, 0xA0, 0xA1})

    def test_unknown_keyboard_entry_is_ignored(self):
        self.assertEqual(vks_por_entrada("MOUSE_LEFT"), set())
        self.assertEqual(vks_por_entrada("VK_BAD"), set())

    def test_virtual_key_is_converted_to_runtime_entry(self):
        self.assertEqual(entrada_por_vk(0x20), "SPACE")
        self.assertEqual(entrada_por_vk(0xA0), "SHIFT")
        self.assertEqual(entrada_por_vk(0xFF), "VK_FF")

    def test_block_spec_uses_active_profile_buttons(self):
        perfis = [
            {
                "slot": "Controle 1",
                "configuracao": {
                    "botoes": [
                        {"nome": "A", "entrada": "SPACE", "acao": "A"},
                        {"nome": "B", "entradas": ["CTRL", "MOUSE_LEFT"], "acao": "B"},
                        {"nome": "RS", "entrada": "MOUSE_RIGHT_MOVE", "acao": "RIGHT STICK RIGHT"},
                    ],
                },
            }
        ]

        spec = criar_especificacao_bloqueio(perfis)

        self.assertEqual(spec.keyboard_vks, frozenset({0x20, 0x11, 0xA2, 0xA3}))
        self.assertEqual(spec.mouse_buttons, frozenset({"MOUSE_LEFT"}))
        self.assertTrue(spec.block_mouse_move)


if __name__ == "__main__":
    unittest.main()
