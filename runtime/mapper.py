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


def mapear_evento_para_acoes(configuracao, evento, nome_configuracao=None, mouse_deadzone=0):
    """Return configured controller actions triggered by a Raw Input event."""
    if not dispositivo_permitido(configuracao, evento):
        return []

    entradas_evento = normalizar_entradas_evento(evento, mouse_deadzone=mouse_deadzone)
    if not entradas_evento:
        return []

    entradas_evento = set(entradas_evento)
    estado = estado_por_evento(evento)
    acoes = []

    for botao in configuracao.get("botoes", []):
        entradas_botao = normalizar_entradas_botao(botao)

        if not entradas_evento.intersection(entradas_botao):
            continue

        acoes.append(
            {
                "configuracao": nome_configuracao,
                "tipo": evento.get("tipo", ""),
                "dispositivo_id": evento.get("id", ""),
                "entrada": next(iter(entradas_evento.intersection(entradas_botao))),
                "estado": estado,
                "nome": botao.get("nome", ""),
                "acao": botao.get("acao", ""),
            }
        )

    return acoes


def dispositivo_permitido(configuracao, evento):
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
