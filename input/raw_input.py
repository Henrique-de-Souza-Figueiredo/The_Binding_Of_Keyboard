import ctypes
from ctypes import wintypes

from devices.device_manager import nome_amigavel_por_path


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

LRESULT = ctypes.c_ssize_t

WM_INPUT = 0x00FF
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002

RIM_TYPEMOUSE = 0
RIM_TYPEKEYBOARD = 1

RID_INPUT = 0x10000003
RIDI_DEVICENAME = 0x20000007

RIDEV_INPUTSINK = 0x00000100

RI_KEY_BREAK = 0x0001

RI_MOUSE_LEFT_BUTTON_DOWN = 0x0001
RI_MOUSE_LEFT_BUTTON_UP = 0x0002
RI_MOUSE_RIGHT_BUTTON_DOWN = 0x0004
RI_MOUSE_RIGHT_BUTTON_UP = 0x0008
RI_MOUSE_MIDDLE_BUTTON_DOWN = 0x0010
RI_MOUSE_MIDDLE_BUTTON_UP = 0x0020
RI_MOUSE_BUTTON_4_DOWN = 0x0040
RI_MOUSE_BUTTON_4_UP = 0x0080
RI_MOUSE_BUTTON_5_DOWN = 0x0100
RI_MOUSE_BUTTON_5_UP = 0x0200
RI_MOUSE_WHEEL = 0x0400


class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [
        ("hDevice", wintypes.HANDLE),
        ("dwType", wintypes.DWORD),
    ]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class RAWMOUSE_BUTTONS(ctypes.Union):
    _fields_ = [
        ("ulButtons", wintypes.ULONG),
        ("usButtonFlags", wintypes.USHORT),
    ]


class RAWMOUSE(ctypes.Structure):
    _fields_ = [
        ("usFlags", wintypes.USHORT),
        ("buttons", RAWMOUSE_BUTTONS),
        ("ulRawButtons", wintypes.ULONG),
        ("lLastX", wintypes.LONG),
        ("lLastY", wintypes.LONG),
        ("ulExtraInformation", wintypes.ULONG),
    ]


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [
        ("MakeCode", wintypes.USHORT),
        ("Flags", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("VKey", wintypes.USHORT),
        ("Message", wintypes.UINT),
        ("ExtraInformation", wintypes.ULONG),
    ]


WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
    ]


def _configurar_winapi():
    user32.GetRawInputDeviceList.argtypes = [
        ctypes.POINTER(RAWINPUTDEVICELIST),
        ctypes.POINTER(wintypes.UINT),
        wintypes.UINT,
    ]
    user32.GetRawInputDeviceList.restype = wintypes.UINT

    user32.GetRawInputDeviceInfoW.argtypes = [
        wintypes.HANDLE,
        wintypes.UINT,
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.UINT),
    ]
    user32.GetRawInputDeviceInfoW.restype = wintypes.UINT

    user32.GetRawInputData.argtypes = [
        wintypes.HANDLE,
        wintypes.UINT,
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.UINT),
        wintypes.UINT,
    ]
    user32.GetRawInputData.restype = wintypes.UINT

    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
    user32.RegisterClassW.restype = wintypes.ATOM

    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        wintypes.HMENU,
        wintypes.HINSTANCE,
        ctypes.c_void_p,
    ]
    user32.CreateWindowExW.restype = wintypes.HWND

    user32.RegisterRawInputDevices.argtypes = [
        ctypes.POINTER(RAWINPUTDEVICE),
        wintypes.UINT,
        wintypes.UINT,
    ]
    user32.RegisterRawInputDevices.restype = wintypes.BOOL

    user32.GetMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG),
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
    ]
    user32.GetMessageW.restype = wintypes.BOOL

    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.TranslateMessage.restype = wintypes.BOOL

    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.restype = LRESULT

    user32.DefWindowProcW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.DefWindowProcW.restype = LRESULT

    user32.PostQuitMessage.argtypes = [ctypes.c_int]
    user32.PostQuitMessage.restype = None

    user32.PostMessageW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.PostMessageW.restype = wintypes.BOOL

    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE


_configurar_winapi()


