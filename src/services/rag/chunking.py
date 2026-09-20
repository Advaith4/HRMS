"""
src/services/rag/chunking.py
Hierarchical Recursive Character Chunker for Production RAG in TalentForge AI.
Preserves paragraph, sentence, and heading boundaries with configurable overlap.
"""
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentChunk:
    text: str
    chunk_index: int
    char_start: int
    char_end: int
    page_number: int = 1
    metadata: dict[str, Any] | None = None


class RecursiveCharacterChunker:
    """
    Hierarchical text chunker that iteratively splits text along natural linguistic boundaries
    (paragraphs -> lines -> sentences -> words) while preserving character overlap.
    """
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        separators: list[str] | None = None,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "; ", ", ", " ", ""]

    def split_text(self, text: str, page_number: int = 1) -> list[DocumentChunk]:
        """Splits text into bounded overlapping chunks."""
        raw_chunks = self._split_recursive(text, self.separators)
        merged_chunks = self._merge_splits(raw_chunks)

        document_chunks = []
        current_pos = 0
        for i, chunk_text in enumerate(merged_chunks):
            start_pos = text.find(chunk_text, max(0, current_pos - self.chunk_overlap * 2))
            if start_pos == -1:
                start_pos = current_pos
            end_pos = start_pos + len(chunk_text)
            current_pos = end_pos

            document_chunks.append(
                DocumentChunk(
                    text=chunk_text,
                    chunk_index=i + 1,
                    char_start=start_pos,
                    char_end=end_pos,
                    page_number=page_number,
                )
            )

        return document_chunks

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        """Recursively splits text on the highest-priority separator available."""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        if not separators:
            # Fallback to hard character slicing
            return [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        sep = separators[0]
        remaining_seps = separators[1:]

        if sep == "":
            return list(text)

        splits = text.split(sep)
        result = []
        for s in splits:
            if not s.strip():
                continue
            if len(s) > self.chunk_size:
                # Recurse with finer separator
                result.extend(self._split_recursive(s, remaining_seps))
            else:
                result.append(s.strip())

        return result

    def _merge_splits(self, splits: list[str]) -> list[str]:
        """Merges small splits into cohesive chunks up to chunk_size with overlap."""
        chunks = []
        current_chunk = []
        current_len = 0

        for split in splits:
            split_len = len(split)
            if current_len + split_len + (1 if current_chunk else 0) > self.chunk_size and current_chunk:
                merged = " ".join(current_chunk).strip()
                if merged:
                    chunks.append(merged)
                
                # Overlap retention: keep the last item if it fits in overlap
                overlap_chunk = []
                overlap_len = 0
                for item in reversed(current_chunk):
                    if overlap_len + len(item) <= self.chunk_overlap:
                        overlap_chunk.insert(0, item)
                        overlap_len += len(item)
                    else:
                        break
                current_chunk = overlap_chunk
                current_len = sum(len(x) for x in current_chunk)

            current_chunk.append(split)
            current_len += split_len + 1

        if current_chunk:
            final_merged = " ".join(current_chunk).strip()
            if final_merged:
                chunks.append(final_merged)

        return chunks

