from __future__ import annotations
from abc import ABC, abstractmethod
from mdpub.parser.models import StructuredDocument

class DocumentRepo(ABC):
    @abstractmethod
    def upsert_by_source_path(self, doc: StructuredDocument) -> tuple[StructuredDocument, bool]:
        """Return (saved_doc, changed_flag)."""
        raise NotImplementedError

    @abstractmethod
    def get_by_source_path(self, source_path: str) -> StructuredDocument | None:
        raise NotImplementedError
