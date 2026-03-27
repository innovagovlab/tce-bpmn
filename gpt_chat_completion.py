import os
import sys
from pathlib import Path
from openai import AzureOpenAI
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


_load_env_files()
EXPLANATION_PATH = _BUNDLE_BASE_PATH / "utils" / "prompts" / "bpmn-explanations.txt"
EXAMPLE_PATH = _BUNDLE_BASE_PATH / "utils" / "prompts" / "bpmn-examples.txt"

with open(EXPLANATION_PATH, "r", encoding="utf-8") as f:
    explanation_prompt = f.read()

with open(EXAMPLE_PATH, "r", encoding="utf-8") as f:
    example_prompt = f.read()


def get_chat_completion(prompt: str):
    try:
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

        response = client.chat.completions.create(
            model=os.getenv("DEPLOYMENT_NAME"),  # model = "deployment_name"
            messages=[
                {
                    "role": "user",
                    "content": explanation_prompt,
                },
                {
                    "role": "user",
                    "content": example_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        return response.choices[0].message.content
    except Exception as e:
        print("Erro ao buscar resposta de IA: ", e)
        raise