TECLAS = {
    0x08: "BACKSPACE",
    0x09: "TAB",
    0x0D: "ENTER",
    0x10: "SHIFT",
    0x11: "CTRL",
    0x12: "ALT",
    0x13: "PAUSE",
    0x14: "CAPSLOCK",
    0x1B: "ESC",
    0x20: "SPACE",
    0x21: "PAGEUP",
    0x22: "PAGEDOWN",
    0x23: "END",
    0x24: "HOME",
    0x25: "LEFT",
    0x26: "UP",
    0x27: "RIGHT",
    0x28: "DOWN",
    0x2D: "INSERT",
    0x2E: "DELETE",
    0x30: "0",
    0x31: "1",
    0x32: "2",
    0x33: "3",
    0x34: "4",
    0x35: "5",
    0x36: "6",
    0x37: "7",
    0x38: "8",
    0x39: "9",
    0x41: "A",
    0x42: "B",
    0x43: "C",
    0x44: "D",
    0x45: "E",
    0x46: "F",
    0x47: "G",
    0x48: "H",
    0x49: "I",
    0x4A: "J",
    0x4B: "K",
    0x4C: "L",
    0x4D: "M",
    0x4E: "N",
    0x4F: "O",
    0x50: "P",
    0x51: "Q",
    0x52: "R",
    0x53: "S",
    0x54: "T",
    0x55: "U",
    0x56: "V",
    0x57: "W",
    0x58: "X",
    0x59: "Y",
    0x5A: "Z",
    0x60: "NUM0",
    0x61: "NUM1",
    0x62: "NUM2",
    0x63: "NUM3",
    0x64: "NUM4",
    0x65: "NUM5",
    0x66: "NUM6",
    0x67: "NUM7",
    0x68: "NUM8",
    0x69: "NUM9",
    0x6A: "NUM*",
    0x6B: "NUM+",
    0x6D: "NUM-",
    0x6E: "NUM.",
    0x6F: "NUM/",
    0x70: "F1",
    0x71: "F2",
    0x72: "F3",
    0x73: "F4",
    0x74: "F5",
    0x75: "F6",
    0x76: "F7",
    0x77: "F8",
    0x78: "F9",
    0x79: "F10",
    0x7A: "F11",
    0x7B: "F12",
    0xBA: ";",
    0xBB: "=",
    0xBC: ",",
    0xBD: "-",
    0xBE: ".",
    0xBF: "/",
    0xC0: "`",
    0xDB: "[",
    0xDC: "\\",
    0xDD: "]",
    0xDE: "'",
}


