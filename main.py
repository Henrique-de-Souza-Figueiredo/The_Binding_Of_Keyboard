import argparse

from devices.device_manager import DeviceManager
from input.raw_input import RawInputMonitor
from interface.app import iniciar_interface


def main():
    parser = argparse.ArgumentParser(
        description="The Binding Of Keyboard - Raw Input + Device Manager"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista os dispositivos Raw Input e encerra.",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Abre o monitor Raw Input no terminal.",
    )
    args = parser.parse_args()

    if not args.list and not args.monitor:
        iniciar_interface()
        return

    device_manager = DeviceManager()
    raw_input = RawInputMonitor(device_manager)

    raw_input.listar_dispositivos()
    device_manager.imprimir()

    if args.list:
        return

    raw_input.iniciar()


if __name__ == "__main__":
    main()
