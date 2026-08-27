import ctypes
from ctypes import wintypes

# ============================================================
# DLLs
# ============================================================

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ============================================================
# TIPOS
# ============================================================

LRESULT = ctypes.c_ssize_t

# ============================================================
# CONSTANTES
# ============================================================

WM_INPUT = 0x00FF
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


# ============================================================
# ESTRUTURAS
# ============================================================

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


class RAWINPUT(ctypes.Union):
    _fields_ = [
        ("mouse", RAWMOUSE),
        ("keyboard", RAWKEYBOARD),
    ]


# ============================================================
# TECLAS
# ============================================================

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


# ============================================================
# DISPOSITIVOS
# ============================================================

dispositivos = {}

contador_teclados = 0
contador_mouses = 0


# ============================================================
# NOME DO DISPOSITIVO
# ============================================================

def obter_nome_dispositivo(handle):

    tamanho = wintypes.UINT(0)

    resultado = user32.GetRawInputDeviceInfoW(
        handle,
        RIDI_DEVICENAME,
        None,
        ctypes.byref(tamanho)
    )

    if resultado == -1 or tamanho.value == 0:
        return "Dispositivo desconhecido"

    buffer = ctypes.create_unicode_buffer(
        tamanho.value + 1
    )

    user32.GetRawInputDeviceInfoW(
        handle,
        RIDI_DEVICENAME,
        buffer,
        ctypes.byref(tamanho)
    )

    return buffer.value


# ============================================================
# IDENTIFICAR DISPOSITIVO
# ============================================================

def identificar_dispositivo(handle, tipo):

    global contador_teclados
    global contador_mouses

    # Já conhecemos esse dispositivo
    if handle in dispositivos:
        return dispositivos[handle]

    nome = obter_nome_dispositivo(handle)

    if tipo == RIM_TYPEKEYBOARD:

        contador_teclados += 1

        dispositivo = {
            "numero": contador_teclados,
            "tipo": "TECLADO",
            "nome": nome
        }

        print()
        print("=" * 70)
        print(f"NOVO TECLADO {contador_teclados}")
        print(f"Dispositivo: {nome}")
        print("=" * 70)

    else:

        contador_mouses += 1

        dispositivo = {
            "numero": contador_mouses,
            "tipo": "MOUSE",
            "nome": nome
        }

        print()
        print("=" * 70)
        print(f"NOVO MOUSE {contador_mouses}")
        print(f"Dispositivo: {nome}")
        print("=" * 70)

    dispositivos[handle] = dispositivo

    return dispositivo


# ============================================================
# PROCESSAR TECLADO
# ============================================================

def processar_teclado(teclado, dispositivo):

    tecla = TECLAS.get(
        teclado.VKey,
        f"VK_{teclado.VKey:02X}"
    )

    if teclado.Flags & RI_KEY_BREAK:

        estado = "UP"

    else:

        estado = "DOWN"

    print(
        f"[TECLADO {dispositivo['numero']}] "
        f"{tecla:<10} {estado}"
    )


# ============================================================
# PROCESSAR MOUSE
# ============================================================

def processar_mouse(mouse, dispositivo):

    numero = dispositivo["numero"]

    # Movimento
    if mouse.lLastX != 0 or mouse.lLastY != 0:

        print(
            f"[MOUSE {numero}] "
            f"MOVE "
            f"X={mouse.lLastX:+5} "
            f"Y={mouse.lLastY:+5}"
        )

    flags = mouse.buttons.usButtonFlags

    if flags & RI_MOUSE_LEFT_BUTTON_DOWN:
        print(f"[MOUSE {numero}] LEFT DOWN")

    if flags & RI_MOUSE_LEFT_BUTTON_UP:
        print(f"[MOUSE {numero}] LEFT UP")

    if flags & RI_MOUSE_RIGHT_BUTTON_DOWN:
        print(f"[MOUSE {numero}] RIGHT DOWN")

    if flags & RI_MOUSE_RIGHT_BUTTON_UP:
        print(f"[MOUSE {numero}] RIGHT UP")

    if flags & RI_MOUSE_MIDDLE_BUTTON_DOWN:
        print(f"[MOUSE {numero}] MIDDLE DOWN")

    if flags & RI_MOUSE_MIDDLE_BUTTON_UP:
        print(f"[MOUSE {numero}] MIDDLE UP")

    if flags & RI_MOUSE_BUTTON_4_DOWN:
        print(f"[MOUSE {numero}] BUTTON 4 DOWN")

    if flags & RI_MOUSE_BUTTON_4_UP:
        print(f"[MOUSE {numero}] BUTTON 4 UP")

    if flags & RI_MOUSE_BUTTON_5_DOWN:
        print(f"[MOUSE {numero}] BUTTON 5 DOWN")

    if flags & RI_MOUSE_BUTTON_5_UP:
        print(f"[MOUSE {numero}] BUTTON 5 UP")

    if flags & RI_MOUSE_WHEEL:

        print(
            f"[MOUSE {numero}] WHEEL"
        )


# ============================================================
# PROCESSAR RAW INPUT
# ============================================================

