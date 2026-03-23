import xml.etree.ElementTree as ET
import json
import re

from bpmn_transformer import BpmnTransformer

from utils.load_process import load_process
from utils.apply_layout import apply_layout
from utils.input_treatment import load_type_document
from gpt_chat_completion import get_chat_completion

INPUT_PATH = "./input/input_example.txt"
LAYOUT_JS_PATH = "./auto-layout-process/layout.js"
FINAL_BPMN_PATH = "./output/arquivo.bpmn"


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

        ET.SubElement(lanes_map[lane_name], "bpmn:flowNodeRef").text = element["id"]
  

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
    
    '''
    A parte abaixo só consiste no DI do diagrama BPMN para com que o auto-layout entenda que contém uma pool no processo
    '''

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
        "isHorizontal": "true"
      }
    )
    ET.SubElement(
      participant_shape,
      "dc:Bounds",
      {
        "x": "0",
        "y": "0",
        "width": str(lane_width),
        "height": str(total_height)
      }
    )

    # Criando de maneira manual o básico do diagrama do shape das lanes
    for i, lane in enumerate(lanes_map.values(), start=1):
      
      lane_shape = ET.SubElement(
        bpmn_plane,
        "bpmndi:BPMNShape",
        {
            "id": f"Lane_{i}_di",
            "bpmnElement": lane.get("id")
        }
      )
      ET.SubElement(
        lane_shape,
        "dc:Bounds",
        {
            "x": "0",
            "y": str(y_position),
            "width": str(lane_width),
            "height": str(lane_height)
        }
      )

      y_position += lane_height

    tree = ET.ElementTree(root)

    ET.indent(tree, space="  ", level=0)

    xml_bytes = ET.tostring(root, encoding="unicode")
    return f"<?xml version='1.0' encoding='utf-8'?>\n{xml_bytes}"


if __name__ == "__main__":
  # Exemplo de processo (planilha transformada em JSON)

  result = load_type_document(INPUT_PATH)
  ai_response =  get_chat_completion(result)

  # remove markdown
  clean = re.sub(r"```json|```", "", ai_response).strip()

  data = json.loads(clean)

  xml_generator = BpmnXmlGenerator()
  bpmn_xml = xml_generator.create_bpmn_xml(load_process(data))

  layouted_xml = apply_layout(bpmn_xml, LAYOUT_JS_PATH)
  
  with open(FINAL_BPMN_PATH, "w", encoding="utf-8") as f:
    f.write(layouted_xml)
