import hashlib
import os
import uuid

from config import Config
class DocumentProcessor:
    @staticmethod
    def read_first_lines(file_path, n_lines=100):
        with open(file_path, "r", encoding="utf-8") as file:
            return [
                line.strip()
                for line, _ in zip(file, range(n_lines))
            ]

    @staticmethod
    def get_file_hash(file_path):
        """Calcola l'hash MD5 del contenuto del file."""

        hash_md5 = hashlib.md5()

        with open(file_path, "rb") as file:
            for chunk in iter(
                lambda: file.read(4096),
                b"",
            ):
                hash_md5.update(chunk)

        return hash_md5.hexdigest()

    @staticmethod
    def get_document_metadata(file_path):
        """Restituisce hash, ultima modifica e nome del file."""

        return {
            "hash": DocumentProcessor.get_file_hash(file_path),
            "last_modified": os.path.getmtime(file_path),
            "source": os.path.basename(file_path),
        }

    @staticmethod
    def process_single_document(file_path):
        """Divide un singolo documento in frammenti."""

        documents = []
        metadatas = []
        ids = []

        with open(
            file_path,
            "r",
            encoding="utf-8",
        ) as file:
            content = file.read()

        chunks = content.replace("\n", ".").split("### ")

        file_metadata = (
            DocumentProcessor.get_document_metadata(file_path)
        )

        for chunk in chunks:
            if chunk.strip():
                documents.append(chunk.strip())
                metadatas.append(file_metadata.copy())
                ids.append(str(uuid.uuid4()))

        return documents, metadatas, ids

    @staticmethod
    def process_documents(db):
        """Sincronizza i curriculum con il database."""

        if not os.path.exists(Config.DOCUMENTS_DIR):
            os.makedirs(Config.DOCUMENTS_DIR)

        current_files = {
            filename: DocumentProcessor.get_document_metadata(
                os.path.join(
                    Config.DOCUMENTS_DIR,
                    filename,
                )
            )
            for filename in os.listdir(Config.DOCUMENTS_DIR)
            if filename.endswith(".txt")
        }

        existing_files = db.get_tracked_files()

        files_to_add = (
            set(current_files.keys())
            - set(existing_files.keys())
        )

        files_to_remove = (
            set(existing_files.keys())
            - set(current_files.keys())
        )

        files_to_update = {
            filename
            for filename in (
                set(current_files.keys())
                & set(existing_files.keys())
            )
            if (
                current_files[filename]["hash"]
                != existing_files[filename]["hash"]
            )
        }

        print(f"Files to add: {files_to_add}")
        print(f"Files to update: {files_to_update}")
        print(f"Files to remove: {files_to_remove}")

        for action, files in [
            ("add", files_to_add),
            ("update", files_to_update),
        ]:
            for filename in files:
                file_path = os.path.join(
                    Config.DOCUMENTS_DIR,
                    filename,
                )

                documents, metadatas, ids = (
                    DocumentProcessor.process_single_document(
                        file_path
                    )
                )

                if action == "update":
                    db.remove_document_by_source(filename)

                if documents:
                    db.add_documents(
                        documents,
                        metadatas,
                        ids,
                    )

        for filename in files_to_remove:
            db.remove_document_by_source(filename)

        return (
            len(files_to_add),
            len(files_to_update),
            len(files_to_remove),
        )