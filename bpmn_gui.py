import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from bpmn_parser import LAYOUT_JS_PATH, generate_bpmn_from_input
from utils.auth import AuthError, AuthService

INPUT_FILETYPES = [
    ("Arquivos suportados", "*.txt *.json *.md *.docx *.xlsx"),
    ("Texto", "*.txt"),
    ("JSON", "*.json"),
    ("Markdown", "*.md"),
    ("Word", "*.docx"),
    ("Excel", "*.xlsx"),
]


def center_window(window: tk.Tk | tk.Toplevel, width: int, height: int) -> None:
    window.update_idletasks()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x_pos = max((screen_w - width) // 2, 0)
    y_pos = max((screen_h - height) // 2, 0)
    window.geometry(f"{width}x{height}+{x_pos}+{y_pos}")


def _default_dialog_dir() -> str:
    downloads_dir = Path.home() / "Downloads"
    if downloads_dir.exists():
        return str(downloads_dir)
    return str(Path.home())


class BpmnGuiApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gerador BPMN")
        self.root.geometry("820x620")
        center_window(self.root, 820, 650)
        self.root.resizable(False, False)

        self.input_mode = tk.StringVar(value="texto")
        self.input_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.output_path_user_set = False
        self._setting_output_path = False
        self.status_var = tk.StringVar(
            value="Clique em Gerar após definir o arquivo de saída."
        )
        self.status_color = "#1f2937"

        self._build_ui()
        self.output_path_var.trace_add("write", self._on_output_path_change)
        # Exibe o modo inicial correto
        self._update_input_mode()

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, padx=30, pady=20)
        container.pack(fill="both", expand=True)

        header = tk.Frame(container)
        header.pack(fill="x", pady=(0, 14))

        tk.Label(
            header,
            text="Conversor de Documento para BPMN",
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")

        tk.Button(
            header,
            text="Ajuda",
            command=self._abrir_ajuda,
            bg="#3e78ff",
            fg="white",
            font=("Segoe UI", 10),
            padx=8,
            relief="flat",
        ).pack(side="right")

        mode_frame = tk.Frame(container)
        mode_frame.pack(anchor="w", pady=(0, 10))

        tk.Label(mode_frame, text="Tipo de entrada:", font=("Segoe UI", 10)).pack(
            side="left"
        )

        tk.Radiobutton(
            mode_frame,
            text="Arquivo",
            variable=self.input_mode,
            value="arquivo",
            command=self._update_input_mode,
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(10, 4))

        tk.Radiobutton(
            mode_frame,
            text="Texto (JSON)",
            variable=self.input_mode,
            value="texto",
            command=self._update_input_mode,
            font=("Segoe UI", 10),
        ).pack(side="left", padx=4)

        self.file_frame = tk.Frame(container)

        tk.Label(
            self.file_frame,
            text="Arquivo de entrada:",
            width=20,
            anchor="w",
            font=("Segoe UI", 10),
        ).pack(side="left")

        tk.Entry(
            self.file_frame,
            textvariable=self.input_path_var,
            font=("Segoe UI", 10),
        ).pack(side="left", fill="x", expand=True, padx=8)

        tk.Button(
            self.file_frame,
            text="Selecionar arquivo",
            command=self._select_input,
            bg="#0f4c81",
            fg="white",
            activebackground="#0b3c66",
            activeforeground="white",
            font=("Segoe UI", 10),
            padx=10,
        ).pack(side="left")

        self.text_frame = tk.Frame(container)

        tk.Label(
            self.text_frame,
            text="Cole o JSON do processo:",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 4))

        json_inner = tk.Frame(self.text_frame)
        json_inner.pack(fill="both", expand=True)

        self.json_text = tk.Text(
            json_inner,
            wrap="none",
            font=("Consolas", 10),
        )
        self.json_text.pack(side="left", fill="both", expand=True)

        scroll_y = tk.Scrollbar(
            json_inner, orient="vertical", command=self.json_text.yview
        )
        scroll_y.pack(side="right", fill="y")

        scroll_x = tk.Scrollbar(
            self.text_frame, orient="horizontal", command=self.json_text.xview
        )
        scroll_x.pack(fill="x")

        self.json_text.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )

        output_row = tk.Frame(container)
        output_row.pack(fill="x", pady=10)

        tk.Label(
            output_row,
            text="Salvar arquivo .bpmn:",
            width=20,
            anchor="w",
            font=("Segoe UI", 10),
        ).pack(side="left")

        tk.Entry(
            output_row,
            textvariable=self.output_path_var,
            font=("Segoe UI", 10),
        ).pack(side="left", fill="x", expand=True, padx=8)

        tk.Button(
            output_row,
            text="Escolher local",
            command=self._select_output,
            bg="#0f4c81",
            fg="white",
            activebackground="#0b3c66",
            activeforeground="white",
            font=("Segoe UI", 10),
            padx=10,
        ).pack(side="left")

        action_row = tk.Frame(container)
        action_row.pack(fill="x", pady=(14, 6))

        self.generate_button = tk.Button(
            action_row,
            text="Gerar BPMN",
            command=self._start_generation,
            height=2,
            bg="#1d7a3a",
            fg="white",
            activebackground="#155d2b",
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            padx=20,
        )
        self.generate_button.pack(side="left")

        self.status_label = tk.Label(
            container,
            textvariable=self.status_var,
            fg=self.status_color,
            font=("Segoe UI", 10, "bold"),
        )
        self.status_label.pack(anchor="w", pady=(8, 0))

    def _update_input_mode(self) -> None:
        mode = self.input_mode.get()

        if mode == "arquivo":
            # Esconde caixa de texto, mostra seletor de arquivo
            self.text_frame.pack_forget()
            self.file_frame.pack(fill="x", pady=6, before=self._get_output_row())
        else:
            # Esconde seletor de arquivo, mostra caixa de texto
            self.file_frame.pack_forget()
            self.text_frame.pack(
                fill="both", expand=True, pady=6, before=self._get_output_row()
            )

    def _get_output_row(self):
        """Retorna o widget de saída para usar como referência de posição."""
        # Percorre os filhos do container e retorna o frame de saída
        container = self.generate_button.master.master
        for child in container.pack_slaves():
            if child is not self.file_frame and child is not self.text_frame:
                # O primeiro frame depois dos modos que contém o Entry de saída
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Entry) and subchild.cget(
                        "textvariable"
                    ) == str(self.output_path_var):
                        return child
        return self.generate_button.master  # fallback

    def _set_output_path(self, value: str, user_set: bool) -> None:
        self._setting_output_path = True
        self.output_path_var.set(value)
        self._setting_output_path = False
        self.output_path_user_set = user_set and bool(value.strip())

    def _on_output_path_change(self, *_: object) -> None:
        if self._setting_output_path:
            return
        self.output_path_user_set = bool(self.output_path_var.get().strip())

    def _default_output_path(self, input_path: str) -> Path:
        if input_path:
            filename = f"{Path(input_path).stem}.bpmn"
        else:
            filename = "arquivo.bpmn"
        return Path("output") / filename

    def _ensure_unique_path(self, target_path: Path) -> Path:
        if not target_path.exists():
            return target_path

        for index in range(1, 1000):
            candidate = target_path.with_name(
                f"{target_path.stem}_{index}{target_path.suffix}"
            )
            if not candidate.exists():
                return candidate

        return target_path

    def _select_input(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo de entrada",
            filetypes=INPUT_FILETYPES,
            initialdir=_default_dialog_dir(),
        )
        if file_path:
            self.input_path_var.set(file_path)
            if not self.output_path_var.get().strip():
                suggested_name = Path(file_path).stem + ".bpmn"
                self._set_output_path(
                    str(Path("output") / suggested_name), user_set=False
                )

    def _select_output(self) -> None:
        file_path = filedialog.asksaveasfilename(
            title="Escolha onde salvar o BPMN",
            defaultextension=".bpmn",
            filetypes=[("BPMN", "*.bpmn")],
            initialfile="arquivo.bpmn",
            initialdir=_default_dialog_dir(),
        )
        if file_path:
            self._set_output_path(file_path, user_set=True)

    def _start_generation(self) -> None:
        mode = self.input_mode.get()
        output_path = self.output_path_var.get().strip()
        input_path = ""
        json_input = ""

        if mode == "arquivo":
            input_path = self.input_path_var.get().strip()
            if not input_path:
                messagebox.showwarning(
                    "Campo obrigatório", "Selecione um arquivo de entrada."
                )
                return
        else:
            json_input = self.json_text.get("1.0", tk.END).strip()
            if not json_input:
                messagebox.showwarning(
                    "Campo obrigatório", "Cole o JSON na caixa de texto."
                )
                return

        prompt_for_save = not output_path or not self.output_path_user_set
        if prompt_for_save:
            if output_path:
                output_path = str(self._ensure_unique_path(Path(output_path)))
            else:
                output_path = str(
                    self._ensure_unique_path(self._default_output_path(input_path))
                )

        self.generate_button.config(state="disabled")
        self.status_var.set("Processando...")
        self.status_label.config(fg="#0f4c81")

        threading.Thread(
            target=self._run_generation,
            args=(input_path, json_input, output_path, prompt_for_save),
            daemon=True,
        ).start()

    def _run_generation(
        self,
        input_data: str,
        json_input: str,
        output_path: str,
        prompt_for_save: bool,
    ) -> None:
        try:
            saved_path = generate_bpmn_from_input(
                input_path=input_data,
                json_input=json_input,
                output_path=output_path,
                layout_js_path=LAYOUT_JS_PATH,
            )
            self.root.after(0, self._on_success, saved_path, prompt_for_save)
        except Exception as exc:
            self.root.after(0, self._on_error, str(exc))

    def _on_success(self, saved_path: str, prompt_for_save: bool) -> None:
        self.generate_button.config(state="normal")
        final_path = saved_path

        if prompt_for_save:
            chosen_path = filedialog.asksaveasfilename(
                title="Escolha onde salvar o BPMN",
                defaultextension=".bpmn",
                filetypes=[("BPMN", "*.bpmn")],
                initialfile=Path(saved_path).name,
                initialdir=str(Path(saved_path).parent)
                if Path(saved_path).parent.exists()
                else _default_dialog_dir(),
            )
            if chosen_path:
                try:
                    target_path = Path(chosen_path)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    if Path(saved_path).resolve() != target_path.resolve():
                        shutil.move(saved_path, target_path)
                    final_path = str(target_path.resolve())
                    self._set_output_path(final_path, user_set=True)
                except Exception as exc:
                    self.status_var.set("Falha ao salvar o arquivo BPMN.")
                    self.status_label.config(fg="#b91c1c")
                    messagebox.showerror(
                        "Erro",
                        f"Não foi possível salvar o BPMN:\n{exc}",
                    )
                    return
            else:
                self._set_output_path(final_path, user_set=False)
                self.status_var.set(
                    "Concluído: arquivo BPMN gerado (salvo temporariamente)."
                )
                self.status_label.config(fg="#166534")
                messagebox.showinfo(
                    "Geração concluída",
                    "O arquivo BPMN foi gerado, mas o local definitivo não foi escolhido."
                    f"\n\nArquivo salvo temporariamente em:\n{final_path}",
                )
                return

        self.status_var.set("Concluído: arquivo BPMN gerado e salvo com sucesso.")
        self.status_label.config(fg="#166534")
        messagebox.showinfo(
            "Geração concluída",
            f"O arquivo BPMN foi gerado com sucesso.\n\nLocal salvo:\n{final_path}",
        )

    def _on_error(self, error_message: str) -> None:
        self.generate_button.config(state="normal")
        self.status_var.set("Falha ao gerar BPMN.")
        self.status_label.config(fg="#b91c1c")
        messagebox.showerror("Erro", f"Não foi possível gerar o BPMN:\n{error_message}")

    def _abrir_ajuda(self) -> None:
        janela = tk.Toplevel(self.root)
        janela.title("Ajuda")
        janela.geometry("760x520")
        janela.resizable(False, False)

        texto = tk.Text(janela, wrap="word", padx=10, pady=10)
        texto.tag_config("negrito", font=("Segoe UI", 10, "bold"))
        texto.tag_config("titulo", font=("Segoe UI", 10, "bold"), justify=("center"))
        texto.tag_config("italico", font=("Segoe UI", 10, "italic"))

        texto.insert(
            "end",
            "--------------------------------------------------------------------------------\n",
            "titulo",
        )
        texto.insert("end", "Fluxo: ARQUIVO\n", "titulo")
        texto.insert(
            "end",
            "--------------------------------------------------------------------------------\n\n",
            "titulo",
        )
        texto.insert(
            "end",
            "1. Clique em 'Selecionar Arquivo' para escolher um arquivo do seu computador.\n",
        )
        texto.insert(
            "end",
            "2. Clique em 'Escolher Local' para definir onde o arquivo .bpmn será salvo.\n",
        )
        texto.insert("end", "3. Clique em 'Gerar BPMN'.\n\n")
        texto.insert("end", "ALERTA - Tipos aceitos: ", "negrito")
        texto.insert("end", ".docx, .json, .md, .txt, .xlsx\n\n\n")

        texto.insert(
            "end",
            "--------------------------------------------------------------------------------\n",
            "titulo",
        )
        texto.insert("end", "Fluxo: TEXTO (JSON)\n", "titulo")
        texto.insert(
            "end",
            "--------------------------------------------------------------------------------\n\n",
            "titulo",
        )
        texto.insert("end", "1. Acesse o AuroraChat no seu navegador.\n")
        texto.insert("end", "2. Abra o arquivo ")
        texto.insert("end", "'full-bpmn-json-prompt.txt'", "italico")
        texto.insert("end", " e copie o prompt.\n")
        texto.insert(
            "end",
            "3. Cole o prompt no AuroraChat juntamente com a tabela de entrada desejada (em texto) e envie.\n",
        )
        texto.insert("end", "4. Copie a resposta JSON retornada.\n")
        texto.insert("end", "5. Cole na caixa 'Resposta JSON' do aplicativo.\n")
        texto.insert(
            "end",
            "6. Clique em 'Escolher Local' para definir onde o arquivo .bpmn será salvo.\n",
        )
        texto.insert("end", "7. Clique em 'Gerar BPMN'.\n\n")
        texto.insert("end", "ALERTA - A resposta deve ser um JSON válido ", "negrito")
        texto.insert(
            "end",
            "no formato esperado (com 'process', 'type', 'id', 'label', 'lane', 'branches', etc.).",
        )

        texto.config(state="disabled")  # Somente leitura
        texto.pack(fill="both", expand=True)

        tk.Button(janela, text="Fechar", command=janela.destroy).pack(pady=10)


class AuthWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Login")
        center_window(self.root, 520, 360)
        self.root.resizable(False, False)

        self.auth = AuthService()
        try:
            self.auth.ensure_ready()
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao iniciar autenticação:\n{exc}")
            self.root.destroy()
            return

        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, padx=16, pady=16)
        container.pack(fill="both", expand=True)

        title = tk.Label(
            container,
            text="Acesso ao sistema",
            font=("Segoe UI", 14, "bold"),
        )
        title.pack(anchor="w", pady=(0, 12))

        email_row = tk.Frame(container)
        email_row.pack(fill="x", pady=6)
        tk.Label(email_row, text="Email:", width=12, anchor="w").pack(side="left")
        tk.Entry(email_row, textvariable=self.email_var).pack(
            side="left", fill="x", expand=True, padx=8
        )

        password_row = tk.Frame(container)
        password_row.pack(fill="x", pady=6)
        tk.Label(password_row, text="Senha:", width=12, anchor="w").pack(side="left")
        tk.Entry(password_row, textvariable=self.password_var, show="*").pack(
            side="left", fill="x", expand=True, padx=8
        )

        action_row = tk.Frame(container)
        action_row.pack(fill="x", pady=(16, 8))

        tk.Button(
            action_row,
            text="Entrar",
            command=self._login,
            bg="#0f4c81",
            fg="white",
            activebackground="#0b3c66",
            activeforeground="white",
            padx=16,
        ).pack(side="left")

        tk.Button(
            action_row,
            text="Cadastrar",
            command=self._open_register,
            bg="#1d7a3a",
            fg="white",
            activebackground="#155d2b",
            activeforeground="white",
            padx=16,
        ).pack(side="left", padx=8)

        tk.Button(
            action_row,
            text="Alterar senha",
            command=self._open_reset,
            bg="#6b7280",
            fg="white",
            activebackground="#4b5563",
            activeforeground="white",
            padx=16,
        ).pack(side="left")

        note = tk.Label(
            container,
            text="Use a OTP enviada por email para definir a primeira senha.",
            fg="#374151",
            font=("Segoe UI", 9),
        )
        note.pack(anchor="w", pady=(12, 0))

    def _login(self) -> None:
        email = self.email_var.get().strip()
        password = self.password_var.get().strip()

        if not email or not password:
            messagebox.showwarning("Campos obrigatórios", "Informe email e senha.")
            return

        try:
            if not self.auth.authenticate(email, password):
                messagebox.showerror("Login", "Email ou senha inválidos.")
                return
        except AuthError as exc:
            messagebox.showwarning("Login", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Login", f"Falha ao autenticar:\n{exc}")
            return

        for widget in self.root.winfo_children():
            widget.destroy()
        BpmnGuiApp(self.root)

    def _open_register(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Cadastro")
        center_window(dialog, 420, 200)
        dialog.resizable(False, False)

        email_var = tk.StringVar()

        container = tk.Frame(dialog, padx=16, pady=16)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Email:", anchor="w").pack(anchor="w")
        tk.Entry(container, textvariable=email_var).pack(fill="x", pady=(4, 12))

        def submit() -> None:
            email = email_var.get().strip()
            if not email:
                messagebox.showwarning("Cadastro", "Informe o email.")
                return
            try:
                self.auth.register_user(email)
            except AuthError as exc:
                messagebox.showerror("Cadastro", str(exc))
                return
            except Exception as exc:
                messagebox.showerror("Cadastro", f"Falha ao cadastrar:\n{exc}")
                return

            messagebox.showinfo(
                "Cadastro",
                "Usuário criado. Enviamos a OTP por email para definir a senha.",
            )
            dialog.destroy()

        tk.Button(
            container,
            text="Cadastrar",
            command=submit,
            bg="#1d7a3a",
            fg="white",
            activebackground="#155d2b",
            activeforeground="white",
            padx=12,
        ).pack()

    def _open_reset(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Alterar senha")
        center_window(dialog, 460, 320)
        dialog.resizable(False, False)

        email_var = tk.StringVar()
        otp_var = tk.StringVar()
        new_password_var = tk.StringVar()
        confirm_var = tk.StringVar()

        container = tk.Frame(dialog, padx=16, pady=16)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Email:", anchor="w").pack(anchor="w")
        tk.Entry(container, textvariable=email_var).pack(fill="x", pady=(4, 8))

        tk.Label(container, text="OTP:", anchor="w").pack(anchor="w")
        tk.Entry(container, textvariable=otp_var).pack(fill="x", pady=(4, 8))

        tk.Label(container, text="Nova senha:", anchor="w").pack(anchor="w")
        tk.Entry(container, textvariable=new_password_var, show="*").pack(
            fill="x", pady=(4, 8)
        )

        tk.Label(container, text="Confirmar senha:", anchor="w").pack(anchor="w")
        tk.Entry(container, textvariable=confirm_var, show="*").pack(
            fill="x", pady=(4, 12)
        )

        action_row = tk.Frame(container)
        action_row.pack(fill="x")

        def resend_otp() -> None:
            email = email_var.get().strip()
            if not email:
                messagebox.showwarning("OTP", "Informe o email para enviar a OTP.")
                return
            try:
                self.auth.issue_otp(email)
            except AuthError as exc:
                messagebox.showerror("OTP", str(exc))
                return
            except Exception as exc:
                messagebox.showerror("OTP", f"Falha ao enviar OTP:\n{exc}")
                return
            messagebox.showinfo("OTP", "OTP enviada por email.")

        def submit() -> None:
            email = email_var.get().strip()
            otp = otp_var.get().strip()
            new_password = new_password_var.get().strip()
            confirm = confirm_var.get().strip()

            if not email or not otp or not new_password:
                messagebox.showwarning("Senha", "Preencha todos os campos.")
                return
            if new_password != confirm:
                messagebox.showwarning("Senha", "As senhas não conferem.")
                return

            try:
                self.auth.reset_password(email, otp, new_password)
            except AuthError as exc:
                messagebox.showerror("Senha", str(exc))
                return
            except Exception as exc:
                messagebox.showerror("Senha", f"Falha ao alterar senha:\n{exc}")
                return

            messagebox.showinfo("Senha", "Senha atualizada com sucesso.")
            dialog.destroy()

        tk.Button(
            action_row,
            text="Reenviar OTP",
            command=resend_otp,
            bg="#6b7280",
            fg="white",
            activebackground="#4b5563",
            activeforeground="white",
            padx=12,
        ).pack(side="left")

        tk.Button(
            action_row,
            text="Alterar",
            command=submit,
            bg="#0f4c81",
            fg="white",
            activebackground="#0b3c66",
            activeforeground="white",
            padx=12,
        ).pack(side="right")


def main() -> None:
    root = tk.Tk()
    AuthWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
