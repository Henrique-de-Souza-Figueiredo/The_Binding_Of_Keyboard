# Distribuicao

## Executavel pronto

O executavel gerado fica em:

```powershell
dist\The Binding Of Keyboard.exe
```

Esse arquivo pode ser copiado para outro computador Windows e aberto sem PyCharm.

## Requisito no computador de destino

Para criar controles virtuais Xbox, o computador precisa ter o driver ViGEmBus instalado.
Sem esse driver, o app abre, mas o `Start` pode falhar ao criar o gamepad virtual.

## Gerar novo exe

Use:

```powershell
.\build_exe.bat
```

O script usa `.venv`, instala as dependencias de `requirements.txt` e gera o exe com PyInstaller.
