import json
from pathlib import Path


def load_process(source: str | dict | list) -> list[dict]:
    """
    Aceita:
    - Um dicionário Python com chave 'process'
    - Uma lista Python diretamente
    - Caminho para um arquivo .json (str ou Path)
    - String JSON raw
    """
    if isinstance(source, list):
        return source

    if isinstance(source, dict):
        return source.get("process", source)

    # Tenta carregar como arquivo .json
    path = Path(source)
    if path.exists() and path.suffix == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("process", data)

    # Tenta interpretar como string JSON raw
    try:
        data = json.loads(source)
        if isinstance(data, list):
            return data
        return data.get("process", data)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Fonte inválida: não é um arquivo, dicionário nem JSON válido. Detalhe: {e}"
        )
