# The Binding of Keyboard - Contexto do Projeto

Este arquivo existe para dar contexto a futuros contribuidores e outros chats de IA, sem precisar redescobrir toda a base do projeto.

## Objetivo

The Binding of Keyboard e uma ferramenta desktop para Windows que detecta multiplos teclados e mouses via Raw Input, permite associar perfis a dispositivos especificos e mapeia entradas fisicas para botoes de controle virtual.

O produto final esperado e:

- detectar cada teclado e mouse separadamente;
- permitir criar perfis de configuracao;
- vincular cada perfil a um teclado e mouse especifico, ou a qualquer dispositivo;
- mapear entradas fisicas para botoes de controle Xbox, PlayStation ou Nintendo;
- futuramente emitir saida real de gamepad virtual, provavelmente usando `vgamepad`.

## Estado Atual

O projeto atualmente tem uma interface Tkinter e um monitor Raw Input.

A interface principal fica em `interface/app.py`.

Atualizacao recente:

- o runtime pode executar ate 6 perfis ao mesmo tempo, criando um controle virtual Xbox por slot ativo;
- controles de execucao sao adicionados sob demanda pelo botao `Adicionar controle`, ate o limite de 6;
- a selecao dos perfis dos controles ativos e salva em `execucao.controles`;
- existe janela `Teste` para acionar botoes/analogicos sem depender de teclado ou mouse;
- a janela `Execucao` mostra qual controle recebeu cada acao;
- perfis podem ser importados/exportados individualmente em JSON;
- mapeamentos aceitam multiplas entradas no campo `Entrada`, separadas por virgula ou ponto e virgula.

Funcionalidades atuais da interface:

- criar, renomear, excluir e salvar perfis de configuracao;
- selecionar um padrao de controle: `Xbox`, `PlayStation` ou `Nintendo`;
- ao trocar o padrao de controle, os botoes mostrados sao recriados automaticamente;
- perfis podem salvar IDs de teclado e mouse selecionados;
- ao selecionar um perfil, a tela atualiza os botoes e os dispositivos salvos daquele perfil;
- os selects de dispositivo mostram o teclado/mouse salvo no perfil atual e permitem trocar no mesmo select;
- existe uma janela de terminal que monitora eventos Raw Input de teclados e mouses;
- ao adicionar ou atualizar um botao, abre uma modal com o texto `aperte uma tecla`;
- ao pressionar uma tecla nessa modal, ela e colocada no campo `Entrada` e o botao e adicionado/atualizado;
- tambem existe um botao `Capturar` para capturar somente o campo de entrada sem salvar imediatamente.

O arquivo de configuracao fica em `config/button_configs.json`.

No momento em que este arquivo foi criado, o projeto ainda nao estava inicializado como repositorio Git. O comando `git status` retornou: `fatal: not a git repository`.

## Como Rodar

Abrir a interface grafica:

```powershell
python main.py
```

Ou, no Windows, usar a venv automaticamente:

```powershell
.\run.bat
```

## Gerar Executavel

Gerar um `.exe` para copiar para outros computadores Windows:

```powershell
.\build_exe.bat
```

O executavel fica em:

```powershell
dist\The Binding Of Keyboard.exe
```

O exe dispensa PyCharm e Python instalado no computador de destino. Para a saida de controles virtuais funcionar, o computador ainda precisa ter o driver ViGEmBus instalado.

Listar dispositivos Raw Input:

```powershell
python main.py --list
```

Monitorar eventos Raw Input no terminal:

```powershell
python main.py --monitor
```

## Arquivos Principais

`main.py`

- ponto de entrada CLI;
- abre a interface Tkinter quando nenhum argumento e passado;
- suporta `--list` e `--monitor`.

`interface/app.py`

- interface principal;
- define presets de controle e entradas padrao;
- controla edicao de perfis, selecao de dispositivos, mapeamento de botoes, modal de captura, leitura/salvamento do JSON e janela de terminal.

`devices/device_manager.py`

- armazena dispositivos detectados;
- cria IDs estaveis a partir do path Raw Input usando SHA-1;
- separa teclados e mouses;
- gera nomes amigaveis como `Teclado VID_xxxx PID_yyyy`.

`input/raw_input.py`

- integracao com Windows Raw Input usando `ctypes`;
- enumera teclados e mouses;
- registra uma janela oculta Raw Input;
- emite eventos normalizados por callback opcional.

`config/button_configs.json`

- dados locais de perfis/configuracoes;
- pode conter IDs especificos da maquina local.

`tools/`

- scripts auxiliares/legados para diagnostico manual.

## Formato Atual da Configuracao

Os perfis ficam dentro de `configuracoes`.

Exemplo:

```json
{
  "configuracoes": {
    "Padrao": {
      "padrao": "Xbox",
      "dispositivos": {
        "teclado": "",
        "mouse": ""
      },
      "botoes": [
        {
          "nome": "A",
          "entrada": "SPACE",
          "acao": "A"
        }
      ]
    }
  }
}
```

Significado dos campos:

- `padrao`: layout de controle. Valores esperados: `Xbox`, `PlayStation`, `Nintendo`.
- `dispositivos.teclado`: ID estavel de teclado vindo do `DeviceManager`; string vazia significa qualquer teclado.
- `dispositivos.mouse`: ID estavel de mouse vindo do `DeviceManager`; string vazia significa qualquer mouse.
- `botoes`: lista de mapeamentos.
- `botoes[].nome`: nome exibido para o mapeamento.
- `botoes[].entrada`: tecla/entrada fisica.
- `botoes[].acao`: botao alvo do controle.

Configuracoes antigas sao normalizadas ao carregar:

- sem `padrao` vira `Xbox`;
- sem `dispositivos` vira `{ "teclado": "", "mouse": "" }`;
- sem `botoes` ou com `botoes` vazio vira o mapeamento padrao do preset selecionado.

Tambem existe a chave opcional `execucao` no topo do JSON:

```json
{
  "execucao": {
    "controles": ["Padrao", "", "", "", "", ""],
    "stick_intensity": 100,
    "mouse_pulse_ms": 60,
    "mouse_deadzone": 0
  }
}
```

## Detalhes Importantes

IDs de dispositivo sao gerados a partir do path Raw Input:

```python
digest = hashlib.sha1(normalized_path.encode("utf-8")).hexdigest()
return digest[:12].upper()
```

Isso significa que os IDs salvos devem ser estaveis para o mesmo path Raw Input no Windows, mas podem mudar entre maquinas ou apos alteracoes de driver/dispositivo.

A interface lista dispositivos criando um `DeviceManager`, criando um `RawInputMonitor` e chamando `listar_dispositivos()`. Nao e necessario iniciar o loop completo do monitor para popular os selects.

A janela de terminal usa `RawInputMonitor` em uma thread de fundo e envia eventos para uma fila Tk.

A modal de captura em `interface/app.py` usa Raw Input temporario e permite escolher o modo de captura: teclado, botao do mouse, movimento do mouse ou qualquer entrada.

## Dependencias

`requirements.txt` atualmente contem:

```text
pywin32
vgamepad
hidapi
```

O codigo usa biblioteca padrao, APIs do Windows via `ctypes` e `vgamepad` para criar controles virtuais Xbox.

## Verificacao Usada Ate Agora

Apos mudancas na interface, a sintaxe foi verificada com:

```powershell
python -m py_compile interface\app.py
```

Ainda nao existem testes automatizados.

## Limitacoes Conhecidas

- O app e somente Windows, pois depende de Windows Raw Input.
- A saida virtual atual e Xbox via `vgamepad`; presets PlayStation/Nintendo sao normalizados para esse backend.
- Para usar controles reais, `vgamepad` e o driver ViGEmBus precisam estar instalados e funcionais.
- Algumas strings antigas em portugues podem aparecer com mojibake se o encoding do arquivo for tratado incorretamente.
- `config/button_configs.json` pode conter dados especificos da maquina local e deve ser revisado antes de ir para o GitHub.
- Ja existe `.gitignore` ignorando `.venv`, caches, IDE e `config/button_configs.json`.

## Proximos Passos Recomendados

1. Inicializar Git, se ainda nao tiver sido feito.

2. Adicionar um `README.md`.

Incluir:

- o que o projeto faz;
- requisito Windows;
- instrucoes de instalacao;
- como rodar `python main.py`;
- como listar/monitorar dispositivos.

3. Testar o fluxo ponta a ponta com dispositivos reais.

Validar:

- captura Raw Input por dispositivo;
- execucao de multiplos perfis;
- criacao de ate 6 controles virtuais;
- leitura das entradas por um jogo, emulador ou tester de gamepad.

4. Melhorar empacotamento.

Criar um instalador ou atalho que prepare dependencias, valide ViGEmBus e abra o app pela `.venv`.

5. Expandir testes para logica pura.

Bons primeiros alvos:

- normalizacao de config;
- mapeamento padrao por preset;
- conversao label de dispositivo para ID;
- mapeamento evento -> acao quando isso for implementado.

6. Separar `interface/app.py` se ele continuar crescendo.

Modulos possiveis:

- `config/store.py` para carregar/salvar/normalizar;
- `mapping/presets.py` para presets e mapeamentos padrao;
- `interface/capture_modal.py` para dialogs de captura;
- `runtime/mapper.py` para traduzir eventos Raw Input em acoes de controle.

## Orientacao Para Outros Chats de IA

Comece lendo:

1. `PROJECT_CONTEXT.md`
2. `main.py`
3. `interface/app.py`
4. `devices/device_manager.py`
5. `input/raw_input.py`

Evite reescritas grandes. O projeto ainda e pequeno, e o principal risco e quebrar o fluxo Raw Input ou o formato do JSON de perfis.

Antes de mudar comportamento, rode:

```powershell
python -m py_compile interface\app.py
```

Se mudar codigo Raw Input, teste no Windows com dispositivos reais:

```powershell
python main.py --list
python main.py --monitor
```

Mantenha o JSON de perfis retrocompativel quando possivel, porque a interface normaliza configuracoes antigas ao carregar.

---

# The Binding of Keyboard - Project Context

This file exists to give future contributors and AI chats enough context to continue the project without rediscovering the whole codebase.

## Goal

The Binding of Keyboard is a Windows desktop tool for detecting multiple keyboards and mice through Raw Input, assigning profiles to specific devices, and mapping physical keyboard/mouse inputs to virtual controller buttons.

The intended final product is:

- detect each keyboard and mouse independently;
- let the user create configuration profiles;
- bind each profile to a specific keyboard and mouse, or to any device;
- map physical inputs to Xbox, PlayStation, or Nintendo controller buttons;
- later, emit a real virtual gamepad output, probably through `vgamepad`.

## Current State

The project currently has a Tkinter interface and a Raw Input monitor.

The GUI is in `interface/app.py`.

Current GUI features:

- create, rename, delete, and save configuration profiles;
- select a controller preset: `Xbox`, `PlayStation`, or `Nintendo`;
- changing the controller preset automatically rebuilds the shown button mappings;
- profiles can store selected keyboard and mouse device IDs;
- profile selection updates the shown mappings and selected devices;
- device selectors show the saved keyboard/mouse for the current profile and allow changing them in the same select;
- a terminal window can monitor Raw Input events from keyboards and mice;
- adding/updating a button opens a modal saying `aperte uma tecla`;
- after pressing a key in that modal, the key is inserted into the `Entrada` field and the button is added/updated;
- there is also a `Capturar` button to capture only the input field without saving immediately.

The configuration file is `config/button_configs.json`.

The project was not initialized as a Git repository when this file was first created. `git status` returned: `fatal: not a git repository`.

## Entry Points

Run the graphical app:

```powershell
python main.py
```

Or use the local virtual environment automatically:

```powershell
.\run.bat
```

List Raw Input devices:

```powershell
python main.py --list
```

Monitor Raw Input events in the terminal:

```powershell
python main.py --monitor
```

## Main Files

`main.py`

- CLI entry point.
- Opens the Tkinter interface when no flags are passed.
- Supports `--list` and `--monitor`.

`interface/app.py`

- Main GUI.
- Defines controller presets and default inputs.
- Handles profile editing, device selection, button mapping, capture modal, saving/loading JSON, and terminal window.

`devices/device_manager.py`

- Stores detected devices.
- Builds stable device IDs from the Raw Input device path using SHA-1.
- Separates keyboards and mice.
- Provides display names such as `Teclado VID_xxxx PID_yyyy`.

`input/raw_input.py`

- Windows Raw Input integration through `ctypes`.
- Enumerates keyboards and mice.
- Registers a hidden Raw Input window.
- Emits normalized events through an optional callback.

`config/button_configs.json`

- Local profile/configuration data.
- May contain machine-specific device IDs.

`tools/`

- Auxiliary/legacy scripts for manual diagnostics.

## Current Config Shape

Profiles are stored under `configuracoes`.

