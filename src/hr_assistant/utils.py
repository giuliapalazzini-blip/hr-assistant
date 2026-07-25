from config import Config
from openai import OpenAI


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
                    "content": f"""
Dato il seguente contesto, individua il nome e il cognome del candidato
e restituisci soltanto il nome e il cognome.

Il testo che sto per fornirti è il curriculum vitae del candidato:

{context}
""",
                }
            ],
        )

        return response.choices[0].message.content

    @staticmethod
    def create_prompt(context, question, candidate_name):
        return f"""
Dato il seguente contesto:

[[[
{context}
]]]

Rispondi alla domanda dell'utente:

[[[
{question}
]]]

Spiega che nel file individuato è presente il profilo più adatto.
Assicurati di nominare il file.
Assicurati di indicare il nome del candidato:

[[[
{candidate_name}
]]]

Argomenta la scelta utilizzando il contenuto del testo individuato nel contesto.
"""