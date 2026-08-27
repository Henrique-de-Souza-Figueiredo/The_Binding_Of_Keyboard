import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from config.store import load_config, save_config
from devices.device_manager import DeviceManager
from input.raw_input import RawInputMonitor
from mapping.presets import CONTROLLER_PRESETS, botoes_do_padrao, criar_botoes_padrao
from runtime.activity import RuntimeActivityLog, activity_from_action, activity_message
from runtime.capture import captura_por_evento, chave_dispositivo_por_tipo
from runtime.gamepad import GamepadBackendError, XboxGamepadBackend
from runtime.input_blocker import (
    InputBlockSpec,
    PhysicalInputBlocker,
    criar_especificacao_bloqueio,
    vks_por_entrada,
)
from runtime.mapper import mapear_evento_para_acoes, normalizar_rotulo_entrada


APP_NAME = "The Binding Of Keyboard"
DISABLED_PROFILE_LABEL = "Desativado"
MAX_RUNTIME_CONTROLLERS = 6


def get_config_path():
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA")
        base_path = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base_path / APP_NAME / "button_configs.json"

    return Path(__file__).resolve().parent.parent / "config" / "button_configs.json"


CONFIG_PATH = get_config_path()


class TheBindingOfKeyboardApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1120x780")
        self.minsize(980, 720)

        self.configuracoes = {}
        self.configuracao_atual = None
        self.device_manager = DeviceManager()
        self.dispositivos_por_label = {}
        self.rodando = False
        self.runtime_queue = queue.Queue()
        self.runtime_device_manager = None
        self.runtime_monitor = None
        self.runtime_thread = None
        self.runtime_action_count = 0
        self.runtime_action_counts_by_slot = {}
        self.runtime_session_id = 0
        self.runtime_profiles = []
        self.runtime_activity_log = RuntimeActivityLog()
        self.runtime_activity_window = None
        self.gamepad_backends = {}
        self.input_blocker = None
        self.toggle_hotkey_blocker = None
        self.toggle_hotkey_queue = queue.Queue()
        self.toggle_hotkey_last_at = 0.0
        self.execucao_config = {}
        self.runtime_profile_combos = []
        self.terminal_window = None

        self._configurar_estilo()
        self._criar_variaveis()
        self._criar_layout()
        self._carregar_dispositivos()
        self._carregar_configuracoes()
        self._atualizar_estado_execucao()
        self._reiniciar_atalho_execucao()
        self.after(80, self._processar_fila_atalho_execucao)
        self.protocol("WM_DELETE_WINDOW", self._fechar_app)

    def _configurar_estilo(self):
        self.configure(bg="#f4f6f8")

        style = ttk.Style(self)

        if "vista" in style.theme_names():
            style.theme_use("vista")

        style.configure("TFrame", background="#f4f6f8")
        style.configure("Panel.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Header.TLabel", background="#f4f6f8", font=("Segoe UI", 18, "bold"))
        style.configure("Subheader.TLabel", background="#ffffff", font=("Segoe UI", 11, "bold"))
        style.configure("Muted.TLabel", background="#ffffff", foreground="#5d6875")
        style.configure("Status.TLabel", background="#ffffff", font=("Segoe UI", 10, "bold"))
        style.configure("TButton", padding=(10, 6))
        style.configure("Primary.TButton", padding=(14, 7))
        style.configure("Danger.TButton", padding=(14, 7))

    def _criar_variaveis(self):
        self.nome_config_var = tk.StringVar()
        self.nome_botao_var = tk.StringVar()
        self.entrada_var = tk.StringVar()
        self.acao_var = tk.StringVar()
        self.padrao_var = tk.StringVar(value="Xbox")
        self.teclado_var = tk.StringVar()
        self.mouse_var = tk.StringVar()
        self.runtime_profile_vars = []
        self.runtime_slot_status_vars = []
        self.stick_intensity_var = tk.IntVar(value=100)
        self.mouse_pulse_ms_var = tk.IntVar(value=60)
        self.mouse_deadzone_var = tk.IntVar(value=0)
        self.desativar_atalho_var = tk.StringVar()
        self.dispositivos_perfil_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Parado")

    def _criar_layout(self):
        root = ttk.Frame(self, padding=18)
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root)
        header.pack(fill=tk.X)

        ttk.Label(header, text=APP_NAME, style="Header.TLabel").pack(side=tk.LEFT)

        controls = ttk.Frame(header)
        controls.pack(side=tk.RIGHT)

        ttk.Button(
            controls,
            text="Execucao",
            command=self._abrir_execucao,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            controls,
            text="Teste",
            command=self._abrir_teste_controle,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            controls,
            text="Terminal",
            command=self._abrir_terminal,
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.start_button = ttk.Button(
            controls,
            text="Start",
            style="Primary.TButton",
            command=self._start,
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_button = ttk.Button(
            controls,
            text="Pare",
            style="Danger.TButton",
            command=self._alternar_execucao,
        )
        self.stop_button.pack(side=tk.LEFT)

        body = ttk.Frame(root)
        body.pack(fill=tk.BOTH, expand=True, pady=(16, 0))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._criar_painel_configuracoes(body)
        self._criar_painel_editor(body)

    def _criar_painel_configuracoes(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        panel.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
        panel.rowconfigure(1, weight=1)

        ttk.Label(panel, text="Configurações", style="Subheader.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.config_list = tk.Listbox(
            panel,
            width=28,
            height=20,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#ccd3dc",
            selectbackground="#2563eb",
            selectforeground="#ffffff",
            activestyle="none",
            font=("Segoe UI", 10),
        )
        self.config_list.grid(row=1, column=0, sticky="nsew", pady=(10, 12))
        self.config_list.bind("<<ListboxSelect>>", self._selecionar_configuracao_evento)

        ttk.Label(panel, text="Nome", style="Muted.TLabel").grid(row=2, column=0, sticky="w")
        name_row = ttk.Frame(panel, style="Panel.TFrame")
        name_row.grid(row=3, column=0, sticky="ew", pady=(4, 10))
        name_row.columnconfigure(0, weight=1)

        ttk.Entry(name_row, textvariable=self.nome_config_var).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 8),
        )
        ttk.Button(name_row, text="Criar", command=self._criar_configuracao).grid(
            row=0,
            column=1,
        )

        buttons = ttk.Frame(panel, style="Panel.TFrame")
        buttons.grid(row=4, column=0, sticky="ew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ttk.Button(buttons, text="Renomear", command=self._renomear_configuracao).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 6),
        )
        ttk.Button(buttons, text="Excluir", command=self._excluir_configuracao).grid(
            row=0,
            column=1,
            sticky="ew",
        )
        ttk.Button(buttons, text="Exportar", command=self._exportar_configuracao).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(0, 6),
            pady=(6, 0),
        )
        ttk.Button(buttons, text="Importar", command=self._importar_configuracao).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=(6, 0),
        )

        ttk.Label(panel, text="Teclado do perfil", style="Muted.TLabel").grid(
            row=5,
            column=0,
            sticky="w",
            pady=(14, 0),
        )
        self.keyboard_combo = ttk.Combobox(
            panel,
            textvariable=self.teclado_var,
            state="readonly",
        )
        self.keyboard_combo.grid(row=6, column=0, sticky="ew", pady=(4, 10))
        self.keyboard_combo.bind("<<ComboboxSelected>>", self._alterar_dispositivo_perfil)

        ttk.Label(panel, text="Mouse do perfil", style="Muted.TLabel").grid(
            row=7,
            column=0,
            sticky="w",
        )
        self.mouse_combo = ttk.Combobox(
            panel,
            textvariable=self.mouse_var,
            state="readonly",
        )
        self.mouse_combo.grid(row=8, column=0, sticky="ew", pady=(4, 10))
        self.mouse_combo.bind("<<ComboboxSelected>>", self._alterar_dispositivo_perfil)

        ttk.Label(
            panel,
            textvariable=self.dispositivos_perfil_var,
            style="Muted.TLabel",
            wraplength=240,
        ).grid(row=9, column=0, sticky="w", pady=(0, 10))

        ttk.Button(
            panel,
            text="Atualizar dispositivos",
            command=self._carregar_dispositivos,
        ).grid(row=10, column=0, sticky="ew")

        ttk.Label(panel, text="Perfis em execucao", style="Muted.TLabel").grid(
            row=11,
            column=0,
            sticky="w",
            pady=(14, 0),
        )

        self.runtime_profiles_frame = ttk.Frame(panel, style="Panel.TFrame")
        self.runtime_profiles_frame.grid(row=12, column=0, sticky="ew", pady=(4, 0))

        runtime_buttons = ttk.Frame(panel, style="Panel.TFrame")
        runtime_buttons.grid(row=13, column=0, sticky="ew", pady=(6, 0))
        runtime_buttons.columnconfigure(0, weight=1)

        self.add_runtime_control_button = ttk.Button(
            runtime_buttons,
            text="Adicionar controle",
            command=self._adicionar_controle_runtime,
        )
        self.add_runtime_control_button.grid(row=0, column=0, sticky="ew")

        settings_row = ttk.Frame(panel, style="Panel.TFrame")
        settings_row.grid(row=14, column=0, sticky="ew", pady=(12, 0))
        settings_row.columnconfigure(1, weight=1)

        ttk.Label(settings_row, text="Analogico %", style="Muted.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Spinbox(
            settings_row,
            from_=1,
            to=100,
            textvariable=self.stick_intensity_var,
            width=8,
        ).grid(row=0, column=1, sticky="e")

        ttk.Label(settings_row, text="Pulso mouse ms", style="Muted.TLabel").grid(
            row=1,
            column=0,
            sticky="w",
            pady=(6, 0),
        )
        ttk.Spinbox(
            settings_row,
            from_=10,
            to=500,
            textvariable=self.mouse_pulse_ms_var,
            width=8,
        ).grid(row=1, column=1, sticky="e", pady=(6, 0))

        ttk.Label(settings_row, text="Zona morta mouse", style="Muted.TLabel").grid(
            row=2,
            column=0,
            sticky="w",
            pady=(6, 0),
        )
        ttk.Spinbox(
            settings_row,
            from_=0,
            to=100,
            textvariable=self.mouse_deadzone_var,
            width=8,
        ).grid(row=2, column=1, sticky="e", pady=(6, 0))

        ttk.Label(settings_row, text="Atalho para parar", style="Muted.TLabel").grid(
            row=3,
            column=0,
            sticky="w",
            pady=(6, 0),
        )

        shortcut_row = ttk.Frame(settings_row, style="Panel.TFrame")
        shortcut_row.grid(row=3, column=1, sticky="ew", pady=(6, 0))
        shortcut_row.columnconfigure(0, weight=1)

        ttk.Entry(
            shortcut_row,
            textvariable=self.desativar_atalho_var,
            width=8,
            state="readonly",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            shortcut_row,
            text="Capturar",
            command=self._capturar_atalho_desativar,
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(
            shortcut_row,
            text="Limpar",
            command=self._limpar_atalho_desativar,
        ).grid(row=0, column=2)

    def _criar_painel_editor(self, parent):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(3, weight=1)

        top = ttk.Frame(panel, style="Panel.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)

        ttk.Label(top, text="Botões configurados", style="Subheader.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(top, textvariable=self.status_var, style="Status.TLabel").grid(
            row=0,
            column=1,
            sticky="e",
        )

        ttk.Label(
            panel,
            text="Capture uma entrada fisica e escolha o botao de controle alvo. Nesta etapa ainda e configuracao visual.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, 14))

        form = ttk.Frame(panel, style="Panel.TFrame")
        form.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=1)
        form.columnconfigure(3, weight=1)
        form.columnconfigure(4, weight=0)

        ttk.Label(form, text="Padrao", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.preset_combo = ttk.Combobox(
            form,
            textvariable=self.padrao_var,
            values=list(CONTROLLER_PRESETS),
            state="readonly",
        )
        self.preset_combo.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.preset_combo.bind("<<ComboboxSelected>>", self._alterar_padrao)

        ttk.Label(form, text="Nome", style="Muted.TLabel").grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Label(form, text="Entrada", style="Muted.TLabel").grid(row=0, column=2, sticky="w", padx=(10, 0))
        ttk.Label(form, text="Botao do controle", style="Muted.TLabel").grid(row=0, column=3, sticky="w", padx=(10, 0))

        ttk.Entry(form, textvariable=self.nome_botao_var).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(10, 0),
            pady=(4, 0),
        )
        ttk.Entry(form, textvariable=self.entrada_var).grid(
            row=1,
            column=2,
            sticky="ew",
            padx=(10, 0),
            pady=(4, 0),
        )
        ttk.Button(
            form,
            text="Capturar",
            command=self._capturar_entrada_para_formulario,
        ).grid(row=1, column=4, sticky="ew", padx=(8, 0), pady=(4, 0))
        self.controller_button_combo = ttk.Combobox(
            form,
            textvariable=self.acao_var,
            values=self._botoes_do_padrao_atual(),
            state="readonly",
        )
        self.controller_button_combo.grid(
            row=1,
            column=3,
            sticky="ew",
            padx=(10, 0),
            pady=(4, 0),
        )

        add_row = ttk.Frame(panel, style="Panel.TFrame")
        add_row.grid(row=3, column=0, sticky="nsew")
        add_row.columnconfigure(0, weight=1)
        add_row.rowconfigure(0, weight=1)

        columns = ("nome", "entrada", "acao")
        self.buttons_table = ttk.Treeview(
            add_row,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.buttons_table.heading("nome", text="Nome")
        self.buttons_table.heading("entrada", text="Entrada")
        self.buttons_table.heading("acao", text="Botao do controle")
        self.buttons_table.column("nome", width=210, minwidth=140)
        self.buttons_table.column("entrada", width=150, minwidth=100)
        self.buttons_table.column("acao", width=260, minwidth=140)
        self.buttons_table.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(add_row, orient=tk.VERTICAL, command=self.buttons_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.buttons_table.configure(yscrollcommand=scrollbar.set)
        self.buttons_table.bind("<<TreeviewSelect>>", self._selecionar_botao_evento)

        bottom = ttk.Frame(panel, style="Panel.TFrame")
        bottom.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        bottom.columnconfigure(3, weight=1)

        ttk.Button(bottom, text="Editar", command=self._adicionar_botao).grid(
            row=0,
            column=0,
            padx=(0, 8),
        )
        ttk.Button(bottom, text="Atualizar", command=self._atualizar_botao).grid(
            row=0,
            column=1,
            padx=(0, 8),
        )
        ttk.Button(bottom, text="Remover", command=self._remover_botao).grid(
            row=0,
            column=2,
            padx=(0, 8),
        )
        ttk.Button(bottom, text="Resetar padrao", command=self._resetar_padrao).grid(
            row=0,
            column=3,
            padx=(0, 8),
        )
        ttk.Button(bottom, text="Salvar", command=self._salvar_configuracoes).grid(
            row=0,
            column=4,
            sticky="e",
        )

    def _carregar_configuracoes(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = load_config(CONFIG_PATH)
        self.configuracoes = data.get("configuracoes", {})
        self.execucao_config = data.get("execucao", {})

        if not self.configuracoes:
            self.configuracoes = self._criar_configuracoes_padrao()

        self._aplicar_execucao_config()
        self._normalizar_configuracoes()
        self._atualizar_lista_configuracoes()
        primeiro_nome = next(iter(self.configuracoes))
        self._selecionar_configuracao(primeiro_nome)
        self._garantir_perfis_runtime_validos()
        self._atualizar_combos_perfis_runtime()
        self._atualizar_status_slots()

    def _carregar_dispositivos(self):
        try:
            self.device_manager = DeviceManager()
            monitor = RawInputMonitor(self.device_manager, log_to_console=False)
            monitor.listar_dispositivos()
        except Exception as erro:
            self.status_var.set(f"Erro ao listar dispositivos: {erro}")

        self._atualizar_combos_dispositivos()

    def _atualizar_combos_dispositivos(self):
        self.dispositivos_por_label = {}
        teclado_id = ""
        mouse_id = ""

        if self.configuracao_atual is not None:
            dispositivos = self._dispositivos_da_configuracao()
            teclado_id = dispositivos.get("teclado", "")
            mouse_id = dispositivos.get("mouse", "")

        teclado_opcoes = self._opcoes_dispositivo("TECLADO", teclado_id)
        mouse_opcoes = self._opcoes_dispositivo("MOUSE", mouse_id)

        self.keyboard_combo.configure(values=[label for label, _device_id in teclado_opcoes])
        self.mouse_combo.configure(values=[label for label, _device_id in mouse_opcoes])

        self.teclado_var.set(self._label_por_id(teclado_opcoes, teclado_id))
        self.mouse_var.set(self._label_por_id(mouse_opcoes, mouse_id))
        self._atualizar_resumo_dispositivos_perfil()

    def _opcoes_dispositivo(self, tipo, selecionado_id=""):
        label_padrao = "Qualquer teclado" if tipo == "TECLADO" else "Qualquer mouse"
        opcoes = [(label_padrao, "")]

        for dispositivo in self.device_manager.listar():
            if dispositivo.get("tipo") != tipo:
                continue

            label = (
                f"{dispositivo.get('nome', tipo.title())} "
                f"({tipo.title()} {dispositivo.get('numero', '?')} | "
                f"ID {dispositivo.get('id', '')})"
            )
            opcoes.append((label, dispositivo.get("id", "")))

        ids = {device_id for _label, device_id in opcoes}
        if selecionado_id and selecionado_id not in ids:
            opcoes.append((f"Dispositivo salvo nao encontrado ({selecionado_id})", selecionado_id))

        for label, device_id in opcoes:
            self.dispositivos_por_label[label] = device_id

        return opcoes

    def _label_por_id(self, opcoes, device_id):
        for label, option_id in opcoes:
            if option_id == device_id:
                return label

        return opcoes[0][0]

    def _criar_configuracoes_padrao(self):
        return {
            "Padrao": {
                "padrao": "Xbox",
                "dispositivos": {
                    "teclado": "",
                    "mouse": "",
                },
                "botoes": criar_botoes_padrao("Xbox"),
            },
        }

    def _normalizar_configuracoes(self):
        for configuracao in self.configuracoes.values():
            dispositivos = configuracao.setdefault("dispositivos", {})
            dispositivos.setdefault("teclado", "")
            dispositivos.setdefault("mouse", "")

            if "padrao" not in configuracao:
                configuracao["padrao"] = "Xbox"
                configuracao["botoes"] = criar_botoes_padrao("Xbox")
            elif not configuracao.get("botoes"):
                configuracao["botoes"] = criar_botoes_padrao(configuracao["padrao"])

    def _criar_botoes_padrao(self, padrao):
        return criar_botoes_padrao(padrao)

    def _botoes_do_padrao_atual(self):
        return botoes_do_padrao(self.padrao_var.get())

    def _atualizar_botoes_do_padrao(self):
        botoes = self._botoes_do_padrao_atual()
        self.controller_button_combo.configure(values=botoes)

        if self.acao_var.get() not in botoes:
            self.acao_var.set(botoes[0] if botoes else "")

    def _alterar_padrao(self, _event=None):
        if self.configuracao_atual is not None:
            padrao = self.padrao_var.get() or "Xbox"
            self.configuracoes[self.configuracao_atual]["padrao"] = padrao
            self.configuracoes[self.configuracao_atual]["botoes"] = self._criar_botoes_padrao(padrao)
            self._limpar_formulario_botao()
            self._atualizar_tabela_botoes()

        self._atualizar_botoes_do_padrao()

    def _resetar_padrao(self):
        if self.configuracao_atual is None:
            return

        padrao = self.padrao_var.get() or "Xbox"
        self.configuracoes[self.configuracao_atual]["padrao"] = padrao
        self.configuracoes[self.configuracao_atual]["botoes"] = self._criar_botoes_padrao(padrao)
        self._limpar_formulario_botao()
        self._atualizar_botoes_do_padrao()
        self._atualizar_tabela_botoes()

    def _salvar_configuracoes(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._alterar_dispositivo_perfil()
        save_config(CONFIG_PATH, self.configuracoes, self._execucao_para_json())

        messagebox.showinfo(APP_NAME, "Configurações salvas.")

    def _aplicar_execucao_config(self):
        controles = list(self.execucao_config.get("controles") or [])
        self.runtime_profile_vars = []
        self.runtime_slot_status_vars = []

        for nome in controles[:MAX_RUNTIME_CONTROLLERS]:
            if nome:
                self.runtime_profile_vars.append(tk.StringVar(value=nome))
                self.runtime_slot_status_vars.append(tk.StringVar(value="Desativado"))

        if not self.runtime_profile_vars:
            self.runtime_profile_vars.append(tk.StringVar(value=DISABLED_PROFILE_LABEL))
            self.runtime_slot_status_vars.append(tk.StringVar(value="Desativado"))

        self.stick_intensity_var.set(int(self.execucao_config.get("stick_intensity", 100)))
        self.mouse_pulse_ms_var.set(int(self.execucao_config.get("mouse_pulse_ms", 60)))
        self.mouse_deadzone_var.set(int(self.execucao_config.get("mouse_deadzone", 0)))
        self.desativar_atalho_var.set(
            normalizar_rotulo_entrada(self.execucao_config.get("desativar_atalho", ""))
        )
        self._renderizar_controles_runtime()

    def _execucao_para_json(self):
        controles = [
            "" if var.get() == DISABLED_PROFILE_LABEL else var.get()
            for var in self.runtime_profile_vars
        ]

        return {
            "controles": controles,
            "stick_intensity": self._valor_int_var(self.stick_intensity_var, 100),
            "mouse_pulse_ms": self._valor_int_var(self.mouse_pulse_ms_var, 60),
            "mouse_deadzone": self._valor_int_var(self.mouse_deadzone_var, 0),
            "desativar_atalho": normalizar_rotulo_entrada(self.desativar_atalho_var.get()),
        }

    def _valor_int_var(self, variable, default):
        try:
            return int(variable.get())
        except (tk.TclError, ValueError):
            return default

    def _atualizar_lista_configuracoes(self):
        self.config_list.delete(0, tk.END)

        for nome in self.configuracoes:
            self.config_list.insert(tk.END, nome)

    def _atualizar_combos_perfis_runtime(self):
        opcoes = [DISABLED_PROFILE_LABEL, *self.configuracoes.keys()]

        for combo in self.runtime_profile_combos:
            combo.configure(values=opcoes)

        self._atualizar_status_slots()

    def _adicionar_controle_runtime(self, nome=DISABLED_PROFILE_LABEL):
        if len(self.runtime_profile_vars) >= MAX_RUNTIME_CONTROLLERS:
            messagebox.showwarning(APP_NAME, "Limite de 6 controles atingido.")
            return

        self.runtime_profile_vars.append(tk.StringVar(value=nome or DISABLED_PROFILE_LABEL))
        self.runtime_slot_status_vars.append(tk.StringVar(value="Desativado"))
        self._renderizar_controles_runtime()

    def _remover_controle_runtime(self, index):
        if self.rodando:
            messagebox.showwarning(APP_NAME, "Pare a execucao antes de remover controles.")
            return

        if index < 0 or index >= len(self.runtime_profile_vars):
            return

        del self.runtime_profile_vars[index]
        del self.runtime_slot_status_vars[index]
        self._renderizar_controles_runtime()

    def _renderizar_controles_runtime(self):
        for child in self.runtime_profiles_frame.winfo_children():
            child.destroy()

        self.runtime_profile_combos = []
        opcoes = [DISABLED_PROFILE_LABEL, *self.configuracoes.keys()]

        for index, profile_var in enumerate(self.runtime_profile_vars, start=1):
            row = ttk.Frame(self.runtime_profiles_frame, style="Panel.TFrame")
            row.grid(row=index - 1, column=0, sticky="ew", pady=(0, 6))
            row.columnconfigure(1, weight=1)

            ttk.Label(row, text=f"Controle {index}", style="Muted.TLabel").grid(
                row=0,
                column=0,
                sticky="w",
                padx=(0, 8),
            )

            combo = ttk.Combobox(
                row,
                textvariable=profile_var,
                values=opcoes,
                state="readonly",
                width=16,
            )
            combo.grid(row=0, column=1, sticky="ew")
            combo.bind("<<ComboboxSelected>>", lambda _event: self._atualizar_status_slots())
            self.runtime_profile_combos.append(combo)

            ttk.Button(
                row,
                text="Remover",
                command=lambda remove_index=index - 1: self._remover_controle_runtime(remove_index),
            ).grid(row=0, column=2, sticky="e", padx=(6, 0))

            ttk.Label(
                row,
                textvariable=self.runtime_slot_status_vars[index - 1],
                style="Muted.TLabel",
                width=24,
            ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 0))

        self._atualizar_estado_botao_adicionar_controle()
        self._atualizar_status_slots()

    def _atualizar_estado_botao_adicionar_controle(self):
        if len(self.runtime_profile_vars) >= MAX_RUNTIME_CONTROLLERS:
            self.add_runtime_control_button.state(["disabled"])
        else:
            self.add_runtime_control_button.state(["!disabled"])

    def _garantir_perfis_runtime_validos(self):
        nomes = list(self.configuracoes)

        if not self.runtime_profile_vars:
            self.runtime_profile_vars.append(tk.StringVar(value=DISABLED_PROFILE_LABEL))
            self.runtime_slot_status_vars.append(tk.StringVar(value="Desativado"))

        for profile_var in self.runtime_profile_vars:
            if profile_var.get() not in nomes:
                profile_var.set(DISABLED_PROFILE_LABEL)

        if nomes and all(var.get() == DISABLED_PROFILE_LABEL for var in self.runtime_profile_vars):
            self.runtime_profile_vars[0].set(nomes[0])

        self._renderizar_controles_runtime()
        self._atualizar_status_slots()

    def _perfis_runtime_ativos(self):
        perfis = []

        for index, profile_var in enumerate(self.runtime_profile_vars, start=1):
            nome = profile_var.get()

            if nome == DISABLED_PROFILE_LABEL or nome not in self.configuracoes:
                continue

            perfis.append(
                {
                    "slot": f"Controle {index}",
                    "nome": nome,
                    "configuracao": self.configuracoes[nome],
                }
            )

        return perfis

    def _validar_perfis_runtime_ativos(self):
        perfis = self._perfis_runtime_ativos()

        if not perfis:
            messagebox.showwarning(APP_NAME, "Selecione pelo menos um perfil para execucao.")
            return []

        nomes = [perfil["nome"] for perfil in perfis]
        if len(nomes) != len(set(nomes)):
            messagebox.showwarning(APP_NAME, "Use perfis diferentes para cada controle ativo.")
            return []

        conflitos = self._conflitos_dispositivos_runtime(perfis)
        if conflitos:
            mensagem = "Conflito de dispositivo entre perfis ativos:\n\n"
            mensagem += "\n".join(conflitos)
            mensagem += "\n\nContinuar mesmo assim?"

            if not messagebox.askyesno(APP_NAME, mensagem):
                return []

        return perfis

    def _conflitos_dispositivos_runtime(self, perfis):
        conflitos = []

        for chave in ("teclado", "mouse"):
            qualquer = []
            especificos = {}

            for perfil in perfis:
                dispositivos = perfil["configuracao"].get("dispositivos") or {}
                device_id = dispositivos.get(chave, "")

                if device_id:
                    especificos.setdefault(device_id, []).append(perfil)
                else:
                    qualquer.append(perfil)

            if len(qualquer) > 1:
                conflitos.append(
                    f"{chave}: qualquer dispositivo em {self._resumo_slots(qualquer)}"
                )

            if qualquer and especificos:
                conflitos.append(
                    f"{chave}: qualquer dispositivo pode conflitar com perfis especificos"
                )

            for device_id, perfis_dispositivo in especificos.items():
                if len(perfis_dispositivo) < 2:
                    continue

                conflitos.append(
                    f"{chave}: {device_id} em {self._resumo_slots(perfis_dispositivo)}"
                )

        return conflitos

    def _resumo_slots(self, perfis):
        return ", ".join(
            f"{perfil['slot']} ({perfil['nome']})"
            for perfil in perfis
        )

    def _atualizar_status_slots(self):
        ativos = {
            perfil["slot"]: perfil["nome"]
            for perfil in self.runtime_profiles
        }

        for index, status_var in enumerate(self.runtime_slot_status_vars, start=1):
            slot = f"Controle {index}"
            nome = self.runtime_profile_vars[index - 1].get()

            if self.rodando and slot in ativos:
                total = self.runtime_action_counts_by_slot.get(slot, 0)
                status_var.set(f"Rodando | {total} acoes")
            elif nome != DISABLED_PROFILE_LABEL:
                status_var.set(f"Pronto: {nome}")
            else:
                status_var.set("Desativado")

    def _selecionar_configuracao_evento(self, _event):
        selected = self.config_list.curselection()

        if not selected:
            return

        nome = self.config_list.get(selected[0])
        if nome == self.configuracao_atual:
            return

        self._sincronizar_configuracao_atual()
        self._selecionar_configuracao(nome)

    def _sincronizar_configuracao_atual(self):
        self._alterar_dispositivo_perfil()

    def _dispositivos_da_configuracao(self):
        configuracao = self.configuracoes[self.configuracao_atual]
        dispositivos = configuracao.setdefault("dispositivos", {})
        dispositivos.setdefault("teclado", "")
        dispositivos.setdefault("mouse", "")
        return dispositivos

    def _alterar_dispositivo_perfil(self, _event=None):
        if self.configuracao_atual is None:
            return

        dispositivos = self._dispositivos_da_configuracao()
        dispositivos["teclado"] = self.dispositivos_por_label.get(self.teclado_var.get(), "")
        dispositivos["mouse"] = self.dispositivos_por_label.get(self.mouse_var.get(), "")
        self._atualizar_resumo_dispositivos_perfil()

    def _atualizar_resumo_dispositivos_perfil(self):
        if self.configuracao_atual is None:
            self.dispositivos_perfil_var.set("")
            return

        self.dispositivos_perfil_var.set(
            f"Selecionado: {self.teclado_var.get()} / {self.mouse_var.get()}"
        )

    def _selecionar_configuracao(self, nome):
        self.configuracao_atual = nome
        self.nome_config_var.set(nome)
        configuracao = self.configuracoes[nome]
        self.padrao_var.set(configuracao.get("padrao", "Xbox"))
        self._atualizar_botoes_do_padrao()
        self._atualizar_combos_dispositivos()
        self._limpar_formulario_botao()

        nomes = list(self.configuracoes)
        index = nomes.index(nome)
        self.config_list.selection_clear(0, tk.END)
        self.config_list.selection_set(index)
        self.config_list.activate(index)

        self.buttons_table.selection_remove(*self.buttons_table.selection())
        self._atualizar_tabela_botoes()

    def _criar_configuracao(self):
        nome = self.nome_config_var.get().strip()

        if not nome:
            messagebox.showwarning(APP_NAME, "Informe um nome para a configuração.")
            return

        if nome in self.configuracoes:
            messagebox.showwarning(APP_NAME, "Já existe uma configuração com esse nome.")
            return

        padrao = self.padrao_var.get() or "Xbox"
        self.configuracoes[nome] = {
            "padrao": padrao,
            "dispositivos": {
                "teclado": self.dispositivos_por_label.get(self.teclado_var.get(), ""),
                "mouse": self.dispositivos_por_label.get(self.mouse_var.get(), ""),
            },
            "botoes": self._criar_botoes_padrao(padrao),
        }
        self._atualizar_lista_configuracoes()
        self._garantir_perfis_runtime_validos()
        self._atualizar_combos_perfis_runtime()
        self._selecionar_configuracao(nome)

    def _renomear_configuracao(self):
        if self.configuracao_atual is None:
            return

        novo_nome = self.nome_config_var.get().strip()

        if not novo_nome:
            messagebox.showwarning(APP_NAME, "Informe um novo nome.")
            return

        if novo_nome != self.configuracao_atual and novo_nome in self.configuracoes:
            messagebox.showwarning(APP_NAME, "Já existe uma configuração com esse nome.")
            return

        nome_anterior = self.configuracao_atual
        self.configuracoes[novo_nome] = self.configuracoes.pop(nome_anterior)

        for profile_var in self.runtime_profile_vars:
            if profile_var.get() == nome_anterior:
                profile_var.set(novo_nome)

        self._atualizar_lista_configuracoes()
        self._garantir_perfis_runtime_validos()
        self._atualizar_combos_perfis_runtime()
        self._selecionar_configuracao(novo_nome)

    def _excluir_configuracao(self):
        if self.configuracao_atual is None:
            return

        if len(self.configuracoes) == 1:
            messagebox.showwarning(APP_NAME, "Mantenha pelo menos uma configuração.")
            return

        resposta = messagebox.askyesno(
            APP_NAME,
            f"Excluir a configuração '{self.configuracao_atual}'?",
        )

        if not resposta:
            return

        del self.configuracoes[self.configuracao_atual]
        self._atualizar_lista_configuracoes()
        self._garantir_perfis_runtime_validos()
        self._atualizar_combos_perfis_runtime()
        self._selecionar_configuracao(next(iter(self.configuracoes)))

    def _exportar_configuracao(self):
        if self.configuracao_atual is None:
            return

        path = filedialog.asksaveasfilename(
            title="Exportar perfil",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=f"{self.configuracao_atual}.json",
        )

        if not path:
            return

        data = {
            "nome": self.configuracao_atual,
            "configuracao": self.configuracoes[self.configuracao_atual],
        }

        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        self.status_var.set(f"Perfil exportado: {self.configuracao_atual}")

    def _importar_configuracao(self):
        path = filedialog.askopenfilename(
            title="Importar perfil",
            filetypes=[("JSON", "*.json")],
        )

        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as erro:
            messagebox.showerror(APP_NAME, f"Nao foi possivel importar o perfil: {erro}")
            return

        nome = data.get("nome") or Path(path).stem
        configuracao = data.get("configuracao")

        if not isinstance(configuracao, dict):
            messagebox.showerror(APP_NAME, "Arquivo de perfil invalido.")
            return

        nome = self._nome_configuracao_disponivel(str(nome).strip() or "Perfil importado")
        self.configuracoes[nome] = configuracao
        self._normalizar_configuracoes()
        self._atualizar_lista_configuracoes()
        self._garantir_perfis_runtime_validos()
        self._atualizar_combos_perfis_runtime()
        self._selecionar_configuracao(nome)
        self.status_var.set(f"Perfil importado: {nome}")

    def _nome_configuracao_disponivel(self, nome_base):
        if nome_base not in self.configuracoes:
            return nome_base

        index = 2

        while f"{nome_base} {index}" in self.configuracoes:
            index += 1

        return f"{nome_base} {index}"

    def _atualizar_tabela_botoes(self):
        self.buttons_table.delete(*self.buttons_table.get_children())

        if self.configuracao_atual is None:
            return

        for index, botao in enumerate(self._botoes_atuais()):
            self.buttons_table.insert(
                "",
                tk.END,
                iid=str(index),
                values=(
                    botao.get("nome", ""),
                    self._entrada_para_exibicao(botao),
                    botao.get("acao", ""),
                ),
            )

    def _selecionar_botao_evento(self, _event):
        index = self._indice_botao_selecionado()

        if index is None:
            return

        botao = self._botoes_atuais()[index]
        self.nome_botao_var.set(botao.get("nome", ""))
        self.entrada_var.set(self._entrada_para_exibicao(botao))
        self.acao_var.set(botao.get("acao", ""))

    def _adicionar_botao(self):
        if self.configuracao_atual is None:
            return

        if not self._formulario_botao_pronto_para_captura():
            return

        self._abrir_modal_captura_entrada(self._adicionar_botao_com_entrada_capturada)

    def _adicionar_botao_com_entrada_capturada(self, entrada):
        self.entrada_var.set(entrada)
        botao = self._ler_formulario_botao()

        if botao is None:
            return

        self._botoes_atuais().append(botao)
        self._limpar_formulario_botao()
        self._atualizar_tabela_botoes()

    def _atualizar_botao(self):
        index = self._indice_botao_selecionado()

        if index is None:
            messagebox.showwarning(APP_NAME, "Selecione um botão para atualizar.")
            return

        if not self._formulario_botao_pronto_para_captura():
            return

        self._abrir_modal_captura_entrada(
            lambda entrada: self._atualizar_botao_com_entrada_capturada(index, entrada)
        )

    def _atualizar_botao_com_entrada_capturada(self, index, entrada):
        self.entrada_var.set(entrada)
        botao = self._ler_formulario_botao()

        if botao is None:
            return

        self._botoes_atuais()[index] = botao
        self._atualizar_tabela_botoes()
        self.buttons_table.selection_set(str(index))

    def _capturar_entrada_para_formulario(self):
        self._abrir_modal_captura_entrada(self.entrada_var.set)

    def _formulario_botao_pronto_para_captura(self):
        nome = self.nome_botao_var.get().strip()
        acao = self.acao_var.get().strip()

        if not nome or not acao:
            messagebox.showwarning(
                APP_NAME,
                "Informe o nome e o botao do controle antes de capturar a tecla.",
            )
            return False

        return True

    def _capturar_atalho_desativar(self):
        self._abrir_modal_captura_entrada(
            self._definir_atalho_desativar,
            modo_inicial="teclado",
            mostrar_modos=False,
            vincular_dispositivo=False,
            texto="aperte a tecla que vai desativar o programa",
        )

    def _definir_atalho_desativar(self, entrada):
        self.desativar_atalho_var.set(normalizar_rotulo_entrada(entrada))
        self._reiniciar_atalho_execucao()

    def _limpar_atalho_desativar(self):
        self.desativar_atalho_var.set("")
        self._parar_atalho_execucao()

    def _abrir_modal_captura_entrada(
        self,
        callback,
        modo_inicial="teclado",
        mostrar_modos=True,
        vincular_dispositivo=True,
        texto="aperte uma tecla ou botao do mouse",
    ):
        modal = tk.Toplevel(self)
        modal.title("Capturar entrada")
        modal.geometry("460x230")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()

        captura_queue = queue.Queue()
        capture_device_manager = DeviceManager()
        monitor = RawInputMonitor(
            capture_device_manager,
            event_callback=captura_queue.put,
            log_to_console=False,
        )
        status_var = tk.StringVar(value="Aguardando entrada Raw Input...")
        device_var = tk.StringVar(value="")
        capture_mode_var = tk.StringVar(value=modo_inicial)

        container = ttk.Frame(modal, padding=18)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)

        ttk.Label(
            container,
            text=texto,
            style="Subheader.TLabel",
            anchor=tk.CENTER,
        ).grid(row=0, column=0, sticky="ew", pady=(8, 8))

        if mostrar_modos:
            mode_row = ttk.Frame(container)
            mode_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))

            for column, (label, value) in enumerate(
                (
                    ("Teclado", "teclado"),
                    ("Botao mouse", "botao_mouse"),
                    ("Movimento", "movimento_mouse"),
                    ("Qualquer", "qualquer"),
                )
            ):
                mode_row.columnconfigure(column, weight=1)
                ttk.Radiobutton(
                    mode_row,
                    text=label,
                    value=value,
                    variable=capture_mode_var,
                ).grid(row=0, column=column, sticky="w")

        ttk.Label(
            container,
            textvariable=status_var,
            style="Muted.TLabel",
            anchor=tk.CENTER,
            wraplength=360,
        ).grid(row=2, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(
            container,
            textvariable=device_var,
            style="Muted.TLabel",
            anchor=tk.CENTER,
            wraplength=360,
        ).grid(row=3, column=0, sticky="ew", pady=(0, 12))

        ttk.Button(container, text="Cancelar", command=lambda: fechar_modal()).grid(
            row=4,
            column=0,
            sticky="ew",
        )

        def rodar_monitor_captura():
            try:
                monitor.listar_dispositivos()
                monitor.iniciar()
            except Exception as erro:
                captura_queue.put(
                    {
                        "tipo": "ERRO_CAPTURA",
                        "mensagem": str(erro),
                    }
                )

        def processar_fila_captura():
            while not captura_queue.empty():
                evento = captura_queue.get()

                if evento.get("tipo") == "ERRO_CAPTURA":
                    status_var.set(f"Erro na captura: {evento.get('mensagem')}")
                    return

                if evento.get("tipo") in {"TECLADO", "MOUSE"}:
                    device_var.set(
                        f"Dispositivo: {evento.get('dispositivo', '')} "
                        f"({evento.get('id', '')})"
                    )

                captura = captura_por_evento(evento, capture_mode_var.get())

                if captura is None:
                    continue

                monitor.parar()
                if vincular_dispositivo:
                    self._vincular_dispositivo_capturado(captura)
                callback(captura["entrada"])
                modal.destroy()
                return

            if modal.winfo_exists():
                modal.after(50, processar_fila_captura)

        def fechar_modal():
            monitor.parar()
            modal.destroy()

        threading.Thread(target=rodar_monitor_captura, daemon=True).start()
        modal.protocol("WM_DELETE_WINDOW", fechar_modal)
        modal.after(50, processar_fila_captura)
        modal.after(100, modal.focus_force)

    def _vincular_dispositivo_capturado(self, captura):
        if self.configuracao_atual is None:
            return

        chave = chave_dispositivo_por_tipo(captura.get("tipo", ""))
        dispositivo_id = captura.get("dispositivo_id", "")

        if not chave or not dispositivo_id:
            return

        dispositivos = self._dispositivos_da_configuracao()
        dispositivos[chave] = dispositivo_id
        self._carregar_dispositivos()
        self.status_var.set(
            f"Capturado: {captura.get('entrada')} | "
            f"{chave} vinculado ao perfil"
        )

    def _entrada_por_evento_tk(self, event):
        mouse_buttons = {
            1: "MOUSE_LEFT",
            2: "MOUSE_MIDDLE",
            3: "MOUSE_RIGHT",
            4: "MOUSE_WHEEL_UP",
            5: "MOUSE_WHEEL_DOWN",
        }

        if getattr(event, "num", None) in mouse_buttons:
            return mouse_buttons[event.num]

        keysym = getattr(event, "keysym", "")
        aliases = {
            "space": "SPACE",
            "Return": "ENTER",
            "Escape": "ESC",
            "Tab": "TAB",
            "BackSpace": "BACKSPACE",
            "Delete": "DELETE",
            "Up": "UP",
            "Down": "DOWN",
            "Left": "LEFT",
            "Right": "RIGHT",
            "Shift_L": "SHIFT",
            "Shift_R": "SHIFT",
            "Control_L": "CTRL",
            "Control_R": "CTRL",
            "Alt_L": "ALT",
            "Alt_R": "ALT",
        }

        if keysym in aliases:
            return aliases[keysym]

        char = getattr(event, "char", "")

        if char and char.isprintable() and not char.isspace():
            return char.upper()

        return keysym.upper() if keysym else ""

    def _remover_botao(self):
        index = self._indice_botao_selecionado()

        if index is None:
            messagebox.showwarning(APP_NAME, "Selecione um botão para remover.")
            return

        del self._botoes_atuais()[index]
        self._limpar_formulario_botao()
        self._atualizar_tabela_botoes()

    def _ler_formulario_botao(self):
        nome = self.nome_botao_var.get().strip()
        entradas = self._entradas_do_formulario()
        acao = self.acao_var.get().strip()

        if not nome or not entradas:
            messagebox.showwarning(
                APP_NAME,
                "Informe pelo menos o nome do botão e a entrada.",
            )
            return None

        botao = {
            "nome": nome,
            "acao": acao,
        }

        if len(entradas) == 1:
            botao["entrada"] = entradas[0]
        else:
            botao["entrada"] = entradas[0]
            botao["entradas"] = entradas

        return botao

    def _entradas_do_formulario(self):
        texto = self.entrada_var.get().strip().upper()

        for separador in (",", ";"):
            texto = texto.replace(separador, "|")

        return [
            entrada.strip()
            for entrada in texto.split("|")
            if entrada.strip()
        ]

    def _entrada_para_exibicao(self, botao):
        entradas = botao.get("entradas")

        if entradas:
            return ", ".join(entradas)

        return botao.get("entrada", "")

    def _limpar_formulario_botao(self):
        self.nome_botao_var.set("")
        self.entrada_var.set("")
        self.acao_var.set("")

    def _botoes_atuais(self):
        configuracao = self.configuracoes[self.configuracao_atual]
        return configuracao.setdefault("botoes", [])

    def _indice_botao_selecionado(self):
        selected = self.buttons_table.selection()

        if not selected:
            return None

        return int(selected[0])

    def _start(self):
        if self.rodando:
            return

        self._sincronizar_configuracao_atual()
        if not self._validar_atalho_desativar_para_start():
            return

        perfis = self._validar_perfis_runtime_ativos()

        if not perfis:
            return

        self.runtime_queue = queue.Queue()
        self.runtime_activity_log.clear()
        self.runtime_device_manager = DeviceManager()
        self.runtime_session_id += 1
        session_id = self.runtime_session_id

        try:
            backends = {}

            for perfil in perfis:
                backends[perfil["slot"]] = self._criar_backend_gamepad()

            self.gamepad_backends = backends
            self._iniciar_bloqueador_input(perfis, session_id)
        except GamepadBackendError as erro:
            for backend in backends.values():
                try:
                    backend.close()
                except Exception:
                    pass

            self._fechar_gamepad_backends()
            self.status_var.set(f"Erro no gamepad: {erro}")
            self._registrar_atividade_runtime(activity_message("ERRO", str(erro)))
            messagebox.showerror(APP_NAME, str(erro))
            return
        except Exception as erro:
            for backend in backends.values():
                try:
                    backend.close()
                except Exception:
                    pass

            self._parar_bloqueador_input()
            self._fechar_gamepad_backends()
            self.status_var.set(f"Erro ao bloquear entradas: {erro}")
            self._registrar_atividade_runtime(activity_message("ERRO", str(erro)))
            messagebox.showerror(
                APP_NAME,
                "Nao foi possivel bloquear as entradas fisicas mapeadas.\n\n"
                f"{erro}",
            )
            return

        self._sincronizar_janela_execucao()
        self.runtime_profiles = perfis
        self.runtime_action_counts_by_slot = {
            perfil["slot"]: 0
            for perfil in perfis
        }
        self._sincronizar_janela_execucao()
        self.runtime_monitor = RawInputMonitor(
            self.runtime_device_manager,
            event_callback=lambda evento: self._receber_evento_runtime(session_id, evento),
            log_to_console=False,
        )
        self.runtime_action_count = 0
        self.rodando = True
        self._atualizar_estado_execucao()
        self._atualizar_status_slots()
        self._registrar_atividade_runtime(
            activity_message("INFO", f"Runtime iniciado: {self._descricao_perfis_runtime()}")
        )
        self.runtime_thread = threading.Thread(
            target=self._rodar_runtime_monitor,
            args=(session_id, self.runtime_monitor),
            daemon=True,
        )
        self.runtime_thread.start()
        self.after(80, self._processar_fila_runtime)

    def _parar(self):
        if not self.rodando and self.runtime_monitor is None and self.input_blocker is None:
            return

        if self.runtime_monitor is not None:
            self.runtime_monitor.parar()
            self.runtime_monitor = None

        self._parar_bloqueador_input()
        self._fechar_gamepad_backends()
        self.runtime_profiles = []
        self.runtime_action_counts_by_slot = {}
        self.rodando = False
        self._atualizar_estado_execucao()
        self._atualizar_status_slots()
        self._sincronizar_janela_execucao()
        self._registrar_atividade_runtime(activity_message("INFO", "Runtime parado"))

    def _alternar_execucao(self):
        if self.rodando:
            self._parar()
        else:
            self._start()

    def _reiniciar_atalho_execucao(self):
        self._parar_atalho_execucao()

        atalho = normalizar_rotulo_entrada(self.desativar_atalho_var.get())
        vks = vks_por_entrada(atalho)

        if not vks:
            return

        spec = InputBlockSpec(
            keyboard_vks=frozenset(vks),
            mouse_buttons=frozenset(),
        )
        self.toggle_hotkey_blocker = PhysicalInputBlocker(
            spec,
            allow_current_process=False,
            keyboard_event_callback=self._receber_evento_atalho_execucao,
        )

        try:
            self.toggle_hotkey_blocker.start()
        except Exception as erro:
            self.toggle_hotkey_blocker = None
            self.status_var.set(f"Erro no atalho de execucao: {erro}")

    def _parar_atalho_execucao(self):
        if self.toggle_hotkey_blocker is None:
            return

        try:
            self.toggle_hotkey_blocker.stop()
        finally:
            self.toggle_hotkey_blocker = None

    def _receber_evento_atalho_execucao(self, evento):
        self.toggle_hotkey_queue.put(dict(evento))

    def _processar_fila_atalho_execucao(self):
        while not self.toggle_hotkey_queue.empty():
            evento = self.toggle_hotkey_queue.get()

            if (
                self._evento_e_atalho_desativar(evento)
                and time.monotonic() - self.toggle_hotkey_last_at >= 0.35
            ):
                self.toggle_hotkey_last_at = time.monotonic()
                self._registrar_atividade_runtime(
                    activity_message(
                        "INFO",
                        f"Atalho de execucao acionado: {self.desativar_atalho_var.get()}",
                    )
                )
                self._alternar_execucao()

        if self.winfo_exists():
            self.after(80, self._processar_fila_atalho_execucao)

    def _fechar_app(self):
        self._parar()
        self._parar_atalho_execucao()
        self.destroy()

    def _rodar_runtime_monitor(self, session_id, monitor):
        try:
            monitor.listar_dispositivos()
            monitor.iniciar()
        except Exception as erro:
            self.runtime_queue.put(
                {
                    "tipo": "ERRO_RUNTIME",
                    "_runtime_session": session_id,
                    "mensagem": str(erro),
                }
            )
        finally:
            self.runtime_queue.put(
                {
                    "tipo": "RUNTIME_FINALIZADO",
                    "_runtime_session": session_id,
                }
            )

    def _receber_evento_runtime(self, session_id, evento):
        evento = dict(evento)
        evento["_runtime_session"] = session_id
        self.runtime_queue.put(evento)

    def _processar_fila_runtime(self):
        while not self.runtime_queue.empty():
            evento = self.runtime_queue.get()

            if evento.get("_runtime_session") != self.runtime_session_id:
                continue

            if evento.get("tipo") == "ERRO_RUNTIME":
                self.rodando = False
                self.runtime_monitor = None
                self._parar_bloqueador_input()
                self._fechar_gamepad_backends()
                self.runtime_profiles = []
                self.runtime_action_counts_by_slot = {}
                self.status_var.set(f"Erro no runtime: {evento.get('mensagem')}")
                self._atualizar_status_slots()
                self._registrar_atividade_runtime(
                    activity_message("ERRO", evento.get("mensagem", ""))
                )
                self._atualizar_estado_execucao()
                continue

            if evento.get("tipo") == "RUNTIME_FINALIZADO":
                if self.rodando:
                    self.rodando = False
                    self.runtime_monitor = None
                    self._parar_bloqueador_input()
                    self._fechar_gamepad_backends()
                    self.runtime_profiles = []
                    self.runtime_action_counts_by_slot = {}
                    self._atualizar_estado_execucao()
                    self._atualizar_status_slots()
                    self._registrar_atividade_runtime(
                        activity_message("INFO", "Runtime finalizado")
                    )
                continue

            self._processar_evento_runtime(evento)

        self._atualizar_gamepad_temporarios()

        if self.rodando and self.winfo_exists():
            self.after(80, self._processar_fila_runtime)

    def _processar_evento_runtime(self, evento):
        if not self.runtime_profiles:
            return

        if self._evento_e_atalho_desativar(evento):
            self._registrar_atividade_runtime(
                activity_message(
                    "INFO",
                    f"Atalho de parada acionado: {self.desativar_atalho_var.get()}",
                )
            )
            self._parar()
            return

        for perfil in self.runtime_profiles:
            nome_configuracao = perfil["nome"]
            configuracao = self.configuracoes.get(nome_configuracao)

            if configuracao is None:
                continue

            acoes = mapear_evento_para_acoes(
                configuracao,
                evento,
                nome_configuracao,
                mouse_deadzone=self._valor_int_var(self.mouse_deadzone_var, 0),
            )

            if not acoes:
                continue

            backend = self.gamepad_backends.get(perfil["slot"])

            if backend is None:
                continue

            for acao in acoes:
                acao["slot"] = perfil["slot"]

                try:
                    aplicada = backend.aplicar_acao(acao)
                except Exception as erro:
                    erro_texto = f"Erro no gamepad: {erro}"
                    self._registrar_atividade_runtime(activity_message("ERRO", str(erro)))
                    self._parar()
                    self.status_var.set(erro_texto)
                    return

                if aplicada:
                    self.runtime_action_count += 1
                    self.runtime_action_counts_by_slot[perfil["slot"]] = (
                        self.runtime_action_counts_by_slot.get(perfil["slot"], 0) + 1
                    )
                    self._registrar_atividade_runtime(activity_from_action(acao))
                    self.runtime_slot_status_vars[int(perfil["slot"].split()[-1]) - 1].set(
                        f"{acao.get('entrada')} -> {acao.get('acao')}"
                    )
                    if (
                        self.runtime_activity_window is not None
                        and self.runtime_activity_window.winfo_exists()
                    ):
                        self.runtime_activity_window.atualizar_resumo_controles()
                    self.status_var.set(
                        "Status: Rodando | "
                        f"{perfil['slot']} | "
                        f"{acao.get('entrada')} {acao.get('estado')} -> {acao.get('acao')}"
                    )

    def _evento_e_atalho_desativar(self, evento):
        atalho = normalizar_rotulo_entrada(self.desativar_atalho_var.get())

        if not atalho:
            return False

        return (
            normalizar_rotulo_entrada(evento.get("tipo")) == "TECLADO"
            and normalizar_rotulo_entrada(evento.get("acao")) == "DOWN"
            and normalizar_rotulo_entrada(evento.get("entrada")) == atalho
        )

    def _validar_atalho_desativar_para_start(self):
        atalho = normalizar_rotulo_entrada(self.desativar_atalho_var.get())

        if atalho:
            return True

        self.status_var.set("Defina o atalho para parar antes de iniciar.")
        messagebox.showwarning(
            APP_NAME,
            "Defina um atalho para parar antes de iniciar.",
        )
        return False

    def _criar_backend_gamepad(self):
        return XboxGamepadBackend(
            stick_value=self._valor_int_var(self.stick_intensity_var, 100) / 100,
            pulse_seconds=self._valor_int_var(self.mouse_pulse_ms_var, 60) / 1000,
        )

    def _iniciar_bloqueador_input(self, perfis, session_id=None):
        self._parar_bloqueador_input()

        spec = criar_especificacao_bloqueio(perfis)

        if spec.empty():
            return

        callback = None
        if session_id is not None:
            callback = lambda evento: self._receber_evento_runtime(session_id, evento)

        self.input_blocker = PhysicalInputBlocker(
            spec,
            keyboard_event_callback=callback,
        )
        self.input_blocker.start()

    def _parar_bloqueador_input(self):
        if self.input_blocker is None:
            return

        try:
            self.input_blocker.stop()
        finally:
            self.input_blocker = None

    def _atualizar_gamepad_temporarios(self):
        if not self.gamepad_backends:
            return

        try:
            for backend in self.gamepad_backends.values():
                backend.atualizar_temporarios()
        except Exception as erro:
            erro_texto = f"Erro no gamepad: {erro}"
            self._registrar_atividade_runtime(activity_message("ERRO", str(erro)))
            self._parar()
            self.status_var.set(erro_texto)

    def _fechar_gamepad_backends(self):
        if not self.gamepad_backends:
            return

        for backend in self.gamepad_backends.values():
            try:
                backend.close()
            except Exception:
                pass

        self.gamepad_backends = {}

    def _descricao_perfis_runtime(self):
        return ", ".join(
            f"{perfil['slot']}={perfil['nome']}"
            for perfil in self.runtime_profiles
        )

    def _registrar_atividade_runtime(self, activity):
        item = self.runtime_activity_log.add(activity)

        if (
            self.runtime_activity_window is not None
            and self.runtime_activity_window.winfo_exists()
        ):
            self.runtime_activity_window.adicionar_atividade(item)

    def _sincronizar_janela_execucao(self):
        if (
            self.runtime_activity_window is not None
            and self.runtime_activity_window.winfo_exists()
        ):
            self.runtime_activity_window.atualizar_resumo_controles()
            self.runtime_activity_window.recarregar()

    def _abrir_execucao(self):
        if (
            self.runtime_activity_window is not None
            and self.runtime_activity_window.winfo_exists()
        ):
            self.runtime_activity_window.lift()
            self.runtime_activity_window.focus_force()
            return

        self.runtime_activity_window = RuntimeActivityWindow(self)

    def _abrir_teste_controle(self):
        TestGamepadWindow(self)

    def _abrir_terminal(self):
        if self.terminal_window is not None and self.terminal_window.winfo_exists():
            self.terminal_window.lift()
            self.terminal_window.focus_force()
            return

        self.terminal_window = InputTerminalWindow(self)

    def _atualizar_estado_execucao(self):
        if self.rodando:
            self.status_var.set("Status: Rodando")
            self.start_button.state(["disabled"])
            self.stop_button.state(["!disabled"])
            self.stop_button.configure(text="Pare")
        else:
            self.status_var.set("Status: Parado")
            self.start_button.state(["!disabled"])
            self.stop_button.state(["!disabled"])
            self.stop_button.configure(text="Ativar")


class TestGamepadWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)

        self.title("Teste de Controle")
        self.geometry("520x360")
        self.minsize(480, 320)

        self.master = master
        self.slot_var = tk.StringVar(value="Controle 1")
        self.status_var = tk.StringVar(value="")

        self._criar_layout()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _criar_layout(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(1, weight=1)

        ttk.Label(header, text="Controle", style="Muted.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
        )
        ttk.Combobox(
            header,
            textvariable=self.slot_var,
            values=[f"Controle {index}" for index in range(1, MAX_RUNTIME_CONTROLLERS + 1)],
            state="readonly",
        ).grid(row=0, column=1, sticky="ew")

        ttk.Label(root, textvariable=self.status_var, style="Status.TLabel").grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 10),
        )

        grid = ttk.Frame(root)
        grid.grid(row=2, column=0, sticky="nsew")

        acoes = [
            ("A", "A"),
            ("B", "B"),
            ("X", "X"),
            ("Y", "Y"),
            ("LB", "LB"),
            ("RB", "RB"),
            ("LT", "LT"),
            ("RT", "RT"),
            ("D-Up", "D-Pad Up"),
            ("D-Down", "D-Pad Down"),
            ("D-Left", "D-Pad Left"),
            ("D-Right", "D-Pad Right"),
            ("LS Up", "Left Stick Up"),
            ("LS Down", "Left Stick Down"),
            ("LS Left", "Left Stick Left"),
            ("LS Right", "Left Stick Right"),
            ("RS Up", "Right Stick Up"),
            ("RS Down", "Right Stick Down"),
            ("RS Left", "Right Stick Left"),
            ("RS Right", "Right Stick Right"),
        ]

        for index, (label, acao) in enumerate(acoes):
            row = index // 4
            column = index % 4
            grid.columnconfigure(column, weight=1)
            ttk.Button(
                grid,
                text=label,
                command=lambda value=acao: self._testar_acao(value),
            ).grid(row=row, column=column, sticky="ew", padx=4, pady=4)

    def _testar_acao(self, acao):
        slot = self.slot_var.get()

        try:
            backend, temporario = self._backend_para_teste(slot)
        except GamepadBackendError as erro:
            self.status_var.set(str(erro))
            messagebox.showerror(APP_NAME, str(erro))
            return

        action_down = {
            "slot": slot,
            "configuracao": "Teste",
            "tipo": "TESTE",
            "entrada": "TESTE",
            "estado": "DOWN",
            "acao": acao,
        }
        action_up = dict(action_down)
        action_up["estado"] = "UP"

        try:
            backend.aplicar_acao(action_down)
            self.status_var.set(f"{slot}: {acao}")
            self.master._registrar_atividade_runtime(activity_from_action(action_down))
            self.after(140, lambda: self._soltar_acao(backend, action_up, temporario))
        except Exception as erro:
            if temporario:
                backend.close()
            self.status_var.set(f"Erro no teste: {erro}")

    def _soltar_acao(self, backend, action_up, temporario):
        try:
            backend.aplicar_acao(action_up)
            self.master._registrar_atividade_runtime(activity_from_action(action_up))
        except Exception as erro:
            self.status_var.set(f"Erro no teste: {erro}")
        finally:
            if temporario:
                backend.close()

    def _backend_para_teste(self, slot):
        backend = self.master.gamepad_backends.get(slot)

        if self.master.rodando and backend is not None:
            return backend, False

        return self.master._criar_backend_gamepad(), True


class RuntimeActivityWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)

        self.title("Execucao")
        self.geometry("900x500")
        self.minsize(760, 420)

        self.master = master
        self.status_var = tk.StringVar(value="")

        self._criar_layout()
        self.atualizar_resumo_controles()
        self.recarregar()
        self.protocol("WM_DELETE_WINDOW", self._fechar)

    def _criar_layout(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Execucao", style="Header.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(header, textvariable=self.status_var, style="Status.TLabel").grid(
            row=0,
            column=1,
            sticky="e",
            padx=(0, 10),
        )
        ttk.Button(header, text="Limpar", command=self._limpar).grid(
            row=0,
            column=2,
            sticky="e",
            padx=(0, 8),
        )
        ttk.Button(header, text="Fechar", command=self._fechar).grid(
            row=0,
            column=3,
            sticky="e",
        )

        self.summary_table = ttk.Treeview(
            root,
            columns=("controle", "perfil", "teclado", "mouse", "acoes"),
            show="headings",
            height=5,
            selectmode="browse",
        )
        for column, heading, width in (
            ("controle", "Controle", 90),
            ("perfil", "Perfil", 150),
            ("teclado", "Teclado", 170),
            ("mouse", "Mouse", 170),
            ("acoes", "Acoes", 70),
        ):
            self.summary_table.heading(column, text=heading)
            self.summary_table.column(column, width=width, minwidth=70, stretch=True)

        self.summary_table.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        columns = (
            "hora",
            "tipo",
            "slot",
            "configuracao",
            "entrada",
            "estado",
            "acao",
            "dispositivo",
            "mensagem",
        )
        self.table = ttk.Treeview(root, columns=columns, show="headings", selectmode="browse")

        headings = {
            "hora": "Hora",
            "tipo": "Tipo",
            "slot": "Controle",
            "configuracao": "Perfil",
            "entrada": "Entrada",
            "estado": "Estado",
            "acao": "Acao",
            "dispositivo": "Dispositivo",
            "mensagem": "Mensagem",
        }
        widths = {
            "hora": 80,
            "tipo": 80,
            "slot": 95,
            "configuracao": 130,
            "entrada": 130,
            "estado": 80,
            "acao": 120,
            "dispositivo": 130,
            "mensagem": 220,
        }

        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=widths[column], minwidth=70, stretch=True)

        self.table.grid(row=2, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=self.table.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)

    def adicionar_atividade(self, activity):
        self.table.insert("", 0, values=self._values(activity))
        self._atualizar_status()

    def recarregar(self):
        self.table.delete(*self.table.get_children())

        for activity in reversed(self.master.runtime_activity_log.list()):
            self.adicionar_atividade(activity)

        self._atualizar_status()

    def atualizar_resumo_controles(self):
        self.summary_table.delete(*self.summary_table.get_children())

        for perfil in self.master.runtime_profiles:
            configuracao = perfil.get("configuracao") or {}
            dispositivos = configuracao.get("dispositivos") or {}
            self.summary_table.insert(
                "",
                tk.END,
                values=(
                    perfil.get("slot", ""),
                    perfil.get("nome", ""),
                    self._rotulo_dispositivo(dispositivos.get("teclado", "")),
                    self._rotulo_dispositivo(dispositivos.get("mouse", "")),
                    self.master.runtime_action_counts_by_slot.get(perfil.get("slot", ""), 0),
                ),
            )

    def _rotulo_dispositivo(self, device_id):
        return device_id or "Qualquer"

    def _values(self, activity):
        return (
            activity.get("hora", ""),
            activity.get("kind", ""),
            activity.get("slot", ""),
            activity.get("configuracao", ""),
            activity.get("entrada", ""),
            activity.get("estado", ""),
            activity.get("acao", ""),
            activity.get("dispositivo_id", ""),
            activity.get("message", ""),
        )

    def _limpar(self):
        self.master.runtime_activity_log.clear()
        self.table.delete(*self.table.get_children())
        self._atualizar_status()

    def _atualizar_status(self):
        self.status_var.set(f"{len(self.master.runtime_activity_log)} eventos")

    def _fechar(self):
        self.master.runtime_activity_window = None
        self.destroy()


class InputTerminalWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)

        self.title("Terminal de Entradas")
        self.geometry("1040x620")
        self.minsize(900, 520)

        self.event_queue = queue.Queue()
        self.device_manager = DeviceManager()
        self.monitor = RawInputMonitor(
            self.device_manager,
            event_callback=self._receber_evento,
            log_to_console=False,
        )
        self.monitor_thread = None
        self.monitorando = False
        self.limite_linhas = 250

        self.status_var = tk.StringVar(value="Monitor parado")

        self._criar_layout()
        self._iniciar_monitor()
        self.after(80, self._processar_fila)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

    def _criar_layout(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Terminal de Entradas", style="Header.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(header, textvariable=self.status_var, style="Status.TLabel").grid(
            row=0,
            column=1,
            sticky="e",
            padx=(0, 10),
        )
        ttk.Button(header, text="Limpar", command=self._limpar_tabelas).grid(
            row=0,
            column=2,
            sticky="e",
            padx=(0, 8),
        )
        ttk.Button(header, text="Fechar", command=self._fechar).grid(
            row=0,
            column=3,
            sticky="e",
        )

        content = ttk.Frame(root)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        self.keyboard_table = self._criar_tabela(
            content,
            titulo="Teclados",
            coluna=0,
            colunas=("hora", "dispositivo", "entrada", "estado", "detalhe"),
            cabecalhos=("Hora", "Teclado", "Tecla", "Estado", "Detalhe"),
            larguras=(80, 120, 90, 80, 150),
        )
        self.mouse_table = self._criar_tabela(
            content,
            titulo="Mouses",
            coluna=1,
            colunas=("hora", "dispositivo", "entrada", "acao", "detalhe"),
            cabecalhos=("Hora", "Mouse", "Entrada", "Ação", "Detalhe"),
            larguras=(80, 120, 100, 90, 180),
        )

    def _criar_tabela(self, parent, titulo, coluna, colunas, cabecalhos, larguras):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        panel.grid(row=0, column=coluna, sticky="nsew", padx=(0, 8) if coluna == 0 else (8, 0))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        ttk.Label(panel, text=titulo, style="Subheader.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        table = ttk.Treeview(panel, columns=colunas, show="headings", selectmode="browse")

        for nome_coluna, cabecalho, largura in zip(colunas, cabecalhos, larguras):
            table.heading(nome_coluna, text=cabecalho)
            table.column(nome_coluna, width=largura, minwidth=70, stretch=True)

        table.grid(row=1, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=table.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        table.configure(yscrollcommand=scrollbar.set)

        return table

    def _iniciar_monitor(self):
        if self.monitorando:
            return

        self.monitorando = True
        self.status_var.set("Monitor iniciado")
        self.monitor_thread = threading.Thread(target=self._rodar_monitor, daemon=True)
        self.monitor_thread.start()

    def _rodar_monitor(self):
        try:
            self.monitor.listar_dispositivos()
            self.monitor.iniciar()
        except Exception as erro:
            self.event_queue.put(
                {
                    "tipo": "ERRO",
                    "mensagem": str(erro),
                }
            )

    def _receber_evento(self, evento):
        self.event_queue.put(evento)

    def _processar_fila(self):
        while not self.event_queue.empty():
            evento = self.event_queue.get()

            if evento.get("tipo") == "ERRO":
                self.status_var.set(f"Erro: {evento.get('mensagem')}")
                continue

            self._adicionar_evento(evento)

        if self.winfo_exists():
            self.after(80, self._processar_fila)

    def _adicionar_evento(self, evento):
        hora = time.strftime("%H:%M:%S")
        tipo = evento.get("tipo")
        numero = evento.get("numero", "?")
        dispositivo = f"{tipo.title()} {numero}"

        if tipo == "TECLADO":
            self._inserir_linha(
                self.keyboard_table,
                (
                    hora,
                    dispositivo,
                    evento.get("entrada", ""),
                    evento.get("acao", ""),
                    evento.get("detalhe", ""),
                ),
            )
        elif tipo == "MOUSE":
            self._inserir_linha(
                self.mouse_table,
                (
                    hora,
                    dispositivo,
                    evento.get("entrada", ""),
                    evento.get("acao", ""),
                    evento.get("detalhe", ""),
                ),
            )

    def _inserir_linha(self, table, values):
        table.insert("", 0, values=values)

        children = table.get_children()

        if len(children) > self.limite_linhas:
            table.delete(*children[self.limite_linhas :])

    def _limpar_tabelas(self):
        self.keyboard_table.delete(*self.keyboard_table.get_children())
        self.mouse_table.delete(*self.mouse_table.get_children())

    def _fechar(self):
        self.status_var.set("Fechando monitor")
        self.monitor.parar()
        self.destroy()


def iniciar_interface():
    app = TheBindingOfKeyboardApp()
    app.mainloop()
