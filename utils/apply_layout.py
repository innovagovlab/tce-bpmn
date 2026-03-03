import subprocess


def apply_layout(bpmn_xml: str, layout_js_path: str) -> str:
    """
    Passa o XML BPMN para o layout.js via stdin e retorna o XML
    com o layout organizado pela biblioteca bpmn-auto-layout.
    Lança RuntimeError se o processo Node.js falhar.
    """
    result = subprocess.run(
        ["node", layout_js_path],
        input=bpmn_xml,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"layout.js falhou (código {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout
