import ctypes
import os
import threading
from ctypes import wintypes
from dataclasses import dataclass

from runtime.mapper import normalizar_entradas_botao, normalizar_rotulo_entrada


WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14

WM_QUIT = 0x0012
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C

HC_ACTION = 0
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002

KEYBOARD_MESSAGES = {
    WM_KEYDOWN,
    WM_KEYUP,
    WM_SYSKEYDOWN,
    WM_SYSKEYUP,
}

MOUSE_BUTTON_MESSAGES = {
    WM_LBUTTONDOWN: "MOUSE_LEFT",
    WM_LBUTTONUP: "MOUSE_LEFT",
    WM_RBUTTONDOWN: "MOUSE_RIGHT",
    WM_RBUTTONUP: "MOUSE_RIGHT",
    WM_MBUTTONDOWN: "MOUSE_MIDDLE",
    WM_MBUTTONUP: "MOUSE_MIDDLE",
}

MOUSE_MOVE_ENTRIES = {
    "MOUSE_UP",
    "MOUSE_DOWN",
    "MOUSE_LEFT_MOVE",
    "MOUSE_RIGHT_MOVE",
}

KEYBOARD_VKS = {
    "BACKSPACE": {0x08},
    "TAB": {0x09},
    "ENTER": {0x0D},
    "SHIFT": {0x10, 0xA0, 0xA1},
    "CTRL": {0x11, 0xA2, 0xA3},
    "CONTROL": {0x11, 0xA2, 0xA3},
    "ALT": {0x12, 0xA4, 0xA5},
    "PAUSE": {0x13},
    "CAPSLOCK": {0x14},
    "CAPS": {0x14},
    "ESC": {0x1B},
    "ESCAPE": {0x1B},
    "SPACE": {0x20},
    "PAGEUP": {0x21},
    "PAGEDOWN": {0x22},
    "END": {0x23},
    "HOME": {0x24},
    "LEFT": {0x25},
    "UP": {0x26},
    "RIGHT": {0x27},
    "DOWN": {0x28},
    "INSERT": {0x2D},
    "DELETE": {0x2E},
    "NUM0": {0x60},
    "NUM1": {0x61},
    "NUM2": {0x62},
    "NUM3": {0x63},
    "NUM4": {0x64},
    "NUM5": {0x65},
    "NUM6": {0x66},
    "NUM7": {0x67},
    "NUM8": {0x68},
    "NUM9": {0x69},
    "NUM*": {0x6A},
    "NUM+": {0x6B},
    "NUM-": {0x6D},
    "NUM.": {0x6E},
    "NUM/": {0x6F},
    ";": {0xBA},
    "=": {0xBB},
    ",": {0xBC},
    "-": {0xBD},
    ".": {0xBE},
    "/": {0xBF},
    "`": {0xC0},
    "[": {0xDB},
    "\\": {0xDC},
    "]": {0xDD},
    "'": {0xDE},
}

KEYBOARD_ENTRIES_BY_VK = {}

for number in range(10):
    KEYBOARD_VKS[str(number)] = {0x30 + number}

for offset, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    KEYBOARD_VKS[letter] = {0x41 + offset}

for index in range(1, 13):
    KEYBOARD_VKS[f"F{index}"] = {0x6F + index}

for entry, vks in KEYBOARD_VKS.items():
    if entry in {"CONTROL", "CAPS", "ESCAPE"}:
        continue

    for vk in vks:
        KEYBOARD_ENTRIES_BY_VK.setdefault(vk, entry)


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


LowLevelProc = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


@dataclass(frozen=True)
class InputBlockSpec:
    keyboard_vks: frozenset
    mouse_buttons: frozenset
    block_mouse_move: bool = False

    def empty(self):
        return not self.keyboard_vks and not self.mouse_buttons and not self.block_mouse_move


