import json
import re
import pandas as pd
from docx import Document

def load_type_document(file_path: str) -> str:
    ext = file_path.rsplit(".", 1)[-1].lower()

    if ext in ("json", "txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    elif ext == "docx":
        return docx_to_json(file_path)
    
    elif ext == "md":
        with open(file_path, "r", encoding="utf-8") as f:  # ✅ lê o arquivo primeiro
            return md_to_json(f.read())
    
    elif ext == "xlsx":
        return xlsx_to_json(file_path)
    
    else:
        raise ValueError(f"Formato não suportado .{ext}")


def docx_to_json(file_path: str) -> str:
    doc = Document (file_path)
    rows = []

    for table in doc.tables:
        headers = [cell.text.strip() for cell in table.rows[0].cells]
        for row in table.rows[1:]:
            values = [cell.text.strip() for cell in row.cells]
            rows.append(dict(zip(headers, values)))

    return json.dumps({"processo": rows}, ensure_ascii=False, indent=2)

def md_to_json(md_content: str) -> str:
    lines = [l.strip() for l in md_content.strip().splitlines()]

    lines = [l for l in lines if l]
    headers = [h.strip() for h in lines[0].split("|") if h.strip()]
    
    rows = []
    for line in lines[2:]:
        if re.match(r"^[\|\s\:\-]+$", line):
            continue
        
        values = [v.strip() for v in line.split("|")]
        values = [v for v in values if v != ""]
        values = [re.sub(r"\*+([^*]+)\*+", r"\1", v) for v in values]

        if values:
            rows.append(dict(zip(headers, values)))

    return json.dumps({"processo": rows}, ensure_ascii=False, indent=2)

def xlsx_to_json(file_path: str) -> str:
    df = pd.read_excel(file_path)
    rows = json.loads(df.to_json(orient="records", force_ascii=False))
    return json.dumps({"processo": rows}, ensure_ascii=False, indent=2)
