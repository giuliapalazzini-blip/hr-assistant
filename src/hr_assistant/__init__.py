import os

import chainlit as cl

from config import Config
from database import Database
from document_processor import DocumentProcessor
from utils import LLMHelper


db = Database()


added, updated, removed = (
    DocumentProcessor.process_documents(db)
)

print(
    "Document sync complete: "
    f"{added} added, "
    f"{updated} updated, "
    f"{removed} removed"
)

@cl.action_callback("db_stats")
async def show_db_stats(action: cl.Action):
    db_info = db.get_stats()

    response = await LLMHelper.get_db_stats(db_info)

    await cl.Message(
        content=response
    ).send()

@cl.action_callback("db_reindex")
async def reindex_database(action: cl.Action):
    added, updated, removed = (
        DocumentProcessor.process_documents(db)
    )

    message = (
        "DB reindicizzato con successo.\n\n"
        f"Documenti aggiunti: {added}\n"
        f"Documenti aggiornati: {updated}\n"
        f"Documenti eliminati: {removed}"
    )

    await cl.Message(
        content=message
    ).send()


@cl.action_callback("say_hello")
async def say_hello(action: cl.Action):
    value = action.payload["value"]

    await cl.Message(
        content=f"Hello {value}"
    ).send()


@cl.on_chat_start
async def start():
    actions = [
        cl.Action(
            name="db_stats",
            icon="mouse-pointer-click",
            payload={"value": "db_stats"},
            label="Statistiche Database",
        ),
        cl.Action(
            name="db_reindex",
            icon="mouse-pointer-click",
            payload={"value": "db_reindex"},
            label="Reindex Database",
        ),
        cl.Action(
            name="say_hello",
            icon="message-circle",
            payload={"value": "Mondo"},
            label="Ciao Mondo",
        ),
    ]

    await cl.Message(
        content="Informazioni del sistema:",
        actions=actions,
    ).send()

    cl.user_session.set(
        "messages",
        [
            {
                "role": "system",
                "content": (
                    "Sei un assistente specializzato nel mondo HR. "
                    "Rispondi in modo professionale, sintetico "
                    "e pragmatico. Il tuo ruolo è individuare "
                    "il candidato ideale rispetto alle richieste "
                    "dell'utente. Usa esclusivamente le informazioni "
                    "presenti nei curriculum e non inventare dati."
                ),
            }
        ],
    )


@cl.on_message
async def handle_message(message: cl.Message):
    try:
        user_question = message.content

        numero_frammenti = db.collection.count()

        if numero_frammenti == 0:
            await cl.Message(
                content=(
                    "Il database non contiene curriculum. "
                    "Aggiungi almeno un file nella cartella resumes."
                )
            ).send()
            return

        n_results = min(3, numero_frammenti)

        results = db.query(
            user_question,
            n_results,
        )

        print("RESULT DB:", results)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not documents or not metadatas:
            await cl.Message(
                content=(
                    "Non ho trovato un curriculum adatto "
                    "alla richiesta."
                )
            ).send()
            return

        filename = metadatas[0]["source"]

        file_path = os.path.join(
            Config.DOCUMENTS_DIR,
            filename,
        )

        candidate_info = (
            DocumentProcessor.read_first_lines(
                file_path,
                10,
            )
        )

        context = (
            f"Nome del file: {filename}\n\n"
            "Paragrafo più significativo:\n"
            f"{documents[0]}\n\n"
            "Informazioni iniziali del candidato:\n"
            f"{candidate_info}"
        )

        prompt = LLMHelper.create_prompt(
            context,
            user_question,
        )

        messages = cl.user_session.get(
            "messages",
            [],
        )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        response_message = cl.Message(content="")
        await response_message.send()

        stream = LLMHelper.chat(messages)

        complete_response = ""

        for chunk in stream:
            token = (
                chunk.choices[0].delta.content
                or ""
            )

            if token:
                complete_response += token

                await response_message.stream_token(
                    token
                )

        await response_message.update()

        messages.append(
            {
                "role": "assistant",
                "content": complete_response,
            }
        )

        cl.user_session.set(
            "messages",
            messages,
        )

    except Exception as error:
        error_message = (
            "Si è verificato un errore: "
            f"{str(error)}"
        )

        print(error_message)

        await cl.Message(
            content=error_message
        ).send()