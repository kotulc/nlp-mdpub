from dataclasses import dataclass, field
from mdpub.parser.models import StructuredDocument
from mdpub.crud.repo import DocumentRepo

@dataclass
class MemoryRepo(DocumentRepo):
    _docs: dict[str, StructuredDocument] = field(default_factory=dict)

    def upsert(self, doc: StructuredDocument) -> StructuredDocument:
        self._docs[doc.doc_id] = doc
        return doc

    def get(self, doc_id: str) -> StructuredDocument | None:
        return self._docs.get(doc_id)
