from collections import defaultdict

from unstructured.documents.elements import Element
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.utils.constants import PartitionStrategy

from knowledge_hub.app.entity import DocumentMetaDataEntity
from knowledge_hub.app.parser.DocumentParser import DocumentParser
from knowledge_hub.app.model import Document,DocumentMetadata

from typing import override

from knowledge_hub.app.enums import FileType
from knowledge_hub.app.enums import ParserType

'''
Name: unstructured
Version: 0.22.31
'''
class UnstructuredParser(DocumentParser):
    def __init__(self,strategyType:PartitionStrategy=PartitionStrategy.HI_RES,
                 keepTableAsHtml:bool=False
                 )->None:
        self.__strategyType = strategyType
        self.__keepTableAsHtml = keepTableAsHtml


    def __create_elements(self,file_path:str)->list[Element]:
        return partition_pdf(
            filename=file_path,
            strategy=self.__strategyType,
            infer_table_structure=self.__keepTableAsHtml,# Keep tables as structured HTML, not jumbled text
            extract_image_block_types=["Image"],  # Grab images found in the PDF
            extract_image_block_to_payload=True  # Store images as base64 data you can actually use
        )


    @override
    def parse(self,file_path:str, metadata: DocumentMetaDataEntity)->list[Document]:
        elements=self.__create_elements(file_path)
        metadata.total_pages = max(
            element.metadata.page_number
            for element in elements
            if element.metadata.page_number is not None
        )
        #grouping by page wise
        pages = defaultdict(list)
        for element in elements:
            page_number = element.metadata.page_number
            pages[page_number].append(element)

        docs=[]
        for page, page_elements in pages.items():
            for element in page_elements:
                p_num = element.metadata.page_number
                isImage = element.category == 'Image'
                isTable = element.category == 'Table'
                doc = Document(
                    content=element.text,
                    metadata=DocumentMetadata(
                        doc_id=metadata.document_id,
                        file_name=file_path.split("/")[-1],
                        source=file_path,
                        file_type=FileType.PDF,
                        page_number=p_num,
                        parser=ParserType.UNSTRUCTURED,
                        has_image=isImage,
                        has_table=isTable,
                        images_as_base64=[getattr(element.metadata, 'image_base64', element.text)],
                        table_as_html=[getattr(element.metadata, 'text_as_html', element.text)],

                    )

                )
                docs.append(doc)




        return docs





