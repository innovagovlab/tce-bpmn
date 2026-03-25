import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from bpmn_parser import LAYOUT_JS_PATH, generate_bpmn_from_input


INPUT_FILETYPES = [
    ("Arquivos suportados", "*.txt *.json *.md *.docx *.xlsx"),
    ("Texto", "*.txt"),
    ("JSON", "*.json"),
    ("Markdown", "*.md"),
    ("Word", "*.docx"),
    ("Excel", "*.xlsx"),
]


class BpmnGuiApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gerador BPMN")
        self.root.geometry("720x240")
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


def main() -> None:
    root = tk.Tk()
    app = BpmnGuiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
