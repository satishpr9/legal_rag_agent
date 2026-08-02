from typing import List, Dict, Optional
from llama_index.core.node_parser import (
    HierarchicalNodeParser,
    SentenceSplitter,
    get_leaf_nodes,
    get_root_nodes
)
from llama_index.core.schema import (
    Document as LIDocument,
    TextNode,
    NodeRelationship,
    RelatedNodeInfo
)
from app.core.config import settings

class LegalHierarchicalChunker:
    def __init__(self):
        chunk_sizes = [
            settings.CHUNK_SIZE_PARENT,
            settings.CHUNK_SIZE_CHILD,
            settings.CHUNK_SIZE_LEAF
        ]
        self.parser = HierarchicalNodeParser.from_defaults(
            chunk_sizes=chunk_sizes,
            chunk_overlap=20
        )

    def chunk_documents(self, documents: List[LIDocument], global_metadata: dict = None) -> List[TextNode]:
        nodes = self.parser.get_nodes_from_documents(documents)
        if global_metadata:
            for node in nodes:
                node.metadata.update(global_metadata)
        return nodes

    def get_leaf_nodes(self, all_nodes: List[TextNode]) -> List[TextNode]:
        return get_leaf_nodes(all_nodes)

    def get_parent_nodes(self, all_nodes: List[TextNode]) -> List[TextNode]:
        return get_root_nodes(all_nodes)

    @staticmethod
    def split_pages(pages: List[Dict], global_metadata: Dict = None) -> List[Dict]:
        documents = []
        for page in pages:
            doc = LIDocument(
                text=page.get("text", ""),
                metadata={"page_number": page.get("page_number", 1)}
            )
            documents.append(doc)
            
        chunker = LegalHierarchicalChunker()
        all_nodes = chunker.chunk_documents(documents, global_metadata)
        leaf_nodes = chunker.get_leaf_nodes(all_nodes)
        
        result = []
        for node in leaf_nodes:
            result.append({
                "text": node.get_content(),
                "metadata": node.metadata
            })
        return result

    @staticmethod
    def split_text(text: str, global_metadata: Dict = None) -> List[Dict]:
        doc = LIDocument(text=text)
        chunker = LegalHierarchicalChunker()
        all_nodes = chunker.chunk_documents([doc], global_metadata)
        leaf_nodes = chunker.get_leaf_nodes(all_nodes)
        
        result = []
        for node in leaf_nodes:
            result.append({
                "text": node.get_content(),
                "metadata": node.metadata
            })
        return result
