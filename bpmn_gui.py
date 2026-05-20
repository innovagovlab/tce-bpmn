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


class BpmnGuiApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gerador BPMN")
        center_window(self.root, 720, 240)
        self.root.resizable(False, False)

        self.input_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Selecione os arquivos para começar.")
        self.status_color_var = tk.StringVar(value="#1f2937")

        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, padx=16, pady=16)
        container.pack(fill="both", expand=True)

        title = tk.Label(
            container,
            text="Conversor de Documento para BPMN",
            font=("Segoe UI", 14, "bold"),
        )
        title.pack(anchor="w", pady=(0, 12))

        input_row = tk.Frame(container)
        input_row.pack(fill="x", pady=6)

        tk.Label(input_row, text="Arquivo de entrada:", width=20, anchor="w").pack(
            side="left"
        )
        tk.Entry(input_row, textvariable=self.input_path_var).pack(
            side="left", fill="x", expand=True, padx=8
        )
        tk.Button(
            input_row,
            text="Selecionar",
            command=self._select_input,
            bg="#0f4c81",
            fg="white",
            activebackground="#0b3c66",
            activeforeground="white",
            padx=10,
        ).pack(side="left")

        output_row = tk.Frame(container)
        output_row.pack(fill="x", pady=6)

        tk.Label(output_row, text="Salvar arquivo .bpmn:", width=20, anchor="w").pack(
            side="left"
        )
        tk.Entry(output_row, textvariable=self.output_path_var).pack(
            side="left", fill="x", expand=True, padx=8
        )
        tk.Button(
            output_row,
            text="Escolher local",
            command=self._select_output,
            bg="#0f4c81",
            fg="white",
            activebackground="#0b3c66",
            activeforeground="white",
            padx=10,
        ).pack(side="left")

        action_row = tk.Frame(container)
        action_row.pack(fill="x", pady=(16, 6))

        self.generate_button = tk.Button(
            action_row,
            text="Gerar BPMN",
            command=self._start_generation,
            height=2,
            bg="#1d7a3a",
            fg="white",
            activebackground="#155d2b",
            activeforeground="white",
            padx=16,
        )
        self.generate_button.pack(side="left")

        self.status_label = tk.Label(
            container,
            textvariable=self.status_var,
            fg=self.status_color_var.get(),
            font=("Segoe UI", 10, "bold"),
        )
        self.status_label.pack(anchor="w", pady=(8, 0))

    def _select_input(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo de entrada",
            filetypes=INPUT_FILETYPES,
        )
        if file_path:
            self.input_path_var.set(file_path)

            if not self.output_path_var.get():
                suggested_name = Path(file_path).stem + ".bpmn"
                self.output_path_var.set(str(Path("output") / suggested_name))

    def _select_output(self) -> None:
        file_path = filedialog.asksaveasfilename(
            title="Escolha onde salvar o BPMN",
            defaultextension=".bpmn",
            filetypes=[("BPMN", "*.bpmn")],
            initialfile="arquivo.bpmn",
        )
        if file_path:
            self.output_path_var.set(file_path)

    def _start_generation(self) -> None:
        input_path = self.input_path_var.get().strip()
        output_path = self.output_path_var.get().strip()

        if not input_path:
            messagebox.showwarning(
                "Campo obrigatório", "Selecione um arquivo de entrada."
            )
            return

        if not output_path:
            messagebox.showwarning(
                "Campo obrigatório", "Escolha onde salvar o arquivo .bpmn."
            )
            return

        self.generate_button.config(state="disabled")
        self.status_var.set("Processando arquivo e gerando BPMN...")
        self.status_label.config(fg="#0f4c81")

        threading.Thread(
            target=self._run_generation,
            args=(input_path, output_path),
            daemon=True,
        ).start()

    def _run_generation(self, input_path: str, output_path: str) -> None:
        try:
            saved_path = generate_bpmn_from_input(
                input_path=input_path,
                output_path=output_path,
                layout_js_path=LAYOUT_JS_PATH,
            )
            self.root.after(0, self._on_success, saved_path)
        except Exception as exc:
            self.root.after(0, self._on_error, str(exc))

    def _on_success(self, saved_path: str) -> None:
        self.generate_button.config(state="normal")
        self.status_var.set("Concluído: arquivo BPMN gerado e salvo com sucesso.")
        self.status_label.config(fg="#166534")
        messagebox.showinfo(
            "Geração concluída",
            f"O arquivo BPMN foi gerado com sucesso.\n\nLocal salvo:\n{saved_path}",
        )

    def _on_error(self, error_message: str) -> None:
        self.generate_button.config(state="normal")
        self.status_var.set("Falha ao gerar BPMN.")
        self.status_label.config(fg="#b91c1c")
        messagebox.showerror("Erro", f"Não foi possível gerar o BPMN:\n{error_message}")


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
