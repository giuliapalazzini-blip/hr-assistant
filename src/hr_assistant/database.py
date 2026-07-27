# database.py
import chromadb
from chromadb.utils import embedding_functions

from config import Config


class Database:
    def __init__(self):
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=Config.OPENAI_KEY,
            model_name=Config.MODEL_NAME
        )

        # Inizializza il client persistente
        self.client = chromadb.PersistentClient(
            path=Config.PERSISTENT_DIR
        )

        self._init_collection()

    def _init_collection(self):
        self.collection = self.client.get_or_create_collection(
            name=Config.COLLECTION_NAME,
            embedding_function=self.openai_ef
        )

    def delete_collection(self):
        try:
            self.client.delete_collection(
                name=Config.COLLECTION_NAME
            )
        except Exception as error:
            print(
                "Errore durante l'eliminazione "
                f"della collection: {error}"
            )

        # Ricrea subito la collection vuota
        self._init_collection()

    def add_documents(self, documents, metadatas, ids):
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, query_text, n_results=1):
        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

    def get_tracked_files(self):
        """
        Restituisce tutti i file unici
        e i relativi metadati presenti nel database.
        """

        result = self.collection.get()
        tracked_files = {}

        if result and result.get("metadatas"):
            for metadata in result["metadatas"]:
                source = metadata.get("source")

                if source and source not in tracked_files:
                    tracked_files[source] = {
                        "hash": metadata.get("hash"),
                        "last_modified": metadata.get(
                            "last_modified"
                        ),
                        "source": source,
                    }

        return tracked_files

    def remove_document_by_source(self, source):
        """
        Rimuove tutti i frammenti associati
        a uno specifico file.
        """

        result = self.collection.get(
            where={"source": source}
        )

        if result and result.get("ids"):
            self.collection.delete(
                ids=result["ids"]
            )

    def get_stats(self):
        result = self.collection.get()
        metadatas = result.get("metadatas") or []

        valori_distinti = {
            metadata.get("source")
            for metadata in metadatas
            if metadata.get("source")
        }

        numero_files = len(valori_distinti)

        stats = {
            "numero_totale_documenti": self.collection.count(),
            "nome_collezione": self.collection.name,
        }

        return f"""
            Nome Collezione: {stats['nome_collezione']}
            Numero totale Frammenti: {stats['numero_totale_documenti']}
            Numero Files Elaborati: {numero_files}
        """