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

## Banco de dados (SQL Server 16 via Docker)

Este repositório inclui um `docker-compose.yml` que sobe um container com **SQL Server 2022 (v16)**.

### Requisitos

- Docker + Docker Compose
- ODBC Driver 18 for SQL Server (para conexao via `pyodbc`)

### Subir o SQL Server

1. Renomeie `.env.example` para `.env` (se ainda não fez).
2. Ajuste a variável `MSSQL_SA_PASSWORD` no `.env`.
3. Suba o serviço:

```bash
docker compose up -d
```

### Conexão

- Host: `localhost`
- Porta: `1433`
- Usuário: `sa`
- Senha: valor de `MSSQL_SA_PASSWORD`

## Cadastro e Login (GUI)

O aplicativo agora abre uma tela de login antes do gerador BPMN. O cadastro envia uma OTP (6 digitos) por email. A OTP expira conforme configuracao no `.env` e deve ser usada para definir a primeira senha. O login só e liberado apos a troca de senha.

### Configuracao no .env

- `DB_*`: dados de conexao do SQL Server (o banco `DB_NAME` é criado automaticamente se nao existir).
- `OTP_EXPIRATION_MINUTES`: expiracao da OTP.
- `TEMP_PASSWORD_LENGTH`: tamanho da senha temporaria (gerada e armazenada, nao enviada).
- `SMTP_*`: servidor de email para envio da OTP.

Fluxo resumido:

1. Clique em **Cadastrar** e informe o email.
2. Verifique o email para obter a OTP.
3. Use **Alterar senha** para definir uma nova senha com a OTP.
4. Entre com email e senha atual (login liberado após a troca).

### Parar e remover

```bash
docker compose down
```

## Executando o Projeto

Para executar o projeto, utilize o script principal `bpmn_parser.py`:

```bash
python bpmn_parser.py
```

O script `bpmn_parser.py` é o ponto de entrada para o fluxo de trabalho de experimentação. Ele realiza as seguintes etapas principais:

1.  Utiliza o módulo `gpt_chat_completion.py` em conjunto com os prompts da pasta `utils/prompts/` para ensinar a IA como passar a tabela de narrativas de processos trabalhada em BPMN-JSON.
2.  Utiliza o módulo `bpmn_transformer.py` para transformar o BPMN-JSON em elementos (elements) e fluxos (flows), para melhor configuração do arquivo final.
3.  Se conecta com o módulo de auto-layout em `auto-layout-process/layout.js` para organizar e renderizar o diagrama BPMN no espaço.
4.  Armazena o resultado em `output/arquivo.bpmn`

A pasta `utils/` fornece funções auxiliares utilizadas pelos demais scripts.

### Execução com Interface Gráfica (GUI)

Também é possível usar uma interface gráfica para selecionar o arquivo de entrada e escolher onde salvar o resultado final `.bpmn`:

```bash
python bpmn_gui.py
```

Fluxo da GUI:

1. Seleciona um arquivo de entrada (`.txt`, `.json`, `.md`, `.docx`, `.xlsx`).
2. Processa o conteúdo com IA e transforma em BPMN.
3. Aplica auto-layout via `auto-layout-process/layout.js`.
4. Salva o arquivo `.bpmn` no local escolhido.

## Gerando executável `.exe` da GUI (Windows)

Para empacotar a interface gráfica em um executável, use o PyInstaller com `bpmn_gui.py` como ponto de entrada.

### 1. Pré-requisitos

- Ambiente virtual Python ativado.
- Dependências Python instaladas (`requirements.txt`).
- Node.js instalado.
- Dependências do layout instaladas:

```bash
cd auto-layout-process
npm install
cd ..
```

### 2. Instalar PyInstaller

```bash
pip install pyinstaller
```

### 3. Gerar o executável da GUI

No diretório raiz do projeto, execute:

```bash
pyinstaller --noconfirm --windowed --onedir --name BPMNGen ^
  --add-data ".env;." ^
  --add-data "utils/prompts;utils/prompts" ^
  --add-data "auto-layout-process;auto-layout-process" ^
  bpmn_gui.py
```

Saída esperada:

- Executável em `dist/BPMNGen/BPMNGen.exe`

### 4. Arquivos necessários junto ao `.exe`

- O `.env` ja fica empacotado pelo comando acima (`--add-data ".env;."`).
- Opcionalmente, voce pode manter um `.env` ao lado do `.exe` para sobrescrever variaveis sem recompilar.
- Pasta `auto-layout-process` (incluindo `node_modules`, quando necessario).

Observação: a aplicação chama o comando `node` em runtime para aplicar auto-layout. Por isso, a máquina que executa o `.exe` precisa ter Node.js disponível no `PATH`.

## Observações

- Certifique-se de que o Python e o pip estão atualizados.
- Sempre ative o ambiente virtual antes de executar os scripts do projeto.
