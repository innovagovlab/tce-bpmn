# Projeto Gerador BPMN

Esse projeto utiliza Python e JavaScript para realizar diagramas BPMN, com o auxílio de IA na confecção dos mesmos.

## Estrutura do Projeto

```bash
│   bpmn_parser.py                     # Transforma o BPMN-JSON em arquivo `.bpmn`. 
│   bpmn_transformer.py                # Transforma a resposta da IA em BPMN-JSON.
│   gpt_chat_completion.py             # Script Python para a conexão com a API da OpenAzureAI
│   requirements.txt                   # Lista de dependências do projeto.
├───auto-layout-process                # Contém os arquivos principais para renderizar o processo no espaço.
│   ├───layout.js                      # Script em JavaScript para configuração do diagrama no espaço.
│   └───*.json                         # Arquivos de configuração do Node.js.
├───utils                              # Contém arquivos com funções úteis para o funcionamento do sistema.
│   └───prompts                        # Pasta de prompts utilizados.
│       └───*.txt                      # Arquivos de texto com os prompts.
└───output                             # Contém os resultados gerados pelo processo de geração de diagramas BPMN.
    └───arquivo.bpmn                   # Arquivo BPMN gerado pelo processo.
```

## Configuração do Ambiente

Siga os passos abaixo para configurar o ambiente virtual Python e instalar as dependências necessárias:

### Requisitos

- Python 3.14.0^

### 1. Criar o Ambiente Virtual

1. Certifique-se de que o Python está instalado em sua máquina. Recomendamos a versão 3.8 ou superior.
2. No terminal, navegue até a pasta do projeto:
   ```bash
   cd bpmn-automatized
   ```
3. Crie o ambiente virtual:
   ```bash
   python -m venv venv
   ```

### 2. Ativar o Ambiente Virtual

- **Windows**:
  ```bash
  venv\Scripts\activate
  ```
- **Linux/Mac**:
  ```bash
  source venv/bin/activate
  ```

### 3. Instalar Dependências

Com o ambiente virtual ativado, instale as dependências listadas no arquivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente

Renomeie o arquivo `.env.example` para `.env`.
Certifique-se de que o arquivo `.env` está configurado corretamente com as variáveis de ambiente necessárias, como `API_KEY` e `AZURE_ENDPOINT`.

## Executando o Projeto

Para executar o projeto, utilize o script principal `bpmn_parser.py`:

```bash
python main.py
```

O script `bpmn_parser.py` é o ponto de entrada para o fluxo de trabalho de experimentação. Ele realiza as seguintes etapas principais:

1.  Utiliza o módulo `gpt_chat_completion.py` em conjunto com os prompts da pasta `utils/prompts/` para ensinar a IA como passar a tabela de narrativas de processos trabalhada em BPMN-JSON.
2.  Utiliza o módulo `bpmn_transformer.py` para transformar o BPMN-JSON em elementos (elements) e fluxos (flows), para melhor configuração do arquivo final.
2.  Se conecta com o módulo de auto-layout em `auto-layout-process/layout.js` para organizar e renderizar o diagrama BPMN no espaço.
3.  Armazena o resultado em `output/arquivo.bpmn`

A pasta `utils/` fornece funções auxiliares utilizadas pelos demais scripts.

## Observações

- Certifique-se de que o Python e o pip estão atualizados.
- Sempre ative o ambiente virtual antes de executar os scripts do projeto.
