from typing import override, List

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Element
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.utils.constants import PartitionStrategy

from knowledge_hub.app.config import app_logger, app_settings
from knowledge_hub.app.entity import DocumentMetaDataEntity
from knowledge_hub.app.enums import FileType, ParserType
from knowledge_hub.app.model import Document, DocumentMetadata
from knowledge_hub.app.processor.document_processor import DocumentProcessor
from knowledge_hub.app.utils.hash_util import HashUtil


class UnStructuredProcessor(DocumentProcessor):

    def __init__(self, strategyType: PartitionStrategy = PartitionStrategy.HI_RES,
                 keepTableAsHtml: bool = False,
                 chunk_size: int = 500,
                 new_after_n_chars: int = 2400,
                 combine_text_under_n_chars: int = 500,
                 enable_vision_model: bool = False,
                 ) -> None:
        self.__strategyType = strategyType
        self.__keepTableAsHtml = keepTableAsHtml
        self.__chunk_size = chunk_size
        self.__new_after_n_chars = new_after_n_chars
        self.__combine_text_under_n_chars = combine_text_under_n_chars
        self.__enable_vision_model=enable_vision_model
        app_logger.info(
            f"UnStructuredProcessor initialized with: strategy={strategyType.value if hasattr(strategyType, 'value') else strategyType}, "
            f"keepTableAsHtml={keepTableAsHtml}, chunk_size={chunk_size}, "
            f"new_after_n_chars={new_after_n_chars}, combine_text_under_n_chars={combine_text_under_n_chars}"
        )

    @override
    def get_config(self) -> dict:
        return {
            "parser_type": ParserType.UNSTRUCTURED.value,
            "strategy": self.__strategyType.value if hasattr(self.__strategyType, 'value') else self.__strategyType,
            "keep_table_as_html": self.__keepTableAsHtml,
            "chunk_size": self.__chunk_size,
            "new_after_n_chars": self.__new_after_n_chars,
            "combine_text_under_n_chars": self.__combine_text_under_n_chars,
        }

    @override
    def compare_config(self, old_config: dict) -> bool:
        if not old_config:
            app_logger.info(
                "UnStructuredProcessor: No old configuration found. Treating as config changed to ensure it gets written.")
            return True

        current_config = self.get_config()
        config_keys_to_compare = [
            "strategy",
            "chunk_size",
            "new_after_n_chars",
            "combine_text_under_n_chars",
            "parser_type"
        ]
        for key in config_keys_to_compare:
            if current_config.get(key) != old_config.get(key):
                app_logger.info(
                    f"UnStructuredProcessor: Config difference detected for key '{key}'. Old: {old_config.get(key)}, New: {current_config.get(key)}")
                return True
        return False

    def __create_elements(self, file_path: str) -> list[Element]:
        app_logger.info(
            f"UnStructuredProcessor: Executing partition_pdf for '{file_path}' using strategy={self.__strategyType.value if hasattr(self.__strategyType, 'value') else self.__strategyType}.")
        try:
            elements = partition_pdf(
                filename=file_path,
                strategy=self.__strategyType,
                infer_table_structure=self.__keepTableAsHtml,  # Keep tables as structured HTML, not jumbled text
                extract_image_block_types=["Image"],  # Grab images found in the PDF
                extract_image_block_to_payload=True  # Store images as base64 data you can actually use
            )
            app_logger.info(f"UnStructuredProcessor: Successfully partitioned PDF into {len(elements)} elements.")
            return elements
        except Exception as e:
            app_logger.error(f"UnStructuredProcessor: Failed to partition PDF '{file_path}'", exc_info=True)
            raise e

    def __create_chunks_by_title(self, elements: list[Element]) -> list[Element]:
        """Create intelligent chunks using title-based strategy"""
        app_logger.info(
            f"UnStructuredProcessor: Creating smart chunks from {len(elements)} elements. "
            f"Config: max_characters={self.__chunk_size}, new_after={self.__new_after_n_chars}, "
            f"combine_under={self.__combine_text_under_n_chars}"
        )
        try:
            chunks = chunk_by_title(
                elements,  # The parsed PDF elements from previous step
                max_characters=self.__chunk_size,
                new_after_n_chars=self.__new_after_n_chars,
                combine_text_under_n_chars=self.__combine_text_under_n_chars
            )
            app_logger.info(f"UnStructuredProcessor: Smart chunking completed. Created {len(chunks)} chunks.")
            return chunks
        except Exception as e:
            app_logger.error("UnStructuredProcessor: Failed to chunk elements by title", exc_info=True)
            raise e

    @override
    def process(self, file_path: str, metadata: DocumentMetaDataEntity) -> list[Document]:
        app_logger.info(f"UnStructuredProcessor: Start processing '{file_path}' (document_id={metadata.document_id})")
        try:
            # 1. Partition the elements
            elements = self.__create_elements(file_path)

            # Determine total pages
            valid_pages = [
                element.metadata.page_number
                for element in elements
                if element.metadata.page_number is not None
            ]
            metadata.total_pages = max(valid_pages) if valid_pages else 0
            app_logger.info(f"UnStructuredProcessor: Total pages detected: {metadata.total_pages}")

            # 2. Chunk process
            chunks = self.__create_chunks_by_title(elements)

            # 3. Assemble documents
            docs = []
            for i, chunk in enumerate(chunks, start=1):
                doc_metadata = DocumentMetadata(
                    doc_id=str(metadata.document_id),
                    file_name=metadata.file_name,
                    source=file_path,
                    parser=ParserType.UNSTRUCTURED,
                    file_type=FileType.PDF,
                    doc_version=metadata.doc_version,
                )

                if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'orig_elements'):
                    for element in chunk.metadata.orig_elements:
                        p_num = element.metadata.page_number
                        if p_num is not None:
                            doc_metadata.page_number = p_num

                        isImage = element.category == 'Image'
                        isTable = element.category == 'Table'

                        if isImage:
                            doc_metadata.has_image = True
                            img_base64 = getattr(element.metadata, 'image_base64', None)
                            if img_base64:
                                doc_metadata.images_as_base64.append(img_base64)

                        if isTable:
                            doc_metadata.has_table = True
                            tbl_html = getattr(element.metadata, 'text_as_html', None)
                            if tbl_html:
                                doc_metadata.table_as_html.append(tbl_html)

                # Generate deterministic chunk_id
                page_num = doc_metadata.page_number if doc_metadata.page_number is not None else 1
                doc_metadata.chunk_id = HashUtil.generate_chunk_id(doc_metadata.doc_id, page_num, i)
                doc_metadata.chunk_index = i
                doc_metadata.chunk_hash = HashUtil.generate_chunk_hash(chunk.text)
                doc_metadata.doc_version = metadata.doc_version

                #cretae summary, if chunk has multi media like image or tables
                summary=self.create_ai_enhanced_summary(chunk.text, doc_metadata.table_as_html,doc_metadata.images_as_base64)
                document = Document(content= summary if summary  else chunk.text , metadata=doc_metadata)
                docs.append(document)

            app_logger.info(f"UnStructuredProcessor: Finished processing. Generated {len(docs)} documents.")
            return docs
        except Exception as e:
            app_logger.error(f"UnStructuredProcessor: Error occurred during document processing for file '{file_path}'",
                             exc_info=True)
            raise e

    def create_ai_enhanced_summary(sefl,text: str, tables: List[str], images: List[str]) -> str:
        """Create AI-enhanced summary multi media context, support , image and tbales"""
        if  not sefl.__enable_vision_model:
            app_logger.info(f"UnStructuredProcessor: Skip multi model")
            return text
        try:
            if len(tables) == 0 and len(images) == 0:
                return text
            # Initialize LLM (needs vision model for images)
            llm = ChatGroq(
                api_key=app_settings.GROQ_API_KEY,
                model=app_settings.GROQ_VISION_MODEL
            )

            # Build the text prompt
            prompt_text = f"""You are creating a searchable description for document content retrieval.

            CONTENT TO ANALYZE:
            TEXT CONTENT:
            {text}

            """

            # Add tables if present
            if tables:
                prompt_text += "TABLES:\n"
                for i, table in enumerate(tables):
                    prompt_text += f"Table {i + 1}:\n{table}\n\n"

                    prompt_text += """
                    YOUR TASK:
                    Generate a comprehensive, searchable description that covers:

                    1. Key facts, numbers, and data points from text and tables
                    2. Main topics and concepts discussed  
                    3. Questions this content could answer
                    4. Visual content analysis (charts, diagrams, patterns in images)
                    5. Alternative search terms users might use

                    Make it detailed and searchable - prioritize findability over brevity.

                    SEARCHABLE DESCRIPTION:"""

            # Build message content: plain string if text-only/tables, multimodal list if images present
            if not images:
                message = HumanMessage(content=prompt_text)
            else:
                message_content = [{"type": "text", "text": prompt_text}]
                for image_base64 in images:
                    message_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    })
                message = HumanMessage(content=message_content)

            # Send to AI and get response
            app_logger.info(f"UnStructuredProcessor: Invoking ChatGroq vision model for AI-enhanced summary (tables={len(tables)}, images={len(images)}).")
            response = llm.invoke([message])
            app_logger.info("UnStructuredProcessor: AI-enhanced summary generated successfully.")

            return response.content

        except Exception as e:
            app_logger.warning(f"UnStructuredProcessor: Error occurred while generating AI summary for multimodal content: {str(e)}", exc_info=True)
            return text

