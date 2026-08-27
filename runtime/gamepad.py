import time


ACTION_ALIASES = {
    "CROSS": "A",
    "CIRCLE": "B",
    "SQUARE": "X",
    "TRIANGLE": "Y",
    "L1": "LB",
    "R1": "RB",
    "L2": "LT",
    "R2": "RT",
    "L3": "LS",
    "R3": "RS",
    "OPTIONS": "START",
    "CREATE": "BACK",
    "PS": "GUIDE",
    "L": "LB",
    "R": "RB",
    "ZL": "LT",
    "ZR": "RT",
    "LEFT STICK": "LS",
    "RIGHT STICK": "RS",
    "PLUS": "START",
    "MINUS": "BACK",
    "HOME": "GUIDE",
    "CAPTURE": "BACK",
}

STICK_DIRECTIONS = {
    "LEFT STICK UP": ("left", "up"),
    "LEFT STICK DOWN": ("left", "down"),
    "LEFT STICK LEFT": ("left", "left"),
    "LEFT STICK RIGHT": ("left", "right"),
    "RIGHT STICK UP": ("right", "up"),
    "RIGHT STICK DOWN": ("right", "down"),
    "RIGHT STICK LEFT": ("right", "left"),
    "RIGHT STICK RIGHT": ("right", "right"),
}


class GamepadBackendError(RuntimeError):
    pass


class DebugGamepadBackend:
    def __init__(self):
        self.actions = []
        self.closed = False

    def aplicar_acao(self, acao_mapeada):
        if self.closed:
            return False

        self.actions.append(dict(acao_mapeada))
        return bool(acao_mapeada.get("acao"))

    def atualizar_temporarios(self):
        return False

    def reset(self):
        self.actions.append({"acao": "RESET"})

    def close(self):
        self.reset()
        self.closed = True


