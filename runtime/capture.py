from runtime.mapper import (
    deslocamento_mouse,
    normalizar_entradas_evento,
    normalizar_rotulo_entrada,
)


CAPTURE_ANY = "qualquer"
CAPTURE_KEYBOARD = "teclado"
CAPTURE_MOUSE_BUTTON = "botao_mouse"
CAPTURE_MOUSE_MOVE = "movimento_mouse"


def captura_por_evento(evento, modo=CAPTURE_ANY):
    modo = normalizar_modo_captura(modo)
    tipo = normalizar_rotulo_entrada(evento.get("tipo", ""))
    estado = normalizar_rotulo_entrada(evento.get("acao", ""))

    if tipo == "TECLADO":
        if modo not in {CAPTURE_ANY, CAPTURE_KEYBOARD}:
            return None

        if estado != "DOWN":
            return None

        entrada = normalizar_rotulo_entrada(evento.get("entrada", ""))
        return _criar_captura(evento, entrada, estado) if entrada else None

    if tipo != "MOUSE" or modo == CAPTURE_KEYBOARD:
        return None

    entrada = _entrada_mouse_capturada(evento, estado, modo)

    if not entrada:
        return None

    return _criar_captura(evento, entrada, estado)


def chave_dispositivo_por_tipo(tipo):
    tipo = normalizar_rotulo_entrada(tipo)

    if tipo == "TECLADO":
        return "teclado"

    if tipo == "MOUSE":
        return "mouse"

    return ""


def normalizar_modo_captura(modo):
    modo = str(modo or CAPTURE_ANY).strip().lower()

    if modo in {CAPTURE_KEYBOARD, CAPTURE_MOUSE_BUTTON, CAPTURE_MOUSE_MOVE}:
        return modo

    return CAPTURE_ANY


def _entrada_mouse_capturada(evento, estado, modo=CAPTURE_ANY):
    entrada = normalizar_rotulo_entrada(evento.get("entrada", ""))

    if entrada == "MOVE" or estado == "MOVE":
        if modo not in {CAPTURE_ANY, CAPTURE_MOUSE_MOVE}:
            return ""

        return _entrada_movimento_dominante(evento)

    if modo == CAPTURE_MOUSE_MOVE:
        return ""

    if estado not in {"DOWN", "SCROLL"}:
        return ""

    entradas = normalizar_entradas_evento(evento)
    return entradas[0] if entradas else ""


def _entrada_movimento_dominante(evento):
    x, y = deslocamento_mouse(evento)

    if x == 0 and y == 0:
        return ""

    if abs(x) >= abs(y):
        return "MOUSE_LEFT_MOVE" if x < 0 else "MOUSE_RIGHT_MOVE"

    return "MOUSE_UP" if y < 0 else "MOUSE_DOWN"


def _criar_captura(evento, entrada, estado):
    return {
        "entrada": entrada,
        "tipo": normalizar_rotulo_entrada(evento.get("tipo", "")),
        "estado": estado,
        "dispositivo_id": evento.get("id", ""),
        "dispositivo": evento.get("dispositivo", ""),
        "numero": evento.get("numero", ""),
        "detalhe": evento.get("detalhe", ""),
    }
