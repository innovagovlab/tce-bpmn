import xml.etree.ElementTree as ET
import sys
from pathlib import Path

from bpmn_transformer import BpmnTransformer
from config import LAYOUT_JS_PATH, FINAL_BPMN_PATH, VALID_TYPES

from utils.input_treatment import load_type_document


def _bundle_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


BASE_PATH = _bundle_base_path()
INPUT_PATH = str(BASE_PATH / "input" / "input_example.txt")
DEFAULT_LAYOUT_JS_PATH = str(BASE_PATH / Path(LAYOUT_JS_PATH))
DEFAULT_FINAL_BPMN_PATH = str(BASE_PATH / Path(FINAL_BPMN_PATH))

REQUIRED_KEYS = {"id", "type"}


def validate_process(process: list[dict]) -> None:
    for i, element in enumerate(process):
        missing = REQUIRED_KEYS - element.keys()
        if missing:
            raise ValueError(f"Elemento {i} esta faltando campos: {missing}")
        if element["type"] not in VALID_TYPES:
            raise ValueError(f"Tipo invalido no elemento {i}: {element['type']}")


class BpmnXmlGenerator:

    def __init__(self):
        self.transformer = BpmnTransformer()

    def create_bpmn_xml(self, process: list[dict]) -> str:
        """
        Transforma o processo em XML BPMN e salva no arquivo indicado.
        Retorna a string XML gerada.
        """

        transformed_process = self.transformer.transform(process)

        lanes_map = {}

        # Fazer com que o XML recconheça essas notações (definitions)
        root = ET.Element("bpmn:definitions")
        root.set("xmlns:bpmn", "http://www.omg.org/spec/BPMN/20100524/MODEL")
        root.set("xmlns:bpmndi", "http://www.omg.org/spec/BPMN/20100524/DI")
        root.set("xmlns:dc", "http://www.omg.org/spec/DD/20100524/DC")
        root.set("xmlns:di", "http://www.omg.org/spec/DD/20100524/DI")
        root.set("id", "definitions_1")

        # Criar a collaboration (base de criação de pools e lanes)
        collaboration = ET.SubElement(root, "bpmn:collaboration")
        collaboration.set("id", "Collaboration_1")

        # Participante da collab
        participant = ET.SubElement(collaboration, "bpmn:participant")
        participant.set("id", "Participant_1")
        participant.set("name", "Mapeamento do Trabalho")
        participant.set("processRef", "Process_1")

        # Criar o elemento do processo (Base para saber os elementos do diagrama e seus fluxos)
        process_element = ET.SubElement(root, "bpmn:process")
        process_element.set("id", "Process_1")
        process_element.set("isExecutable", "false")

        # Criar lane set do XML
        lane_set = ET.SubElement(process_element, "bpmn:laneSet")
        lane_set.set("id", "LaneSet_1")

        # Adicionando elementos
        for element in transformed_process["elements"]:
            elem = ET.SubElement(process_element, f"bpmn:{element["type"]}")
            elem.set("id", element["id"])

            lane_name = element.get("lane")

            if lane_name:
                if lane_name not in lanes_map:
                    lane = ET.SubElement(lane_set, "bpmn:lane")
                    lane.set("id", f"Lane_{len(lanes_map)+1}")
                    lane.set("name", lane_name)

                    lanes_map[lane_name] = lane

                ET.SubElement(lanes_map[lane_name], "bpmn:flowNodeRef").text = element[
                    "id"
                ]

            # Adicionando as descrições, caso exista
            if element["label"]:
                elem.set("name", element["label"])

            # Caso tenha um flow padrão no elemento, adicione no XML
            if "default_flow" in element and element["default_flow"]:
                elem.set("default", element["default_flow"])

            # Adicionando entradas e saídas dos fluxos de cada elemento
            for incoming in element["incoming"]:
                ET.SubElement(elem, "bpmn:incoming").text = incoming
            for outgoing in element["outgoing"]:
                ET.SubElement(elem, "bpmn:outgoing").text = outgoing

        # Adicionando fluxos no sistema por completo
        for flow in transformed_process["flows"]:
            seq_flow = ET.SubElement(process_element, "bpmn:sequenceFlow")
            seq_flow.set("id", flow["id"])
            seq_flow.set("sourceRef", flow["sourceRef"])
            seq_flow.set("targetRef", flow["targetRef"])

            # Caso haja condição, adicionada
            if flow["condition"]:
                seq_flow.set("name", flow["condition"])

        """
    A parte abaixo só consiste no DI do diagrama BPMN para com que o auto-layout entenda que contém uma pool no processo
    """

        # Criar o DI base do BPMN (Diagrama da modelagem)
        bpmn_diagram = ET.SubElement(root, "bpmndi:BPMNDiagram")
        bpmn_diagram.set("id", "BPMNDiagram_Process_1")

        # Criando de maneira manual o básico do diagrama da Collaboration
        bpmn_plane = ET.SubElement(bpmn_diagram, "bpmndi:BPMNPlane")
        bpmn_plane.set("id", "BPMNPlane_Process_1")
        bpmn_plane.set("bpmnElement", "Collaboration_1")
        bpmn_plane.text = "\n"

        lane_height = 200
        y_position = 0
        lane_width = 2000

        total_height = lane_height * len(lanes_map)

        # Criando de maneira manual o básico do diagrama dos Participants
        participant_shape = ET.SubElement(
            bpmn_plane,
            "bpmndi:BPMNShape",
            {
                "id": "Participant_1_di",
                "bpmnElement": "Participant_1",
                "isHorizontal": "true",
            },
        )
        ET.SubElement(
            participant_shape,
            "dc:Bounds",
            {"x": "0", "y": "0", "width": str(lane_width), "height": str(total_height)},
        )

        # Criando de maneira manual o básico do diagrama do shape das lanes
        for i, lane in enumerate(lanes_map.values(), start=1):

            lane_shape = ET.SubElement(
                bpmn_plane,
                "bpmndi:BPMNShape",
                {"id": f"Lane_{i}_di", "bpmnElement": lane.get("id")},
            )
            ET.SubElement(
                lane_shape,
                "dc:Bounds",
                {
                    "x": "0",
                    "y": str(y_position),
                    "width": str(lane_width),
                    "height": str(lane_height),
                },
            )

            y_position += lane_height

        tree = ET.ElementTree(root)

        ET.indent(tree, space="  ", level=0)

        xml_bytes = ET.tostring(root, encoding="unicode")
        return f"<?xml version='1.0' encoding='utf-8'?>\n{xml_bytes}"


def generate_bpmn_from_input(
    input_path: str,
    json_input: str,
    output_path: str,
    layout_js_path: str = DEFAULT_LAYOUT_JS_PATH,
) -> str:
    """
    Executa o pipeline completo:
    1) Lê e trata documento de entrada
    2) Solicita estrutura de processo para IA
    3) Converte para XML BPMN
    4) Aplica auto-layout
    5) Salva no caminho final

    Retorna o caminho absoluto do arquivo salvo.
    """
    from pipeline import BpmnPipeline

    if input_path:
        raw_input = load_type_document(input_path)
        layouted_xml = BpmnPipeline(layout_js_path=layout_js_path).run(raw_input)

    else:
        layouted_xml = BpmnPipeline(layout_js_path=layout_js_path).run(json_input=json_input)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(layouted_xml)

    return str(output_file.resolve())


if __name__ == "__main__":
    # Exemplo de uso por linha de comando
    generate_bpmn_from_input(INPUT_PATH, FINAL_BPMN_PATH, LAYOUT_JS_PATH)
