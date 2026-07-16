from abc import ABC,abstractmethod

from knowledge_hub.app.model import Document


class Chunker(ABC):
    def __init__(self,chunk_size:int=512)->None:
        self._chunk_size = chunk_size
    @abstractmethod
    def chunk(self,docs:list[Document])->list[Document]:
        pass
