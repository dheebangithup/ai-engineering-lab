from abc import ABC, abstractmethod

from knowledge_hub.app.entity import DocumentMetaDataEntity
from  knowledge_hub.app.model import Document
class DocumentParser(ABC):

    @abstractmethod
    def parse(self,file_path, metadata: DocumentMetaDataEntity)->list[Document]:
        pass

