import os
from openai import AzureOpenAI
from dotenv import load_dotenv

# Configurações básicas
load_dotenv()
EXPLANATION_PATH = "./utils/prompts/bpmn-explanations.txt"
EXAMPLE_PATH = "./utils/prompts/bpmn-examples.txt"

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),
    api_key=os.getenv("API_KEY"),
    api_version=os.getenv("API_VERSION"),
)

with open(EXPLANATION_PATH, "r", encoding="utf-8") as f:
    explanation_prompt = f.read()

with open(EXAMPLE_PATH, "r", encoding="utf-8") as f:
    example_prompt = f.read()

def get_chat_completion(prompt: str):
    try:
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