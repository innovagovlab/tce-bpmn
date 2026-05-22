from bpmn_parser import BpmnXmlGenerator, validate_process
from config import LAYOUT_JS_PATH
from gpt_chat_completion import get_chat_completion
from utils.apply_layout import apply_layout
from utils.load_process import load_process
import json
import re


def _clean_json_input(json_input: str) -> str:
    cleaned = json_input.strip().lstrip("\ufeff")
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned


class BpmnPipeline:
    def __init__(self, layout_js_path: str = LAYOUT_JS_PATH):
        self.layout_js_path = layout_js_path

    def run(self, raw_input: str = "", json_input: str = "") -> str:
        if json_input:
            # Pula a IA, entra direto na validação
            cleaned = _clean_json_input(json_input)
            if not cleaned:
                raise ValueError("JSON vazio na entrada de texto.")
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "JSON invalido na entrada de texto: "
                    f"{exc.msg} (linha {exc.lineno}, coluna {exc.colno})."
                ) from exc
        else:
            # Fluxo normal: IA -> JSON estruturado
            data = get_chat_completion(raw_input)

        # Validação
        process = load_process(data)
        validate_process(process)

        # Transformação -> XML
        xml = BpmnXmlGenerator().create_bpmn_xml(process)

        # Layout
        return apply_layout(xml, self.layout_js_path)
