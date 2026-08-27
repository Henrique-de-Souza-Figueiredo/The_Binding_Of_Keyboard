import hashlib
import re


class DeviceManager:
    def __init__(self):
        self.devices_by_id = {}
        self.devices_by_handle = {}
        self.counts_by_type = {
            "TECLADO": 0,
            "MOUSE": 0,
        }
        self.active_counts_by_type = {
            "TECLADO": 0,
            "MOUSE": 0,
        }

    def adicionar(self, handle, tipo, nome, path):
        device_id = self._build_stable_id(path)
        handle_key = self._handle_key(handle)

        if device_id in self.devices_by_id:
            device = self.devices_by_id[device_id]
            if handle_key is not None:
                self.devices_by_handle[handle_key] = device_id
            return device

        self.counts_by_type[tipo] += 1

        device = {
            "id": device_id,
            "numero": self.counts_by_type[tipo],
            "tipo": tipo,
            "nome": nome,
            "path": path,
            "handle": handle_key,
            "numero_ativo": None,
        }

        self.devices_by_id[device_id] = device
        if handle_key is not None:
            self.devices_by_handle[handle_key] = device_id

        return device

    def adicionar_sem_handle(self, tipo):
        path = f"RAWINPUT_NULL_{tipo}"
        nome = "Dispositivo sem handle"

        if tipo == "TECLADO":
            nome = "Teclado sem handle"
        elif tipo == "MOUSE":
            nome = "Mouse integrado ou sem handle"

        return self.adicionar(None, tipo, nome, path)

    def obter(self, device_id):
        return self.devices_by_id.get(device_id)

    def obter_por_handle(self, handle):
        handle_key = self._handle_key(handle)

        if handle_key is None:
            return None

        device_id = self.devices_by_handle.get(handle_key)

        if device_id is None:
            return None

        return self.devices_by_id.get(device_id)

    def listar(self):
        return list(self.devices_by_id.values())

    def listar_teclados(self):
        return self._listar_por_tipo("TECLADO")

    def listar_mouses(self):
        return self._listar_por_tipo("MOUSE")

    def marcar_ativo(self, device):
        if device.get("numero_ativo") is not None:
            return device

        tipo = device["tipo"]
        self.active_counts_by_type[tipo] += 1
        device["numero_ativo"] = self.active_counts_by_type[tipo]

        return device

    def imprimir(self):
        print()
        print("=" * 60)
        print("            THE BINDING OF KEYBOARD")
        print("=" * 60)

        self._imprimir_grupo("TECLADOS", self.listar_teclados())
        self._imprimir_grupo("MOUSES", self.listar_mouses())

        print()
        print("=" * 60)

    def _listar_por_tipo(self, tipo):
        return [
            device
            for device in self.devices_by_id.values()
            if device["tipo"] == tipo
        ]

    def _imprimir_grupo(self, titulo, devices):
        print()
        print(titulo)

        if not devices:
            print()
            print("Nenhum dispositivo encontrado.")
            return

        for device in devices:
            print()
            print(f"[{device['numero']}] {device['nome']}")
            print(f"    ID:   {device['id']}")
            print(f"    Path: {device['path']}")

    @staticmethod
    def _build_stable_id(path):
        normalized_path = str(path or "").strip().lower()
        digest = hashlib.sha1(normalized_path.encode("utf-8")).hexdigest()
        return digest[:12].upper()

    @staticmethod
    def _handle_key(handle):
        if handle is None:
            return None

        if hasattr(handle, "value"):
            return handle.value

        return int(handle)


def nome_amigavel_por_path(path, tipo):
    if not path:
        return "Dispositivo desconhecido"

    vid = _extract_hex_field(path, "VID")
    pid = _extract_hex_field(path, "PID")

    if tipo == "TECLADO":
        base_name = "Teclado"
    elif tipo == "MOUSE":
        base_name = "Mouse"
    else:
        base_name = "Dispositivo"

    if vid and pid:
        return f"{base_name} VID_{vid} PID_{pid}"

    return base_name


def _extract_hex_field(path, field_name):
    match = re.search(rf"{field_name}_([0-9A-Fa-f]{{4}})", str(path))

    if not match:
        return None

    return match.group(1).upper()
