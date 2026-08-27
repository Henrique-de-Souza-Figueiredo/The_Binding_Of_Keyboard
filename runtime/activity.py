from collections import deque
import time


class RuntimeActivityLog:
    def __init__(self, limit=250):
        self.limit = limit
        self._entries = deque(maxlen=limit)

    def add(self, entry):
        item = dict(entry)
        item.setdefault("hora", time.strftime("%H:%M:%S"))
        self._entries.appendleft(item)
        return item

    def clear(self):
        self._entries.clear()

    def list(self):
        return list(self._entries)

    def __len__(self):
        return len(self._entries)


def activity_from_action(acao_mapeada, applied=True, message=""):
    return {
        "kind": "ACTION",
        "applied": applied,
        "message": message,
        "slot": acao_mapeada.get("slot", ""),
        "configuracao": acao_mapeada.get("configuracao", ""),
        "tipo": acao_mapeada.get("tipo", ""),
        "dispositivo_id": acao_mapeada.get("dispositivo_id", ""),
        "entrada": acao_mapeada.get("entrada", ""),
        "estado": acao_mapeada.get("estado", ""),
        "acao": acao_mapeada.get("acao", ""),
    }


def activity_message(kind, message):
    return {
        "kind": kind,
        "applied": "",
        "message": message,
        "slot": "",
        "configuracao": "",
        "tipo": "",
        "dispositivo_id": "",
        "entrada": "",
        "estado": "",
        "acao": "",
    }
