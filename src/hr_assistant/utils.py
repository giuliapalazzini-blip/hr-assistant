from openai import OpenAI
from config import Config


client = OpenAI(
    base_url=Config.AI_API_URL,
    api_key=Config.AI_API_KEY,
)
class LLMHelper:
    @staticmethod
    def chat(messages):
        return client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=messages,
            stream=True,
        )
    @staticmethod
    async def get_candidate_name(context):
        response = client.chat.completions.create(
            model=Config.LLM_MODEL_LOW,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Dato il seguente curriculum, individua "
                        "il nome e il cognome del candidato. "
                        "Restituisci esclusivamente il nome e "
                        "il cognome.\n\n"
                        f"Curriculum:\n{context}"
                    ),
                }
            ],
        )

        return response.choices[0].message.content

    @staticmethod
    async def get_db_stats(context):
        response = client.chat.completions.create(
            model=Config.LLM_MODEL_LOW,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Descrivi in modo sintetico e chiaro "
                        "le statistiche del database dei curriculum. "
                        "Utilizza esclusivamente i dati seguenti:\n\n"
                        f"{context}"
                    ),
                }
            ],
        )

        return response.choices[0].message.content

    @staticmethod
    def create_prompt(context, question):
        return f"""
Dato il seguente contesto:

[[[
{context}
]]]

Rispondi alla domanda dell'utente:

[[[
{question}
]]]

Indica quale candidato risulta più adatto.

Argomenta la scelta utilizzando esclusivamente le informazioni
presenti nel contesto.

Alla fine crea una sezione "Contatti del candidato" indicando:
- nome e cognome;
- email;
- numero di telefono.

Dopo la sezione dei contatti indica il nome del file del curriculum.
Non nominare il file prima di questa sezione.
"""