class PhysicalInputBlocker:
    def __init__(self, spec, allow_current_process=True, keyboard_event_callback=None):
        self.spec = spec
        self.allow_current_process = allow_current_process
        self.keyboard_event_callback = keyboard_event_callback
        self.current_pid = os.getpid()
        self._stop_event = threading.Event()
        self._started_event = threading.Event()
        self._thread = None
        self._thread_id = None
        self._error = None
        self._keyboard_hook = None
        self._mouse_hook = None
        self._keyboard_proc = None
        self._mouse_proc = None
        self._user32 = None
        self._kernel32 = None

    def start(self):
        if self.spec.empty():
            return False

        if self._thread is not None:
            return True

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._started_event.wait(2)

        if self._error is not None:
            self.stop()
            raise self._error

        return True

    def stop(self):
        self._stop_event.set()

        if self._user32 is not None and self._thread_id is not None:
            self._user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1)

        self._thread = None
        self._thread_id = None

    def _run(self):
        try:
            self._configurar_winapi()
            self._thread_id = self._kernel32.GetCurrentThreadId()
            self._keyboard_proc = LowLevelProc(self._keyboard_callback)
            self._mouse_proc = LowLevelProc(self._mouse_callback)

            hinstance = self._kernel32.GetModuleHandleW(None)

            if self.spec.keyboard_vks:
                self._keyboard_hook = self._user32.SetWindowsHookExW(
                    WH_KEYBOARD_LL,
                    self._keyboard_proc,
                    hinstance,
                    0,
                )
                if not self._keyboard_hook:
                    raise ctypes.WinError(ctypes.GetLastError())

            if self.spec.mouse_buttons or self.spec.block_mouse_move:
                self._mouse_hook = self._user32.SetWindowsHookExW(
                    WH_MOUSE_LL,
                    self._mouse_proc,
                    hinstance,
                    0,
                )
                if not self._mouse_hook:
                    raise ctypes.WinError(ctypes.GetLastError())

            self._started_event.set()
            msg = wintypes.MSG()

            while not self._stop_event.is_set():
                resultado = self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if resultado <= 0:
                    break

        except Exception as erro:
            self._error = erro
            self._started_event.set()
        finally:
            self._desinstalar_hooks()

    def _keyboard_callback(self, code, wparam, lparam):
        if (
            code == HC_ACTION
            and int(wparam) in KEYBOARD_MESSAGES
            and not self._foreground_is_current_process()
        ):
            info = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if int(info.vkCode) in self.spec.keyboard_vks:
                self._emitir_evento_teclado_bloqueado(int(info.vkCode), int(wparam))
                return 1

        return self._user32.CallNextHookEx(self._keyboard_hook, code, wparam, lparam)

    def _emitir_evento_teclado_bloqueado(self, vk_code, message):
        if self.keyboard_event_callback is None:
            return

        estado = "UP" if message in {WM_KEYUP, WM_SYSKEYUP} else "DOWN"
        entrada = entrada_por_vk(vk_code)

        try:
            self.keyboard_event_callback(
                {
                    "tipo": "TECLADO",
                    "numero": "",
                    "dispositivo": "Teclado bloqueado em segundo plano",
                    "id": "",
                    "entrada": entrada,
                    "acao": estado,
                    "detalhe": f"VK={vk_code:02X}",
                    "_origem": "HOOK_TECLADO",
                    "_ignorar_dispositivo": True,
                }
            )
        except Exception:
            pass

    def _mouse_callback(self, code, wparam, lparam):
        if code == HC_ACTION and not self._foreground_is_current_process():
            mensagem = int(wparam)

            if mensagem == WM_MOUSEMOVE and self.spec.block_mouse_move:
                return 1

            botao = MOUSE_BUTTON_MESSAGES.get(mensagem)
            if botao in self.spec.mouse_buttons:
                return 1

            if mensagem == WM_MOUSEWHEEL and "MOUSE_WHEEL" in self.spec.mouse_buttons:
                return 1

            if mensagem in {WM_XBUTTONDOWN, WM_XBUTTONUP}:
                info = ctypes.cast(lparam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                xbutton = (int(info.mouseData) >> 16) & 0xFFFF
                if xbutton == XBUTTON1 and "MOUSE_BUTTON_4" in self.spec.mouse_buttons:
                    return 1
                if xbutton == XBUTTON2 and "MOUSE_BUTTON_5" in self.spec.mouse_buttons:
                    return 1

        return self._user32.CallNextHookEx(self._mouse_hook, code, wparam, lparam)

    def _foreground_is_current_process(self):
        if not self.allow_current_process:
            return False

        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return False

        pid = wintypes.DWORD(0)
        self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value) == self.current_pid

    def _desinstalar_hooks(self):
        if self._user32 is None:
            return

        for hook in (self._keyboard_hook, self._mouse_hook):
            if hook:
                self._user32.UnhookWindowsHookEx(hook)

        self._keyboard_hook = None
        self._mouse_hook = None

    def _configurar_winapi(self):
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

        self._user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            LowLevelProc,
            wintypes.HINSTANCE,
            wintypes.DWORD,
        ]
        self._user32.SetWindowsHookExW.restype = wintypes.HHOOK

        self._user32.CallNextHookEx.argtypes = [
            wintypes.HHOOK,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        self._user32.CallNextHookEx.restype = ctypes.c_ssize_t

        self._user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        self._user32.UnhookWindowsHookEx.restype = wintypes.BOOL

        self._user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self._user32.GetMessageW.restype = wintypes.BOOL

        self._user32.PostThreadMessageW.argtypes = [
            wintypes.DWORD,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        self._user32.PostThreadMessageW.restype = wintypes.BOOL

        self._user32.GetForegroundWindow.argtypes = []
        self._user32.GetForegroundWindow.restype = wintypes.HWND

        self._user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self._user32.GetWindowThreadProcessId.restype = wintypes.DWORD

        self._kernel32.GetCurrentThreadId.argtypes = []
        self._kernel32.GetCurrentThreadId.restype = wintypes.DWORD

        self._kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self._kernel32.GetModuleHandleW.restype = wintypes.HMODULE


def criar_especificacao_bloqueio(perfis):
    keyboard_vks = set()
    mouse_buttons = set()
    block_mouse_move = False

    for perfil in perfis:
        configuracao = perfil.get("configuracao") or perfil

        for botao in configuracao.get("botoes", []):
            for entrada in normalizar_entradas_botao(botao):
                if entrada.startswith("MOUSE_"):
                    if entrada in MOUSE_MOVE_ENTRIES:
                        block_mouse_move = True
                    else:
                        mouse_buttons.add(entrada)
                    continue

                keyboard_vks.update(vks_por_entrada(entrada))

    return InputBlockSpec(
        keyboard_vks=frozenset(keyboard_vks),
        mouse_buttons=frozenset(mouse_buttons),
        block_mouse_move=block_mouse_move,
    )


def vks_por_entrada(entrada):
    entrada = normalizar_rotulo_entrada(entrada)

    if entrada.startswith("VK_"):
        try:
            vk = int(entrada[3:], 16)
        except ValueError:
            return set()

        return {vk} if 0 <= vk <= 0xFF else set()

    return set(KEYBOARD_VKS.get(entrada, set()))


def entrada_por_vk(vk_code):
    return KEYBOARD_ENTRIES_BY_VK.get(vk_code, f"VK_{vk_code:02X}")