class XboxGamepadBackend:
    def __init__(
        self,
        vgamepad_module=None,
        gamepad=None,
        stick_value=1.0,
        pulse_seconds=0.06,
        time_func=None,
    ):
        self.vg = vgamepad_module or self._importar_vgamepad()
        self.gamepad = gamepad or self._criar_gamepad()
        self.stick_value = stick_value
        self.pulse_seconds = pulse_seconds
        self.time_func = time_func or time.monotonic
        self.button_map = self._criar_mapa_botoes()
        self.trigger_map = {
            "LT": self.gamepad.left_trigger,
            "RT": self.gamepad.right_trigger,
        }
        self.stick_directions = {
            "left": set(),
            "right": set(),
        }
        self.stick_pulses = {
            "left": {},
            "right": {},
        }

    def aplicar_acao(self, acao_mapeada):
        acao = normalizar_acao_controle(acao_mapeada.get("acao", ""))
        estado = str(acao_mapeada.get("estado", "")).upper()

        if not acao:
            return False

        if acao in self.button_map:
            return self._aplicar_botao(acao, estado)

        if acao in self.trigger_map:
            return self._aplicar_trigger(acao, estado)

        if acao in STICK_DIRECTIONS:
            return self._aplicar_direcao_stick(acao, estado)

        return False

    def atualizar_temporarios(self):
        agora = self.time_func()
        alterado = False

        for stick, pulses in self.stick_pulses.items():
            expirados = [
                direcao
                for direcao, expira_em in pulses.items()
                if expira_em <= agora
            ]

            for direcao in expirados:
                del pulses[direcao]
                alterado = True

            if expirados:
                self._atualizar_stick(stick)

        if alterado:
            self.gamepad.update()

        return alterado

    def reset(self):
        if hasattr(self.gamepad, "reset"):
            self.gamepad.reset()
        else:
            self._centralizar_sticks()
            for setter in self.trigger_map.values():
                setter(0)

        self.gamepad.update()

    def close(self):
        self.reset()

    def _aplicar_botao(self, acao, estado):
        button = self.button_map[acao]

        if estado == "DOWN":
            self.gamepad.press_button(button=button)
        elif estado == "UP":
            self.gamepad.release_button(button=button)
        else:
            return False

        self.gamepad.update()
        return True

    def _aplicar_trigger(self, acao, estado):
        setter = self.trigger_map[acao]

        if estado == "DOWN":
            setter(255)
        elif estado == "UP":
            setter(0)
        else:
            return False

        self.gamepad.update()
        return True

    def _aplicar_direcao_stick(self, acao, estado):
        stick, direcao = STICK_DIRECTIONS[acao]

        if estado == "DOWN":
            self.stick_directions[stick].add(direcao)
        elif estado == "UP":
            self.stick_directions[stick].discard(direcao)
        elif estado == "MOVE":
            self.stick_pulses[stick][direcao] = self.time_func() + self.pulse_seconds
        else:
            return False

        self._atualizar_stick(stick)
        self.gamepad.update()
        return True

    def _atualizar_stick(self, stick):
        direcoes = set(self.stick_directions[stick])
        direcoes.update(self.stick_pulses[stick])

        x = 0.0
        y = 0.0

        if "left" in direcoes and "right" not in direcoes:
            x = -self.stick_value
        elif "right" in direcoes and "left" not in direcoes:
            x = self.stick_value

        if "up" in direcoes and "down" not in direcoes:
            y = self.stick_value
        elif "down" in direcoes and "up" not in direcoes:
            y = -self.stick_value

        if stick == "left":
            self.gamepad.left_joystick_float(x_value_float=x, y_value_float=y)
        else:
            self.gamepad.right_joystick_float(x_value_float=x, y_value_float=y)

    def _centralizar_sticks(self):
        self.gamepad.left_joystick_float(x_value_float=0.0, y_value_float=0.0)
        self.gamepad.right_joystick_float(x_value_float=0.0, y_value_float=0.0)

    def _criar_mapa_botoes(self):
        buttons = self.vg.XUSB_BUTTON
        return {
            "A": buttons.XUSB_GAMEPAD_A,
            "B": buttons.XUSB_GAMEPAD_B,
            "X": buttons.XUSB_GAMEPAD_X,
            "Y": buttons.XUSB_GAMEPAD_Y,
            "LB": buttons.XUSB_GAMEPAD_LEFT_SHOULDER,
            "RB": buttons.XUSB_GAMEPAD_RIGHT_SHOULDER,
            "LS": buttons.XUSB_GAMEPAD_LEFT_THUMB,
            "RS": buttons.XUSB_GAMEPAD_RIGHT_THUMB,
            "D-PAD UP": buttons.XUSB_GAMEPAD_DPAD_UP,
            "D-PAD DOWN": buttons.XUSB_GAMEPAD_DPAD_DOWN,
            "D-PAD LEFT": buttons.XUSB_GAMEPAD_DPAD_LEFT,
            "D-PAD RIGHT": buttons.XUSB_GAMEPAD_DPAD_RIGHT,
            "START": buttons.XUSB_GAMEPAD_START,
            "BACK": buttons.XUSB_GAMEPAD_BACK,
            "GUIDE": buttons.XUSB_GAMEPAD_GUIDE,
        }

    def _importar_vgamepad(self):
        try:
            import vgamepad
        except Exception as erro:
            raise GamepadBackendError(
                "vgamepad nao esta disponivel no Python atual. Rode pelo run.bat, "
                "use .\\.venv\\Scripts\\python.exe main.py ou instale as dependencias "
                "com python -m pip install -r requirements.txt."
            ) from erro

        return vgamepad

    def _criar_gamepad(self):
        try:
            return self.vg.VX360Gamepad()
        except Exception as erro:
            raise GamepadBackendError(
                "Nao foi possivel criar o controle virtual Xbox. Verifique se o "
                "driver ViGEmBus esta instalado e se o Windows reconhece dispositivos "
                "virtuais Xbox."
            ) from erro


def normalizar_acao_controle(acao):
    normalizada = str(acao or "").strip().upper()
    return ACTION_ALIASES.get(normalizada, normalizada)
