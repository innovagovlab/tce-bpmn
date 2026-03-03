import xml.etree.ElementTree as ET

from bpmn_transformer import BpmnTransformer

from utils.load_process import load_process
from utils.apply_layout import apply_layout


LAYOUT_JS_PATH = "./layout.js"


class BpmnXmlGenerator:

    def __init__(self):
        self.transformer = BpmnTransformer()

    def create_bpmn_xml(self, process: list[dict]) -> str:
        """
        Transforma o processo em XML BPMN e salva no arquivo indicado.
        Retorna a string XML gerada.
        """

        transformed_process = self.transformer.transform(process)

        # Create the root element (definitions)
        root = ET.Element("definitions")
        root.set("xmlns", "http://www.omg.org/spec/BPMN/20100524/MODEL")
        root.set("xmlns:bpmndi", "http://www.omg.org/spec/BPMN/20100524/DI")
        root.set("xmlns:dc", "http://www.omg.org/spec/DD/20100524/DC")
        root.set("xmlns:di", "http://www.omg.org/spec/DD/20100524/DI")
        root.set("id", "definitions_1")

        # Create the process element
        process_element = ET.SubElement(root, "process")
        process_element.set("id", "Process_1")
        process_element.set("isExecutable", "false")

        # Adicionando elementos
        for element in transformed_process["elements"]:
            elem = ET.SubElement(process_element, element["type"])
            elem.set("id", element["id"])

            # Adicionando as descrições, caso exista
            if element["label"]:
                elem.set("name", element["label"])

            # Caso tenha um flow padrão no elemento, adicione no XML
            if "default_flow" in element and element["default_flow"]:
                elem.set("default", element["default_flow"])

            # Adicionando entradas e saídas dos fluxos de cada elemento
            for incoming in element["incoming"]:
                ET.SubElement(elem, "incoming").text = incoming
            for outgoing in element["outgoing"]:
                ET.SubElement(elem, "outgoing").text = outgoing

        # Adicionando fluxos no sistema por completo
        for flow in transformed_process["flows"]:
            seq_flow = ET.SubElement(process_element, "sequenceFlow")
            seq_flow.set("id", flow["id"])
            seq_flow.set("sourceRef", flow["sourceRef"])
            seq_flow.set("targetRef", flow["targetRef"])

            # Caso haja condição, adicionada
            if flow["condition"]:
                seq_flow.set("name", flow["condition"])

        tree = ET.ElementTree(root)

        ET.indent(tree, space="  ", level=0)

        tree.write("arquivo.bpmn", encoding="utf-8", xml_declaration=True)

        xml_bytes = ET.tostring(root, encoding="unicode")
        return f"<?xml version='1.0' encoding='utf-8'?>\n{xml_bytes}"


## Exemplo feito manual, não utilizo chamada via API por que eu ainda não tenho :)
if __name__ == "__main__":
    process = """
    {
  "process": [
    {
      "type": "startEvent",
      "id": "cs_start",
      "label": "Início Manutenção"
    },
    {
      "type": "inclusiveGateway",
      "id": "cs_gateway1",
      "label": "Forma de Início",
      "has_join": true,
      "branches": [
        {
          "condition": "Verificação periódica Ouvidoria",
          "path": [
            {
              "type": "userTask",
              "id": "cs_task1a",
              "label": "Iniciar Manutenção"
            },
            {
              "type": "sendTask",
              "id": "cs_task2",
              "label": "Comunicar Setor"
            }
          ]
        },
        {
          "condition": "Identificação espontânea Ouvidoria",
          "path": [
            {
              "type": "userTask",
              "id": "cs_task1b",
              "label": "Iniciar Manutenção"
            },
            {
              "type": "sendTask",
              "id": "cs_task2_repeat",
              "label": "Comunicar Setor"
            }
          ]
        },
        {
          "condition": "Solicitação direta de setor",
          "path": [
            {
              "type": "userTask",
              "id": "cs_task1c",
              "label": "Iniciar Manutenção"
            }
          ]
        }
      ]
    },
    {
      "type": "userTask",
      "id": "cs_task3",
      "label": "Solicitar Alteração Carta"
    },
    {
      "type": "userTask",
      "id": "cs_task4",
      "label": "Analisar Solicitação"
    },
    {
      "type": "exclusiveGateway",
      "id": "cs_gateway2",
      "label": "Solicitação Completa?",
      "has_join": false,
      "branches": [
        {
          "condition": "Sim",
          "path": [
            {
              "type": "serviceTask",
              "id": "cs_task5",
              "label": "Alterar Carta"
            },
            {
              "type": "parallelGateway",
              "id": "cs_gateway3",
              "branches": [
                [
                  {
                    "type": "serviceTask",
                    "id": "cs_task6",
                    "label": "Publicar Alteração"
                  }
                ],
                [
                  {
                    "type": "sendTask",
                    "id": "cs_task7",
                    "label": "Comunicar Conclusão"
                  }
                ]
              ]
            },
            {
              "type": "endEvent",
              "id": "cs_end",
              "label": "Conclusão Processo"
            }
          ]
        },
        {
          "condition": "Não",
          "path": [
            {
              "type": "userTask",
              "id": "cs_task8",
              "label": "Solicitar Complemento"
            }
          ],
          "next": "cs_task4"
        }
      ]
    }
  ]
}
    """

    test = BpmnXmlGenerator()
    bpmn_xml = test.create_bpmn_xml(load_process(process))
    print("--- XML gerado ---")
    print(bpmn_xml)

    print("\n--- XML com layout aplicado ---")
    layouted_xml = apply_layout(bpmn_xml, LAYOUT_JS_PATH)
    print(
        layouted_xml
    )  # Por enquanto só imprimindo na tela, daqui pode manipular de outras formas :)
