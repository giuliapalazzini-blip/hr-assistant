import chainlit as cl

from config import Config
from database import Database
from document_processor import DocumentProcessor
from utils import LLMHelper


db = Database()

added, updated, removed = DocumentProcessor.process_documents(db)

print(f"Documenti aggiunti: {added}")
print(f"Documenti aggiornati: {updated}")
print(f"Documenti eliminati: {removed}")


@cl.on_chat_start
async def on_chat_start():
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

    await cl.Message(
        content=(
            "Ciao! Sono il tuo HR Assistant.\n\n"
            f"Documenti aggiunti: {added}\n"
            f"Documenti aggiornati: {updated}\n"
            f"Documenti eliminati: {removed}"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    try:
        results = db.query(
            query_text=message.content,
            n_results=1,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not documents:
            await cl.Message(
                content="Non ho trovato curriculum adatti alla richiesta."
            ).send()
            return

        context = documents[0]

        source = "file sconosciuto"

        if metadatas and metadatas[0]:
            source = metadatas[0].get("source", source)

        candidate_name = await LLMHelper.get_candidate_name(context)

        prompt = LLMHelper.create_prompt(
            context=context,
            question=message.content,
            candidate_name=candidate_name,
        )

        messages = cl.user_session.get("messages", [])

        messages.append(
            {
                "role": "user",
                "content": (
                    f"Nome del file individuato: {source}\n\n"
                    f"{prompt}"
                ),
            }
        )

        response = LLMHelper.chat(messages)

        answer = cl.Message(content="")

        await answer.send()

        complete_response = ""

        for chunk in response:
            content = chunk.choices[0].delta.content

            if content:
                complete_response += content
                await answer.stream_token(content)

        await answer.update()

        messages.append(
            {
                "role": "assistant",
                "content": complete_response,
            }
        )

        cl.user_session.set("messages", messages)

    except Exception as error:
        print(f"Errore: {error}")

        await cl.Message(
            content=f"Si è verificato un errore: {error}"
        ).send()