def processar_raw_input(hrawinput):

    tamanho = wintypes.UINT(0)

    resultado = user32.GetRawInputData(
        hrawinput,
        RID_INPUT,
        None,
        ctypes.byref(tamanho),
        ctypes.sizeof(RAWINPUTHEADER)
    )

    if resultado == -1:
        return

    buffer = ctypes.create_string_buffer(
        tamanho.value
    )

    resultado = user32.GetRawInputData(
        hrawinput,
        RID_INPUT,
        buffer,
        ctypes.byref(tamanho),
        ctypes.sizeof(RAWINPUTHEADER)
    )

    if resultado == -1:
        return

    header = RAWINPUTHEADER.from_buffer_copy(
        buffer
    )

    dispositivo = identificar_dispositivo(
        header.hDevice,
        header.dwType
    )

    offset = ctypes.sizeof(
        RAWINPUTHEADER
    )

    if header.dwType == RIM_TYPEKEYBOARD:

        teclado = RAWKEYBOARD.from_buffer_copy(
            buffer,
            offset
        )

        processar_teclado(
            teclado,
            dispositivo
        )

    elif header.dwType == RIM_TYPEMOUSE:

        mouse = RAWMOUSE.from_buffer_copy(
            buffer,
            offset
        )

        processar_mouse(
            mouse,
            dispositivo
        )


# ============================================================
# WINDOW PROCEDURE
# ============================================================

WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM
)


@WNDPROC
def janela_proc(hwnd, msg, wparam, lparam):

    if msg == WM_INPUT:

        processar_raw_input(
            lparam
        )

        return 0

    if msg == WM_DESTROY:

        user32.PostQuitMessage(0)

        return 0

    return user32.DefWindowProcW(
        hwnd,
        msg,
        wparam,
        lparam
    )


# ============================================================
# WNDCLASS
# ============================================================

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

# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("       MONITOR DE TECLADOS E MOUSES")
    print("                  RAW INPUT")
    print("=" * 70)

    print()
    print("Pressione teclas ou movimente os mouses.")
    print("CTRL+C para sair.")
    print()

    # --------------------------------------------------------
    # Instância do programa
    # --------------------------------------------------------

    hinstance = kernel32.GetModuleHandleW(None)

    nome_classe = "RawInputMonitorPython"

    # --------------------------------------------------------
    # Registrar classe
    # --------------------------------------------------------

    wc = WNDCLASS()

    wc.style = 0
    wc.lpfnWndProc = janela_proc
    wc.cbClsExtra = 0
    wc.cbWndExtra = 0
    wc.hInstance = hinstance
    wc.hIcon = None
    wc.hCursor = None
    wc.hbrBackground = None
    wc.lpszMenuName = None
    wc.lpszClassName = nome_classe

    resultado = user32.RegisterClassW(
        ctypes.byref(wc)
    )

    if not resultado:

        erro = ctypes.GetLastError()

        print(
            f"Erro ao registrar classe: {erro}"
        )

        return

    # --------------------------------------------------------
    # Criar janela invisível
    # --------------------------------------------------------

    hwnd = user32.CreateWindowExW(
        0,
        nome_classe,
        "Monitor Raw Input",
        0,
        0,
        0,
        0,
        0,
        None,
        None,
        hinstance,
        None
    )

    if not hwnd:

        erro = ctypes.GetLastError()

        print(
            f"Erro ao criar janela: {erro}"
        )

        return

    # --------------------------------------------------------
    # Registrar teclado e mouse
    # --------------------------------------------------------

    dispositivos_raw = (
        RAWINPUTDEVICE * 2
    )()

    # Teclado
    dispositivos_raw[0].usUsagePage = 0x01
    dispositivos_raw[0].usUsage = 0x06
    dispositivos_raw[0].dwFlags = RIDEV_INPUTSINK
    dispositivos_raw[0].hwndTarget = hwnd

    # Mouse
    dispositivos_raw[1].usUsagePage = 0x01
    dispositivos_raw[1].usUsage = 0x02
    dispositivos_raw[1].dwFlags = RIDEV_INPUTSINK
    dispositivos_raw[1].hwndTarget = hwnd

    resultado = user32.RegisterRawInputDevices(
        dispositivos_raw,
        2,
        ctypes.sizeof(RAWINPUTDEVICE)
    )

    if not resultado:

        erro = ctypes.GetLastError()

        print(
            f"Erro ao registrar Raw Input: {erro}"
        )

        return

    print("Raw Input registrado com sucesso!")
    print()
    print("-" * 70)

    # --------------------------------------------------------
    # Loop principal
    # --------------------------------------------------------

    msg = wintypes.MSG()

    try:

        while True:

            resultado = user32.GetMessageW(
                ctypes.byref(msg),
                hwnd,
                0,
                0
            )

            if resultado <= 0:
                break

            user32.TranslateMessage(
                ctypes.byref(msg)
            )

            user32.DispatchMessageW(
                ctypes.byref(msg)
            )

    except KeyboardInterrupt:

        print()
        print("-" * 70)
        print("Programa encerrado.")
        print("-" * 70)


# ============================================================
# EXECUTAR
# ============================================================

if __name__ == "__main__":
    main()
