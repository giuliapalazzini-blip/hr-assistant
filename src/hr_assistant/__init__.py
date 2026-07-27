import os
import shutil

import chainlit as cl

from document_processor import DocumentProcessor
from database import Database
from config import Config
from utils import LLMHelper


db = Database()

# Process documents
dp = DocumentProcessor()
added, updated, removed = dp.process_documents(db)

print(
    f"Document sync complete: "
    f"{added} added, {updated} updated, {removed} removed"
)


@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Ricerca candidato",
            message="Cercami un candidato che abbia le competenze di un saldatore",
            icon="/public/idea.svg",
        ),
    ]


@cl.action_callback("db_stats")
async def on_db_stats(action: cl.Action):
    actions = [
        cl.Action(
            name="db_stats",
            icon="mouse-pointer-click",
            payload={"value": "db_stats"},
            label="Ricalcola Statistiche Database",
        ),
    ]

    db_info = db.get_stats()
    response = await LLMHelper.get_db_stats(db_info)

    await cl.Message(
        content=response,
        actions=actions
    ).send()


@cl.action_callback("db_reindex")
async def on_db_reindex(action: cl.Action):
    added, updated, removed = dp.process_documents(db)

    message = (
        "DB reindicizzato con successo. "
        f"Document sync complete: {added} added, "
        f"{updated} updated, {removed} removed"
    )

    await cl.Message(content=message).send()


@cl.action_callback("db_remove")
async def on_db_remove(action: cl.Action):
    db.delete_collection()

    message = (
        "Il database è stato completamente rimosso. "
        "È necessario lanciare il reindex."
    )

    await cl.Message(content=message).send()


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
            name="db_remove",
            icon="mouse-pointer-click",
            payload={"value": "db_remove"},
            label="Svuota completamente il Database",
        ),
    ]

    await cl.Message(
        content="Informazioni del sistema:",
        actions=actions
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


async def _process_and_index_file(
    file_path: str,
    file_name: str
) -> str:
    """
    Elabora e indicizza il documento,
    restituendo un messaggio di esito.
    """

    documents, metadatas, ids = dp.process_single_document(file_path)

    if documents:
        db.add_documents(documents, metadatas, ids)

        return (
            f"File '{file_name}' caricato "
            "e indicizzato con successo."
        )

    return f"Errore nel processare il file '{file_name}'."


async def _file_upload(file) -> str:
    file_name = file.name
    src_file_path = file.path

    dst_file_path = os.path.join(
        Config.DOCUMENTS_DIR,
        file_name
    )

    os.makedirs(
        Config.DOCUMENTS_DIR,
        exist_ok=True
    )

    shutil.move(
        src_file_path,
        dst_file_path
    )

    return await _process_and_index_file(
        dst_file_path,
        file_name
    )


@cl.on_message
async def handle_message(message: cl.Message):

    # Gestione dell'upload dei file
    if message.elements:
        print("message.elements", message.elements)

        await cl.Message(
            content="Caricamento e indicizzazione documenti"
        ).send()

        files = [
            file
            for file in message.elements
            if file.name.lower().endswith(
                tuple(DocumentProcessor.SUPPORTED_EXTENSIONS)
            )
        ]

        if files:
            results_upload = [
                await _file_upload(file)
                for file in files
            ]
        else:
            results_upload = [
                "Nessun file supportato caricato"
            ]

        result_message = "\n".join(results_upload)

        await cl.Message(
            content=result_message
        ).send()

        await cl.Message(
            content=f"Caricati {len(files)} file"
        ).send()

        # Se il messaggio non contiene una domanda,
        # termina dopo il caricamento dei file
        if not message.content.strip():
            return

    # Interrogazione del sistema
    user_question = message.content.strip()

    if not user_question:
        return

    results = db.query(user_question)

    print("results", results)

    try:
        filename = results["metadatas"][0][0]["source"]
        significant_paragraph = results["documents"][0][0]

    except Exception as error:
        error_message = (
            "Non sono riuscito a trovare un curriculum "
            f"corrispondente alla richiesta. Dettaglio: {error}"
        )

        await cl.Message(
            content=error_message
        ).send()

        print(error_message)
        return

    context_lines = DocumentProcessor.read_first_lines(
        os.path.join(
            Config.DOCUMENTS_DIR,
            filename
        ),
        200
    )

    context = (
        f"CONTESTO: nome file {filename}. "
        "Ecco il paragrafo più significativo: "
        f"{significant_paragraph}"
    )

    candidate_name = await LLMHelper.get_candidate_name(
        context_lines
    )

    prompt = LLMHelper.create_prompt(
        context,
        user_question,
        candidate_name
    )

    messages = cl.user_session.get(
        "messages",
        []
    )

    messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    response_message = cl.Message(content="")
    await response_message.send()

    try:
        stream = LLMHelper.chat(messages)

        for chunk in stream:
            token = str(
                chunk.choices[0].delta.content or ""
            )

            await response_message.stream_token(token)

        messages.append(
            {
                "role": "assistant",
                "content": response_message.content
            }
        )

        await response_message.update()

    except Exception as error:
        error_message = (
            f"Si è verificato un errore: {error}"
        )

        await cl.Message(
            content=error_message
        ).send()

        print(error_message)

    cl.user_session.set(
        "messages",
        messages
    )


# @cl.on_chat_end
# async def end():
#     await cl.Message(
#         content=(
#             "Grazie per aver utilizzato "
#             "il nostro assistente. Buona giornata!"
#         )
#     ).send()