class RawInputMonitor:
    def __init__(self, device_manager, event_callback=None, log_to_console=True):
        self.device_manager = device_manager
        self.event_callback = event_callback
        self.log_to_console = log_to_console
        self.hwnd = None
        self._parando = False
        self._wndproc = WNDPROC(self._janela_proc)

    def listar_dispositivos(self):
        quantidade = wintypes.UINT(0)
        tamanho = ctypes.sizeof(RAWINPUTDEVICELIST)

        resultado = user32.GetRawInputDeviceList(None, ctypes.byref(quantidade), tamanho)

        if _resultado_erro(resultado):
            raise ctypes.WinError(ctypes.GetLastError())

        if quantidade.value == 0:
            return []

        raw_devices = (RAWINPUTDEVICELIST * quantidade.value)()

        resultado = user32.GetRawInputDeviceList(
            raw_devices,
            ctypes.byref(quantidade),
            tamanho,
        )

        if _resultado_erro(resultado):
            raise ctypes.WinError(ctypes.GetLastError())

        for raw_device in raw_devices:
            tipo = self._tipo_por_raw_type(raw_device.dwType)

            if tipo is None:
                continue

            path = obter_path_dispositivo(raw_device.hDevice)
            nome = nome_amigavel_por_path(path, tipo)
            self.device_manager.adicionar(raw_device.hDevice, tipo, nome, path)

        return self.device_manager.listar()

    def iniciar(self):
        if self._parando:
            return

        self._criar_janela()

        if self._parando:
            self.parar()
            return

        self._registrar_raw_input()

        if self._parando:
            self.parar()
            return

        self._log("Raw Input registrado com sucesso.")
        self._log("Pressione teclas ou movimente os mouses.")
        self._log("CTRL+C para sair.")
        self._log()
        self._log("-" * 60)

        self._loop_mensagens()

    def parar(self):
        self._parando = True

        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)

    def _criar_janela(self):
        hinstance = kernel32.GetModuleHandleW(None)
        nome_classe = f"TheBindingOfKeyboardRawInputWindow{id(self)}"

        wc = WNDCLASS()
        wc.style = 0
        wc.lpfnWndProc = self._wndproc
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hinstance
        wc.hIcon = None
        wc.hCursor = None
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = nome_classe

        resultado = user32.RegisterClassW(ctypes.byref(wc))

        if not resultado:
            erro = ctypes.GetLastError()
            raise ctypes.WinError(erro)

        self.hwnd = user32.CreateWindowExW(
            0,
            nome_classe,
            "The Binding Of Keyboard Raw Input",
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            hinstance,
            None,
        )

        if not self.hwnd:
            erro = ctypes.GetLastError()
            raise ctypes.WinError(erro)

    def _registrar_raw_input(self):
        dispositivos_raw = (RAWINPUTDEVICE * 2)()

        dispositivos_raw[0].usUsagePage = 0x01
        dispositivos_raw[0].usUsage = 0x06
        dispositivos_raw[0].dwFlags = RIDEV_INPUTSINK
        dispositivos_raw[0].hwndTarget = self.hwnd

        dispositivos_raw[1].usUsagePage = 0x01
        dispositivos_raw[1].usUsage = 0x02
        dispositivos_raw[1].dwFlags = RIDEV_INPUTSINK
        dispositivos_raw[1].hwndTarget = self.hwnd

        resultado = user32.RegisterRawInputDevices(
            dispositivos_raw,
            2,
            ctypes.sizeof(RAWINPUTDEVICE),
        )

        if not resultado:
            erro = ctypes.GetLastError()
            raise ctypes.WinError(erro)

    def _loop_mensagens(self):
        msg = wintypes.MSG()

        try:
            while True:
                resultado = user32.GetMessageW(ctypes.byref(msg), self.hwnd, 0, 0)

                if resultado <= 0:
                    break

                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        except KeyboardInterrupt:
            self._log()
            self._log("-" * 60)
            self._log("Programa encerrado.")
            self._log("-" * 60)

    def _janela_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_INPUT:
            try:
                self._processar_raw_input(lparam)
            except Exception as erro:
                print(f"[ERRO RAW INPUT] {erro}")

            return 0

        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0

        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _processar_raw_input(self, hrawinput):
        tamanho = wintypes.UINT(0)

        resultado = user32.GetRawInputData(
            hrawinput,
            RID_INPUT,
            None,
            ctypes.byref(tamanho),
            ctypes.sizeof(RAWINPUTHEADER),
        )

        if _resultado_erro(resultado):
            return

        buffer = ctypes.create_string_buffer(tamanho.value)

        resultado = user32.GetRawInputData(
            hrawinput,
            RID_INPUT,
            buffer,
            ctypes.byref(tamanho),
            ctypes.sizeof(RAWINPUTHEADER),
        )

        if _resultado_erro(resultado):
            return

        header = RAWINPUTHEADER.from_buffer_copy(buffer)
        dispositivo = self._obter_ou_adicionar_dispositivo(header)

        if dispositivo is None:
            return

        offset = ctypes.sizeof(RAWINPUTHEADER)

        if header.dwType == RIM_TYPEKEYBOARD:
            teclado = RAWKEYBOARD.from_buffer_copy(buffer, offset)
            self._processar_teclado(teclado, dispositivo)

        elif header.dwType == RIM_TYPEMOUSE:
            mouse = RAWMOUSE.from_buffer_copy(buffer, offset)
            self._processar_mouse(mouse, dispositivo)

    def _obter_ou_adicionar_dispositivo(self, header):
        tipo = self._tipo_por_raw_type(header.dwType)

        if tipo is None:
            return None

        if header.hDevice is None:
            dispositivo = self.device_manager.adicionar_sem_handle(tipo)
        else:
            dispositivo = self.device_manager.obter_por_handle(header.hDevice)

            if dispositivo is None:
                path = obter_path_dispositivo(header.hDevice)
                nome = nome_amigavel_por_path(path, tipo)
                dispositivo = self.device_manager.adicionar(header.hDevice, tipo, nome, path)

        ja_estava_ativo = dispositivo.get("numero_ativo") is not None
        self.device_manager.marcar_ativo(dispositivo)

        if not ja_estava_ativo:
            self._log()
            self._log("=" * 60)
            self._log(f"{tipo} ATIVO {dispositivo['numero_ativo']}")
            self._log(f"ID: {dispositivo['id']}")
            self._log(f"Dispositivo: {dispositivo['path']}")
            self._log("=" * 60)

        return dispositivo

    def _processar_teclado(self, teclado, dispositivo):
        tecla = TECLAS.get(teclado.VKey, f"VK_{teclado.VKey:02X}")
        estado = "UP" if teclado.Flags & RI_KEY_BREAK else "DOWN"

        self._emitir_evento(
            {
                "tipo": "TECLADO",
                "numero": dispositivo["numero_ativo"],
                "dispositivo": dispositivo["nome"],
                "id": dispositivo["id"],
                "entrada": tecla,
                "acao": estado,
                "detalhe": f"VK={teclado.VKey:02X}",
            }
        )
        self._log(f"[TECLADO {dispositivo['numero_ativo']}] {tecla:<10} {estado}")

    def _processar_mouse(self, mouse, dispositivo):
        numero = dispositivo["numero_ativo"]

        if mouse.lLastX != 0 or mouse.lLastY != 0:
            self._emitir_evento(
                {
                    "tipo": "MOUSE",
                    "numero": numero,
                    "dispositivo": dispositivo["nome"],
                    "id": dispositivo["id"],
                    "entrada": "MOVE",
                    "acao": "MOVE",
                    "detalhe": f"X={mouse.lLastX:+5} Y={mouse.lLastY:+5}",
                }
            )
            self._log(f"[MOUSE {numero}] MOVE X={mouse.lLastX:+5} Y={mouse.lLastY:+5}")

        flags = mouse.buttons.usButtonFlags

        if flags & RI_MOUSE_LEFT_BUTTON_DOWN:
            self._emitir_mouse_botao(dispositivo, "LEFT", "DOWN")
        if flags & RI_MOUSE_LEFT_BUTTON_UP:
            self._emitir_mouse_botao(dispositivo, "LEFT", "UP")
        if flags & RI_MOUSE_RIGHT_BUTTON_DOWN:
            self._emitir_mouse_botao(dispositivo, "RIGHT", "DOWN")
        if flags & RI_MOUSE_RIGHT_BUTTON_UP:
            self._emitir_mouse_botao(dispositivo, "RIGHT", "UP")
        if flags & RI_MOUSE_MIDDLE_BUTTON_DOWN:
            self._emitir_mouse_botao(dispositivo, "MIDDLE", "DOWN")
        if flags & RI_MOUSE_MIDDLE_BUTTON_UP:
            self._emitir_mouse_botao(dispositivo, "MIDDLE", "UP")
        if flags & RI_MOUSE_BUTTON_4_DOWN:
            self._emitir_mouse_botao(dispositivo, "BUTTON 4", "DOWN")
        if flags & RI_MOUSE_BUTTON_4_UP:
            self._emitir_mouse_botao(dispositivo, "BUTTON 4", "UP")
        if flags & RI_MOUSE_BUTTON_5_DOWN:
            self._emitir_mouse_botao(dispositivo, "BUTTON 5", "DOWN")
        if flags & RI_MOUSE_BUTTON_5_UP:
            self._emitir_mouse_botao(dispositivo, "BUTTON 5", "UP")
        if flags & RI_MOUSE_WHEEL:
            self._emitir_mouse_botao(dispositivo, "WHEEL", "SCROLL")

    def _emitir_mouse_botao(self, dispositivo, entrada, acao):
        numero = dispositivo["numero_ativo"]
        self._emitir_evento(
            {
                "tipo": "MOUSE",
                "numero": numero,
                "dispositivo": dispositivo["nome"],
                "id": dispositivo["id"],
                "entrada": entrada,
                "acao": acao,
                "detalhe": "",
            }
        )
        self._log(f"[MOUSE {numero}] {entrada} {acao}")

    def _emitir_evento(self, evento):
        if self.event_callback is None:
            return

        try:
            self.event_callback(evento)
        except Exception as erro:
            self._log(f"[ERRO CALLBACK] {erro}")

    def _log(self, texto=""):
        if self.log_to_console:
            print(texto)

    @staticmethod
    def _tipo_por_raw_type(raw_type):
        if raw_type == RIM_TYPEKEYBOARD:
            return "TECLADO"

        if raw_type == RIM_TYPEMOUSE:
            return "MOUSE"

        return None


def obter_path_dispositivo(handle):
    tamanho = wintypes.UINT(0)

    resultado = user32.GetRawInputDeviceInfoW(
        handle,
        RIDI_DEVICENAME,
        None,
        ctypes.byref(tamanho),
    )

    if _resultado_erro(resultado) or tamanho.value == 0:
        return "Dispositivo desconhecido"

    buffer = ctypes.create_unicode_buffer(tamanho.value + 1)

    resultado = user32.GetRawInputDeviceInfoW(
        handle,
        RIDI_DEVICENAME,
        buffer,
        ctypes.byref(tamanho),
    )

    if _resultado_erro(resultado):
        return "Dispositivo desconhecido"

    return buffer.value


def _resultado_erro(resultado):
    return resultado == -1 or resultado == ctypes.c_uint(-1).value
