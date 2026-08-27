import hid


def listar_dispositivos():
    dispositivos = hid.enumerate()

    teclados = []
    mouses = []

    for dispositivo in dispositivos:
        nome = dispositivo.get("product_string")
        fabricante = dispositivo.get("manufacturer_string")
        vid = dispositivo.get("vendor_id")
        pid = dispositivo.get("product_id")
        caminho = dispositivo.get("path")

        if not nome:
            nome = "Dispositivo desconhecido"

        info = {
            "nome": nome,
            "fabricante": fabricante,
            "vid": vid,
            "pid": pid,
            "path": caminho
        }

        # Uso da classe HID:
        # 0x01 = Generic Desktop
        # 0x02 = Mouse
        # 0x06 = Keyboard
        usage_page = dispositivo.get("usage_page")
        usage = dispositivo.get("usage")

        if usage_page == 0x01 and usage == 0x02:
            mouses.append(info)

        elif usage_page == 0x01 and usage == 0x06:
            teclados.append(info)

    print("\n" + "=" * 60)
    print("TECLADOS")
    print("=" * 60)

    if not teclados:
        print("Nenhum teclado encontrado.")

    for i, teclado in enumerate(teclados, 1):
        print(f"\nTeclado {i}")
        print(f"  Nome:        {teclado['nome']}")
        print(f"  Fabricante:  {teclado['fabricante']}")
        print(f"  VID:         {teclado['vid']:04X}")
        print(f"  PID:         {teclado['pid']:04X}")
        print(f"  Path:        {teclado['path']}")

    print("\n" + "=" * 60)
    print("MOUSES")
    print("=" * 60)

    if not mouses:
        print("Nenhum mouse encontrado.")

    for i, mouse in enumerate(mouses, 1):
        print(f"\nMouse {i}")
        print(f"  Nome:        {mouse['nome']}")
        print(f"  Fabricante:  {mouse['fabricante']}")
        print(f"  VID:         {mouse['vid']:04X}")
        print(f"  PID:         {mouse['pid']:04X}")
        print(f"  Path:        {mouse['path']}")

    print("\n" + "=" * 60)
    print(f"Total de teclados: {len(teclados)}")
    print(f"Total de mouses:   {len(mouses)}")
    print("=" * 60)


if __name__ == "__main__":
    listar_dispositivos()
