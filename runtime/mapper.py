import re


MOUSE_BUTTON_ENTRIES = {
    "LEFT": "MOUSE_LEFT",
    "RIGHT": "MOUSE_RIGHT",
    "MIDDLE": "MOUSE_MIDDLE",
    "BUTTON 4": "MOUSE_BUTTON_4",
    "BUTTON_4": "MOUSE_BUTTON_4",
    "BUTTON 5": "MOUSE_BUTTON_5",
    "BUTTON_5": "MOUSE_BUTTON_5",
    "WHEEL": "MOUSE_WHEEL",
}

MOUSE_MOVE_ENTRIES = {
    "MOUSE_UP",
    "MOUSE_DOWN",
    "MOUSE_LEFT_MOVE",
    "MOUSE_RIGHT_MOVE",
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

STICK_LABELS = {
    "left": "Left Stick",
    "right": "Right Stick",
}


def mapear_evento_para_acoes(configuracao, evento, nome_configuracao=None, mouse_deadzone=0):
    """Return configured controller actions triggered by a Raw Input event."""
    if not dispositivo_permitido(configuracao, evento):
        return []

    entradas_evento = normalizar_entradas_evento(evento, mouse_deadzone=mouse_deadzone)
    if not entradas_evento:
        return []

    entradas_evento_set = set(entradas_evento)
    estado = estado_por_evento(evento)
    acoes = []
    analog_sticks = {}
    movimento_mouse = _evento_e_movimento_mouse(evento)
    x_mouse, y_mouse = deslocamento_mouse(evento) if movimento_mouse else (0, 0)

    for botao in configuracao.get("botoes", []):
        entradas_botao = normalizar_entradas_botao(botao)
        entradas_encontradas = entradas_evento_set.intersection(entradas_botao)
        stick_por_movimento_mouse = movimento_mouse and _botao_e_stick_por_movimento_mouse(
            botao,
            entradas_botao,
        )

        if stick_por_movimento_mouse:
            _registrar_eixo_stick_analogico(analog_sticks, botao, x_mouse, y_mouse)

        if not entradas_encontradas:
            continue

        if stick_por_movimento_mouse:
            _registrar_entrada_stick_analogico(
                analog_sticks,
                botao,
                entradas_evento,
                entradas_encontradas,
            )
            continue

        acoes.append(
            {
                "configuracao": nome_configuracao,
                "tipo": evento.get("tipo", ""),
                "dispositivo_id": evento.get("id", ""),
                "entrada": _primeira_entrada(entradas_evento, entradas_encontradas),
                "estado": estado,
                "nome": botao.get("nome", ""),
                "acao": botao.get("acao", ""),
            }
        )

    acoes.extend(_acoes_stick_analogico(nome_configuracao, evento, estado, analog_sticks))
    return acoes


def dispositivo_permitido(configuracao, evento):
    if evento.get("_ignorar_dispositivo"):
        return True

    dispositivos = configuracao.get("dispositivos") or {}
    tipo = str(evento.get("tipo", "")).upper()

    if tipo == "TECLADO":
        selecionado = dispositivos.get("teclado", "")
    elif tipo == "MOUSE":
        selecionado = dispositivos.get("mouse", "")
    else:
        return False

    return not selecionado or selecionado == evento.get("id", "")


def normalizar_entradas_evento(evento, mouse_deadzone=0):
    tipo = str(evento.get("tipo", "")).upper()
    entrada = normalizar_rotulo_entrada(evento.get("entrada", ""))

    if tipo == "TECLADO":
        return [entrada] if entrada else []

    if tipo != "MOUSE":
        return []

    if entrada == "MOVE" or normalizar_rotulo_entrada(evento.get("acao", "")) == "MOVE":
        return entradas_movimento_mouse(evento, deadzone=mouse_deadzone)

    return [MOUSE_BUTTON_ENTRIES.get(entrada, f"MOUSE_{entrada}") if entrada else ""]


def entradas_movimento_mouse(evento, deadzone=0):
    x, y = deslocamento_mouse(evento)
    entradas = []

    if abs(x) <= deadzone:
        x = 0

    if abs(y) <= deadzone:
        y = 0

    if y < 0:
        entradas.append("MOUSE_UP")
    elif y > 0:
        entradas.append("MOUSE_DOWN")

    if x < 0:
        entradas.append("MOUSE_LEFT_MOVE")
    elif x > 0:
        entradas.append("MOUSE_RIGHT_MOVE")

    return entradas


def _evento_e_movimento_mouse(evento):
    tipo = str(evento.get("tipo", "")).upper()
    entrada = normalizar_rotulo_entrada(evento.get("entrada", ""))
    acao = normalizar_rotulo_entrada(evento.get("acao", ""))
    return tipo == "MOUSE" and (entrada == "MOVE" or acao == "MOVE")


def _botao_e_stick_por_movimento_mouse(botao, entradas_botao):
    acao = normalizar_rotulo_entrada(botao.get("acao", ""))
    return acao in STICK_DIRECTIONS and bool(entradas_botao.intersection(MOUSE_MOVE_ENTRIES))


def _registrar_eixo_stick_analogico(analog_sticks, botao, x_mouse, y_mouse):
    acao = normalizar_rotulo_entrada(botao.get("acao", ""))
    stick, direcao = STICK_DIRECTIONS[acao]
    eixo = "x" if direcao in {"left", "right"} else "y"
    dados = analog_sticks.setdefault(
        stick,
        {
            "entries": [],
            "axes": set(),
            "nomes": [],
            "raw_x": x_mouse,
            "raw_y": y_mouse,
        },
    )

    dados["axes"].add(eixo)


def _registrar_entrada_stick_analogico(
    analog_sticks,
    botao,
    entradas_evento,
    entradas_encontradas,
):
    acao = normalizar_rotulo_entrada(botao.get("acao", ""))
    stick, _direcao = STICK_DIRECTIONS[acao]
    dados = analog_sticks[stick]
    dados["nomes"].append(botao.get("nome", ""))

    for entrada in entradas_evento:
        if entrada in entradas_encontradas and entrada not in dados["entries"]:
            dados["entries"].append(entrada)


def _acoes_stick_analogico(nome_configuracao, evento, estado, analog_sticks):
    acoes = []

    for stick, dados in analog_sticks.items():
        entradas = dados.get("entries") or []

        if not entradas:
            continue

        acoes.append(
            {
                "configuracao": nome_configuracao,
                "tipo": evento.get("tipo", ""),
                "dispositivo_id": evento.get("id", ""),
                "entrada": " + ".join(entradas) if entradas else "MOUSE_MOVE",
                "estado": estado,
                "nome": " + ".join(nome for nome in dados.get("nomes", []) if nome),
                "acao": STICK_LABELS.get(stick, stick),
                "stick_analog": {
                    "stick": stick,
                    "x": dados.get("raw_x", 0),
                    "y": dados.get("raw_y", 0),
                    "axes": sorted(dados.get("axes", set())),
                },
            }
        )

    return acoes


def _primeira_entrada(entradas_evento, entradas_encontradas):
    for entrada in entradas_evento:
        if entrada in entradas_encontradas:
            return entrada

    return next(iter(entradas_encontradas))


def deslocamento_mouse(evento):
    if "x" in evento or "y" in evento:
        return int(evento.get("x", 0)), int(evento.get("y", 0))

    detalhe = str(evento.get("detalhe", ""))
    x = _extrair_numero_detalhe(detalhe, "X")
    y = _extrair_numero_detalhe(detalhe, "Y")
    return x, y


def estado_por_evento(evento):
    acao = normalizar_rotulo_entrada(evento.get("acao", ""))

    if acao in {"DOWN", "UP", "MOVE", "SCROLL"}:
        return acao

    return ""


def normalizar_rotulo_entrada(valor):
    return str(valor or "").strip().upper()


def normalizar_entradas_botao(botao):
    entradas = []

    if botao.get("entradas"):
        entradas.extend(botao.get("entradas") or [])
    elif botao.get("entrada"):
        entradas.append(botao.get("entrada", ""))

    return {
        normalizada
        for normalizada in (normalizar_rotulo_entrada(entrada) for entrada in entradas)
        if normalizada
    }


def _extrair_numero_detalhe(detalhe, campo):
    match = re.search(rf"\b{campo}=\s*([+-]?\d+)", detalhe)

    if not match:
        return 0

    return int(match.group(1))
