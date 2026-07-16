from abc import ABC, abstractmethod

from knowledge_hub.app.entity import DocumentMetaDataEntity
from knowledge_hub.app.model import Document


class DocumentProcessor(ABC):


    @abstractmethod
    def process(self, file_path: str, metadata: DocumentMetaDataEntity) -> list[Document]:
        '''
        step 0: set total pages in doc_metadata object
        steps 1: partition the doc
        steps 2: chunk the doc
        steps 3: generate chunk id and set into metadata
        '''
        pass