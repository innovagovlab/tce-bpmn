from bpmn_parser import BpmnXmlGenerator, validate_process
from config import LAYOUT_JS_PATH
from gpt_chat_completion import get_chat_completion
from utils.apply_layout import apply_layout
from utils.load_process import load_process


class BpmnPipeline:
    def __init__(self, layout_js_path: str = LAYOUT_JS_PATH):
        self.layout_js_path = layout_js_path

    def run(self, raw_input: str) -> str:
        # IA -> JSON estruturado
        data = get_chat_completion(raw_input)

        # Validação
        process = load_process(data)
        validate_process(process)

        # Transformação -> XML
        xml = BpmnXmlGenerator().create_bpmn_xml(process)

        # Layout
        return apply_layout(xml, self.layout_js_path)
