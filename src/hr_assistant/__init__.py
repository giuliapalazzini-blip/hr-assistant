import os
from pathlib import Path

import chainlit as cl
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "La variabile OPENAI_API_KEY non è stata trovata nel file .env"
    )

openai_client = OpenAI(api_key=api_key)

BASE_DIR = Path(__file__).resolve().parents[2]
RESUMES_DIR = BASE_DIR / "resumes"
CHROMA_DIR = BASE_DIR / "chroma_db"


def leggi_curriculum():
    curriculum = []

    if not RESUMES_DIR.exists():
        print("La cartella resumes non esiste.")
        return curriculum

    for file_path in RESUMES_DIR.glob("*.txt"):
        contenuto = file_path.read_text(encoding="utf-8")

        curriculum.append(
            {
                "nome_file": file_path.name,
                "contenuto": contenuto,
            }
        )

    return curriculum

embedding_function = OpenAIEmbeddingFunction(
    api_key=api_key,
    model_name="text-embedding-3-small",
)

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

collection = chroma_client.get_or_create_collection(
    name="curriculum",
    embedding_function=embedding_function,
)


def salva_curriculum_in_chroma(curriculum):
    for cv in curriculum:
        collection.upsert(
            ids=[cv["nome_file"]],
            documents=[cv["contenuto"]],
            metadatas=[
                {
                    "nome_file": cv["nome_file"],
                }
            ],
        )


@cl.on_chat_start
async def on_chat_start():
    curriculum = leggi_curriculum()

    salva_curriculum_in_chroma(curriculum)

    print(f"Curriculum letti: {len(curriculum)}")
    print(f"Curriculum presenti in ChromaDB: {collection.count()}")

    await cl.Message(
        content=(
            "👋 Ciao! Sono il tuo HR Assistant.\n\n"
            f"Ho caricato {collection.count()} curriculum.\n\n"
            "Puoi chiedermi, per esempio:\n"
            "“Quale candidato conosce Python?”"
        )
    ).send()


@cl.on_chat_start
async def on_chat_start():
    curriculum = leggi_curriculum()
    salva_curriculum_in_chroma(curriculum)

    cl.user_session.set(
        "messages",
        [
            {
                "role": "system",
                "content": (
                    "Sei un assistente specializzato nel mondo HR. "
                    "Rispondi in modo professionale, sintetico e pragmatico. "
                    "Usa esclusivamente le informazioni presenti nei curriculum. "
                    "Non inventare competenze, esperienze o titoli di studio."
                ),
            }
        ],
    )

    print(f"Curriculum letti: {len(curriculum)}")
    print(f"Curriculum presenti in ChromaDB: {collection.count()}")

    await cl.Message(
        content=(
            "Ciao! Sono il tuo HR Assistant.\n\n"
            f"Ho caricato {collection.count()} curriculum."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    try:
        numero_curriculum = collection.count()

        if numero_curriculum == 0:
            await cl.Message(
                content="Non ci sono curriculum disponibili."
            ).send()
            return

        risultati = collection.query(
            query_texts=[message.content],
            n_results=numero_curriculum,
        )

        documenti = risultati.get("documents", [[]])[0]
        metadati = risultati.get("metadatas", [[]])[0]

        curriculum_per_prompt = []

        for indice, documento in enumerate(documenti):
            nome_file = "Curriculum sconosciuto"

            if indice < len(metadati) and metadati[indice]:
                nome_file = metadati[indice].get(
                    "nome_file",
                    nome_file,
                )

            curriculum_per_prompt.append(
                f"""
CANDIDATO {indice + 1}
File: {nome_file}

{documento}
"""
            )

        testo_curriculum = "\n".join(curriculum_per_prompt)

        prompt = f"""
Domanda dell'utente:
{message.content}

CURRICULUM DISPONIBILI:
{testo_curriculum}
"""

        messages = cl.user_session.get("messages", [])

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        response = openai_client.responses.create(
            model="gpt-4.1-mini",
            input=messages,
        )

        risposta = response.output_text

        messages.append(
            {
                "role": "assistant",
                "content": risposta,
            }
        )

        cl.user_session.set("messages", messages)

        await cl.Message(
            content=risposta
        ).send()

    except Exception as error:
        print(f"Errore: {error}")

        await cl.Message(
            content=f"Si è verificato un errore: {error}"
        ).send()