from overrides import overrides

from knowledge_hub.app.chunkers.chunker import Chunker
from knowledge_hub.app.constants import ErrorMessage,ErrorCode
from knowledge_hub.app.exception import InvalidInputException
from knowledge_hub.app.model import Document

from langchain_text_splitters import RecursiveCharacterTextSplitter

from knowledge_hub.app.utils.document_util import DocumentUtil
from knowledge_hub.app.config import app_logger

class RecursiveChunker(Chunker):
    def __init__(self, chunk_size:int,chunk_overlap:int)->None:
        super().__init__(chunk_size)
        self.chunk_overlap = chunk_overlap
        self.__splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    @overrides
    def chunk(self,docs:list[Document])->list[Document]:
        app_logger.info(f"Chunking {len(docs)} documents")
        if docs is None or len(docs)==0:
            app_logger.error(f"Empty chunk list")
            raise InvalidInputException(message=ErrorMessage.INPUT_SHOULD_NOT_BE_EMPTY,code=ErrorCode.INVALID_INPUT)

        d_docs=DocumentUtil.to_lang_chain_document(docs)
        chunks=self.__splitter.split_documents(d_docs)
        app_logger.info(f"Chunking completed {len(docs)} documents")
        return DocumentUtil.to_document_from_lang_chain(chunks,generate_chunk_id=True)