Example:

```json
{
  "configuracoes": {
    "Padrao": {
      "padrao": "Xbox",
      "dispositivos": {
        "teclado": "",
        "mouse": ""
      },
      "botoes": [
        {
          "nome": "A",
          "entrada": "SPACE",
          "acao": "A"
        }
      ]
    }
  }
}
```

Field meanings:

- `padrao`: controller layout preset. Expected values: `Xbox`, `PlayStation`, `Nintendo`.
- `dispositivos.teclado`: stable keyboard ID from `DeviceManager`; empty string means any keyboard.
- `dispositivos.mouse`: stable mouse ID from `DeviceManager`; empty string means any mouse.
- `botoes`: list of mappings.
- `botoes[].nome`: user-facing mapping name.
- `botoes[].entrada`: physical key/input label.
- `botoes[].acao`: target controller button name.

Old configs are normalized on load:

- missing `padrao` becomes `Xbox`;
- missing `dispositivos` becomes `{ "teclado": "", "mouse": "" }`;
- missing or empty `botoes` becomes the default mapping for the selected preset.

## Important Implementation Details

Device IDs are generated from the Raw Input path:

```python
digest = hashlib.sha1(normalized_path.encode("utf-8")).hexdigest()
return digest[:12].upper()
```

That means saved device IDs should be stable for the same Windows Raw Input path, but may differ across machines or after driver/device changes.

The GUI lists devices by creating a `DeviceManager`, creating a `RawInputMonitor`, and calling `listar_dispositivos()`. It does not need to start the full monitor loop just to populate the selects.

The terminal window uses `RawInputMonitor` in a background thread and sends events into a Tk queue.

The capture modal in `interface/app.py` uses a temporary Raw Input monitor and can capture keyboard input, mouse buttons, mouse movement, or any input.

## Dependencies

`requirements.txt` currently lists:

```text
pywin32
vgamepad
hidapi
```

Current code uses standard library + Windows APIs through `ctypes`, and `vgamepad` to create virtual Xbox controllers.

## Verification Used So Far

After GUI edits, syntax was checked with:

```powershell
python -m py_compile interface\app.py
```

No automated tests exist yet.

## Known Limitations

- The app is Windows-only because it depends on Windows Raw Input APIs.
- Current virtual output is Xbox through `vgamepad`; PlayStation/Nintendo presets are normalized into that backend.
- Real controller output requires `vgamepad` and a working ViGEmBus driver.
- Some user-visible Portuguese strings in older code may show mojibake if file encoding is mishandled.
- `config/button_configs.json` may contain local machine-specific data and should be reviewed before committing.
- A `.gitignore` already exists for `.venv`, caches, IDE files, and `config/button_configs.json`.

## Recommended Next Steps

1. Initialize Git, if it has not been done yet.

2. Add a `README.md`.

Include:

- what the project does;
- Windows-only requirement;
- setup instructions;
- how to run `python main.py`;
- how to list/monitor devices.

3. Test the end-to-end flow with real devices.

Validate:

- Raw Input capture per device;
- multiple profiles running at once;
- up to 6 virtual controllers;
- input visibility in a game, emulator, or gamepad tester.

4. Improve packaging.

Create an installer or shortcut that prepares dependencies, validates ViGEmBus, and opens the app through `.venv`.

5. Add more tests around pure logic.

Good first targets:

- config normalization;
- controller preset default mapping;
- device label to ID mapping;
- event-to-action mapping once implemented.

6. Split `interface/app.py` if it grows further.

Potential modules:

- `config/store.py` for load/save/normalize;
- `mapping/presets.py` for presets and default mappings;
- `interface/capture_modal.py` for capture dialogs;
- `runtime/mapper.py` for translating Raw Input events into controller actions.

## Guidance For Future AI Chats

Start by reading:

1. `PROJECT_CONTEXT.md`
2. `main.py`
3. `interface/app.py`
4. `devices/device_manager.py`
5. `input/raw_input.py`

Avoid broad rewrites. The project is still small, and the main risk is breaking the Raw Input flow or the profile JSON shape.

Before changing behavior, run:

```powershell
python -m py_compile interface\app.py
```

If changing Raw Input code, test on Windows with real keyboard/mouse devices using:

```powershell
python main.py --list
python main.py --monitor
```

Keep the profile JSON backward-compatible when possible, because the GUI currently normalizes older configs on load.
