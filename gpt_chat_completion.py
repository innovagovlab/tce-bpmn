import os
import json
import re
import sys
import time
from pathlib import Path
from openai import AzureOpenAI, RateLimitError
from dotenv import load_dotenv


# Configurações básicas
def _bundle_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


def _app_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


_BUNDLE_BASE_PATH = _bundle_base_path()
_APP_BASE_PATH = _app_base_path()


def _load_env_files() -> None:
    # Prioriza .env ao lado do executavel (ou raiz do projeto) e faz fallback
    # para o bundle do PyInstaller quando empacotado com --add-data.
    candidates = [
        _APP_BASE_PATH / ".env",
        _BUNDLE_BASE_PATH / ".env",
        _BUNDLE_BASE_PATH / "_internal" / ".env",
    ]
    for env_path in candidates:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)


def _get_env(name: str, *aliases: str) -> str | None:
    for key in (name, *aliases):
        value = os.getenv(key)
        if value:
            return value
    return None


def _get_retries_from_env(default: int = 3) -> int:
    raw = _get_env("CHAT_COMPLETION_RETRIES", "OPENAI_RETRIES", "AZURE_OPENAI_RETRIES")
    if not raw:
        return default

    try:
        parsed = int(raw)
        if parsed < 1:
            return default
        return parsed
    except ValueError:
        return default


_load_env_files()
EXPLANATION_PATH = _BUNDLE_BASE_PATH / "utils" / "prompts" / "bpmn-explanations.txt"
EXAMPLE_PATH = _BUNDLE_BASE_PATH / "utils" / "prompts" / "bpmn-examples.txt"

with open(EXPLANATION_PATH, "r", encoding="utf-8") as f:
    explanation_prompt = f.read()

with open(EXAMPLE_PATH, "r", encoding="utf-8") as f:
    example_prompt = f.read()


PROCESS_JSON_SCHEMA = {
    "name": "bpmn_process_response",
    "strict": False,
    "schema": {
        "type": "object",
        "properties": {
            "process": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": [
                                "startEvent",
                                "endEvent",
                                "task",
                                "userTask",
                                "serviceTask",
                                "sendTask",
                                "receiveTask",
                                "exclusiveGateway",
                                "parallelGateway",
                                "inclusiveGateway",
                            ],
                        },
                    },
                    "required": ["id", "type"],
                },
            }
        },
        "required": ["process"],
    },
}


def get_chat_completion(prompt: str, retries: int | None = None) -> dict:
    retries = retries if retries is not None else _get_retries_from_env(default=3)

    api_key = _get_env("API_KEY", "AZURE_OPENAI_API_KEY")
    azure_endpoint = _get_env("AZURE_ENDPOINT", "AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("API_VERSION")

    if not api_key or not azure_endpoint or not api_version:
        raise RuntimeError(
            "Credenciais Azure OpenAI ausentes. Verifique o .env com "
            "API_KEY/AZURE_OPENAI_API_KEY, AZURE_ENDPOINT/AZURE_OPENAI_ENDPOINT e API_VERSION."
        )

    client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=api_key,
        api_version=api_version,
    )

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=os.getenv("DEPLOYMENT_NAME"),  # model = "deployment_name"
                messages=[
                    {
                        "role": "system",
                        "content": explanation_prompt,
                    },
                    {
                        "role": "user",
                        "content": f"{example_prompt}\n\n---\n\nAgora processe o seguinte:\n{prompt}",
                    },
                ],
                temperature=0.3,
                response_format={
                    "type": "json_schema",
                    "json_schema": PROCESS_JSON_SCHEMA,
                },
            )

            content = response.choices[0].message.content or ""
            clean = re.sub(r"```json|```", "", content).strip()
            return json.loads(clean)
        except RateLimitError:
            if attempt < retries - 1:
                wait_seconds = 2**attempt
                print(
                    f"Rate limit atingido. Nova tentativa {attempt + 2}/{retries} em {wait_seconds}s..."
                )
                time.sleep(wait_seconds)
            else:
                print("Erro ao buscar resposta de IA: limite de taxa excedido.")
                raise
        except Exception as e:
            print(f"Erro na tentativa {attempt + 1}: {e}")
            raise

    raise RuntimeError("Falha ao obter resposta da IA apos as tentativas configuradas.")
