import json
from pathlib import Path


DEFAULT_EXECUTION = {
    "controles": [],
    "stick_intensity": 100,
    "mouse_pulse_ms": 60,
    "mouse_deadzone": 0,
    "desativar_atalho": "",
}


def load_config(path):
    path = Path(path)

    if not path.exists():
        return {
            "configuracoes": {},
            "execucao": dict(DEFAULT_EXECUTION),
        }

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return {
        "configuracoes": data.get("configuracoes", {}),
        "execucao": normalize_execution_config(data.get("execucao", {})),
    }


def save_config(path, configuracoes, execucao):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "configuracoes": configuracoes,
        "execucao": normalize_execution_config(execucao),
    }

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def normalize_execution_config(execucao):
    data = dict(DEFAULT_EXECUTION)
    data.update(execucao or {})
    data["controles"] = list(data.get("controles") or [])
    data["stick_intensity"] = _clamp_int(data.get("stick_intensity"), 1, 100, 100)
    data["mouse_pulse_ms"] = _clamp_int(data.get("mouse_pulse_ms"), 10, 500, 60)
    data["mouse_deadzone"] = _clamp_int(data.get("mouse_deadzone"), 0, 100, 0)
    data["desativar_atalho"] = _normalize_shortcut(data.get("desativar_atalho"))
    return data


def _clamp_int(value, min_value, max_value, default):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default

    return max(min_value, min(max_value, number))


def _normalize_shortcut(value):
    return str(value or "").strip().upper()
