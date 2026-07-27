import os

import chainlit as cl

from document_processor import DocumentProcessor
from database import Database
from config import Config
from utils import LLMHelper


db = Database()


# Sincronizza i documenti all'avvio
added, updated, removed = DocumentProcessor.process_documents(db)

print(
    f"Document sync complete: "
    f"{added} added, "
    f"{updated} updated, "
    f"{removed} removed"
)


@cl.action_callback("db_stats")
async def on_db_stats(action: cl.Action):
    print(action.payload)

    db_info = db.get_stats()
    print(db_info)

    response = await LLMHelper.get_db_stats(db_info)

    await cl.Message(
        content=response
    ).send()


@cl.action_callback("db_reindex")
async def on_db_reindex(action: cl.Action):
    added, updated, removed = DocumentProcessor.process_documents(db)

    message = (
        "DB reindicizzato con successo. "
        f"Document sync complete: "
        f"{added} added, "
        f"{updated} updated, "
        f"{removed} removed"
    )

    await cl.Message(
        content=message
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
                "content": """
Sei un assistente specializzato nel mondo HR,
rispondi in modo professionale, sintetico e pragmatico.

Il tuo ruolo è individuare il candidato ideale
rispetto alle richieste dell'utente.
""",
            }
        ],
    )


@cl.on_message
async def handle_message(message: cl.Message):
    user_question = message.content

    results = db.query(user_question)

    filename = results["metadatas"][0][0]["source"]

    context_lines = DocumentProcessor.read_first_lines(
        os.path.join(
            Config.DOCUMENTS_DIR,
            filename,
        ),
        200,
    )

    context = (
        "CONTESTO: "
        f"nome file {results['metadatas'][0][0]['source']} "
        "ecco il paragrafo più significativo: "
        f"{results['documents'][0][0]}"
    )

    candidate_name = await LLMHelper.get_candidate_name(
        context_lines
    )

    prompt = LLMHelper.create_prompt(
        context,
        user_question,
        candidate_name,
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

    try:
        stream = LLMHelper.chat(messages)

        for chunk in stream:
            await response_message.stream_token(
                str(
                    chunk.choices[0].delta.content
                    or ""
                )
            )

        messages.append(
            {
                "role": "assistant",
                "content": response_message.content,
            }
        )

        await response_message.update()

    except Exception as e:
        error_message = (
            f"An error occurred: {str(e)}"
        )

        await cl.Message(
            content=error_message
        ).send()

        print(error_message)

    cl.user_session.set(
        "messages",
        messages,
    )


# @cl.on_chat_end
# def end():
#     cl.Message(
#         content=(
#             "Grazie per aver utilizzato il nostro assistente. "
#             "Buona giornata!"
#         )
#     ).send()