import re

import numpy as np
from langchain_openai import OpenAIEmbeddings
from sklearn.metrics.pairwise import cosine_similarity

from config import Config


class SemanticChunking:
    def __init__(
        self,
        api_key,
        breakpoint_percentile=95,
        buffer_size=1
    ):
        self.embeddings = OpenAIEmbeddings(
            model=Config.MODEL_NAME,
            openai_api_key=api_key
        )
        self.breakpoint_percentile = breakpoint_percentile
        self.buffer_size = buffer_size

    def _split_into_sentences(self, text):
        # Prima prova a dividere il testo usando la punteggiatura
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        # Se viene trovata una sola frase molto lunga,
        # divide usando altri delimitatori
        if len(sentences) == 1 and len(text) > 100:
            delimiters = r"([.!?\n;:])"
            parts = re.split(delimiters, text.strip())

            sentences = []

            for i in range(0, len(parts) - 1, 2):
                if parts[i].strip():
                    sentences.append(
                        parts[i].strip() + parts[i + 1]
                    )

            # Come ultima possibilità divide usando le virgole
            if len(sentences) == 1:
                sentences = [
                    sentence.strip() + ","
                    for sentence in text.split(",")
                    if sentence.strip()
                ]

                if sentences:
                    sentences[-1] = sentences[-1][:-1] + "."

        # Rimuove eventuali frasi vuote
        sentences = [
            sentence
            for sentence in sentences
            if sentence.strip()
        ]

        if not sentences:
            sentences = [text + "."]

        return sentences

    def _process_sentences(self, text):
        raw_sentences = self._split_into_sentences(text)

        sentences = [
            {
                "sentence": sentence,
                "index": index
            }
            for index, sentence in enumerate(raw_sentences)
        ]

        # Combina ogni frase con le frasi vicine
        for index, current in enumerate(sentences):
            context_range = range(
                max(0, index - self.buffer_size),
                min(
                    len(sentences),
                    index + self.buffer_size + 1
                )
            )

            current["combined_sentence"] = " ".join(
                sentences[position]["sentence"]
                for position in context_range
            )

        return sentences

    def _calculate_distances(self, sentences):
        embeddings = self.embeddings.embed_documents(
            [
                sentence["combined_sentence"]
                for sentence in sentences
            ]
        )

        distances = []

        for index in range(len(sentences) - 1):
            distance = 1 - cosine_similarity(
                [embeddings[index]],
                [embeddings[index + 1]]
            )[0][0]

            distances.append(distance)

        return distances

    def chunk_text(self, text):
        sentences = self._process_sentences(text)

        if not sentences:
            return [text]

        # Se esiste una sola frase non è necessario calcolare le distanze
        if len(sentences) == 1:
            return [sentences[0]["sentence"]]

        distances = self._calculate_distances(sentences)

        threshold = np.percentile(
            distances,
            self.breakpoint_percentile
        )

        split_points = [
            index
            for index, distance in enumerate(distances)
            if distance > threshold
        ]

        chunks = []
        start = 0

        for point in split_points + [len(sentences) - 1]:
            chunk = " ".join(
                sentence["sentence"]
                for sentence in sentences[start:point + 1]
            )

            chunks.append(chunk)
            start = point + 1

        return chunks