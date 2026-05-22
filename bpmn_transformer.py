from typing import Optional

'''
O foco dessa classe é criar e separar, de maneira clara, os elementos e fluxos da modelagem BPMN, onde vamos separar o JSON-BPMN em duas partes
 Elements: Elementos da linguagem BPMN
 Flows: Como vão ser ligados os elementos nessa modelagem BPMN (vulgo as setas)

 Resultado: Um JSON Object --> Dicionário
'''
class BpmnTransformer:

    def __init__(self):
        '''
        Um elemento vai ser definido em cerca desse modelo JSON:
            {
                "id": "element_id",                     // id do elemento
                "type": "element_type",                 // tipo do elemento
                "label": "element_label",               // descrição do elemento
                "lane": "element_lane",                 // Em qual lane se posiciona o elemento
                "incoming": ["incoming_flow_id"],       // fluxo que está "entrando no elemento" Ex: 'cs_gateway1-cs_task1a'
                "outgoing": ["outgoing_flow_id"]        // fluxo que está "saíndo do elemento" Ex: 'cs_start-cs_gateway1'
            }
        '''
        self.elements: list[dict] = []

        '''
        Um flow vai ser definido em cerca desse modelo JSON:
            {
                "id": "flow_id",                        // id do flow
                "sourceRef": "source_element_id",       // id do elemento de origem
                "targetRef": "target_element_id",       // id do elemento "alvo"
                "condition": "flow_condition"           // qual a condição para esse flow acontecer
            }
        '''
        self.flows: list[dict] = []

    def transform(self, process: list[dict], next_id: Optional[str] = None) -> dict:
        # Retorna um JSON que possua os elementos e seus respectivos flows ("flechas")
        self.elements = []
        self.flows = []
        self.process(process, next_id)
        self.attach_incoming_outgoing()
        return {"elements": self.elements, "flows": self.flows}

    def process(self, process: list[dict], next_id: Optional[str] = None) -> None:
        
        first_non_start_id = next(
        (el["id"] for el in process if el["type"] != "startEvent"), next_id
        )

        for index, element in enumerate(process):
            # Identificar qual vai ser o próximo elemento para construção dos flows
            successor_id = (
                process[index + 1]["id"] if index < len(process) - 1 else next_id  # Caso seja uma chamada recursiva. Ex: Handlers
            )

            # Itens padrões de qualquer elemento
            self.elements.append({
                "id": element["id"],
                "type": element["type"],
                "label": element.get("label"),
                "lane": element.get("lane"),
                "default_flow": None
            })

            element_type = element["type"]

            # Tipos específicos de elementos que devemos ter um pouco mais de cuidado
            if element_type == "exclusiveGateway":
                join_id = self.handle_split_gateway(element, successor_id, element_type)
            elif element_type == "parallelGateway":
                join_id = self.handle_parallel_gateway(element)
            elif element_type == "inclusiveGateway":
                join_id = self.handle_split_gateway(element, successor_id, element_type)
            elif element_type == "startEvent":
                join_id = self.add_flow(element["id"], first_non_start_id)
            else:
                join_id = None

            if join_id and successor_id:
                self.add_flow(join_id, successor_id)
            elif successor_id and element_type not in (
                "endEvent", "exclusiveGateway", "parallelGateway", "inclusiveGateway", "startEvent"
            ):
                self.add_flow(element["id"], successor_id)

    def handle_split_gateway(
        self,
        element: dict,
        next_id: Optional[str],
        element_type: str,
    ) -> Optional[str]:
        '''
        Trata exclusiveGateway e inclusiveGateway (mesma lógica estrutural).

        Caso o gateway possua outro gateway para juntar os ramos,
        então criamos outro elemento no JSON para a criação dele no BPMN, de acordo com "has_join".
        '''
        join_id = None
        default_flow_id = None

        if element.get("has_join"):
            join_id = f"{element['id']}-join"
            self.elements.append({"id": join_id, "type": element_type, "label": None, "lane": element.get("lane")})

        # Visto que um gateway possuí elementos dentro dele (no caso seriam os ramos), vamos percorrer por eles para identificar todos
        for branch in element["branches"]:
            is_default = branch.get("is_default", False)
            condition = branch.get("condition")
            branch_next = branch.get("next")
            # or == A or B com prioridade no A
            fallback_id = branch_next or join_id or next_id

            '''
            Caso o ramo não possua um caminho, ele analisa o trajeto para construir o fluxo de primeira

            Ex: quando algum ramo não possua tasks intermediárias, ele não precisa construir um "path"
            '''
            if not branch.get("path"):
                target = branch.get("next") or join_id or next_id

                if target is None:
                    raise ValueError(f"Branch sem destino no gateway {element['id']}")

                flow_id = f"{element['id']}-{target}"
                self.add_flow(element["id"], target, flow_id=flow_id, condition=condition)

                if is_default:
                    default_flow_id = flow_id

                continue

            # Caso ele tenha path, vamos passar por todos os caminhos para enumerar os elementos
            sub = BpmnTransformer()
            sub.process(branch["path"], fallback_id)
            sub.attach_incoming_outgoing()

            self.elements.extend(sub.elements)
            self.flows.extend(sub.flows)

            first = sub.elements[0] if sub.elements else None
            if first:
                flow_id = f"{element['id']}-{first['id']}"
                self.add_flow(element["id"], first["id"], flow_id=flow_id, condition=condition)
                if is_default:
                    default_flow_id = flow_id

        if default_flow_id:
            for elem in self.elements:
                if elem["id"] == element["id"]:
                    elem["default_flow"] = default_flow_id
                    break

        return join_id

    def handle_parallel_gateway(self, element: dict) -> str:
        '''
        No caso do gateway paralelo, é obrigatório que ele tenha um "join gateway"
        então não precisaremos da verificação dele
        '''
        join_id = f"{element['id']}-join"
        self.elements.append({"id": join_id, "type": "parallelGateway", "label": None, "lane": element.get("lane")})

        # Um gateway paralelo nunca vai ser vazio, então não precisamos conferir
        for branch in element["branches"]:
            sub = BpmnTransformer()
            sub.process(branch, join_id)
            sub.attach_incoming_outgoing()

            self.elements.extend(sub.elements)
            self.flows.extend(sub.flows)

            if sub.elements:
                self.add_flow(element["id"], sub.elements[0]["id"])
                # self.add_flow(sub.elements[-1]["id"], join_id) o add_flow tem o guard de duplicata, então não quebra, mas o fluxo correto já vem do sub.process, então da pra remover essa linha com segurança

        return join_id

    def add_flow(
        self,
        source: str,
        target: str,
        flow_id: Optional[str] = None,
        condition: Optional[str] = None,
    ) -> None:
        # Caso já exista alguma seta com esse caminho específico, não precisa refazer o trabalho.
        if any(f["sourceRef"] == source and f["targetRef"] == target for f in self.flows):
            return
            
        self.flows.append({
            "id": flow_id or f"{source}-{target}",
            "sourceRef": source,
            "targetRef": target,
            "condition": condition,
        })

    def attach_incoming_outgoing(self) -> None:
        for element in self.elements:
            eid = element["id"]
            # Para achar a seta que está entrando, precisamos verificar se o ALVO é realmente esse elemento
            element["incoming"] = [f["id"] for f in self.flows if f["targetRef"] == eid]
            # Para achar a seta que está saindo, precisamos verificar se a ORIGEM é realmente esse elemento
            element["outgoing"] = [f["id"] for f in self.flows if f["sourceRef"] == eid]
