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
        self.root.geometry("800x700")
        self.root.resizable(False, False)
 
        self.input_mode = tk.StringVar(value="texto")
        self.input_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Clique em Gerar após definir o arquivo de saída.")
        self.status_color = "#1f2937"
 
        self._build_ui()
        # Exibe o modo inicial correto
        self._update_input_mode()
 
    def _build_ui(self) -> None:
        container = tk.Frame(self.root, padx=30, pady=20)
        container.pack(fill="both", expand=True)
 
        tk.Label(
            container,
            text="Conversor de Documento para BPMN",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", pady=(0, 14))
 
        mode_frame = tk.Frame(container)
        mode_frame.pack(anchor="w", pady=(0, 10))
 
        tk.Label(mode_frame, text="Tipo de entrada:", font=("Segoe UI", 10)).pack(side="left")
 
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
 
        scroll_y = tk.Scrollbar(json_inner, orient="vertical", command=self.json_text.yview)
        scroll_y.pack(side="right", fill="y")
 
        scroll_x = tk.Scrollbar(self.text_frame, orient="horizontal", command=self.json_text.xview)
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
            self.text_frame.pack(fill="both", expand=True, pady=6, before=self._get_output_row())
 
    def _get_output_row(self):
        """Retorna o widget de saída para usar como referência de posição."""
        # Percorre os filhos do container e retorna o frame de saída
        container = self.generate_button.master.master
        for child in container.pack_slaves():
            if child is not self.file_frame and child is not self.text_frame:
                # O primeiro frame depois dos modos que contém o Entry de saída
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Entry) and subchild.cget("textvariable") == str(self.output_path_var):
                        return child
        return self.generate_button.master  # fallback
 
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
        mode = self.input_mode.get()
        output_path = self.output_path_var.get().strip()
        input_path = ""
        json_input = ""
 
        if mode == "arquivo":
            input_path = self.input_path_var.get().strip()
            if not input_path:
                messagebox.showwarning("Campo obrigatório", "Selecione um arquivo de entrada.")
                return
        else:
            json_input = self.json_text.get("1.0", tk.END).strip()
            if not json_input:
                messagebox.showwarning("Campo obrigatório", "Cole o JSON na caixa de texto.")
                return
 
        if not output_path:
            messagebox.showwarning("Campo obrigatório", "Escolha onde salvar o arquivo .bpmn.")
            return
 
        self.generate_button.config(state="disabled")
        self.status_var.set("Processando...")
        self.status_label.config(fg="#0f4c81")
 
        threading.Thread(
            target=self._run_generation,
            args=(input_path, json_input, output_path),
            daemon=True,
        ).start()
 
    def _run_generation(self, input_data: str, json_input: str, output_path: str) -> None:
        try:
            saved_path = generate_bpmn_from_input(
                input_path=input_data,
                json_input=json_input,
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