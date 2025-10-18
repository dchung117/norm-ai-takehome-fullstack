from pydantic import BaseModel
from itertools import chain

import qdrant_client
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.schema import Document
from llama_index.core import (
    VectorStoreIndex,
    Settings
)
from llama_index.core.postprocessor import SimilarityPostprocessor

from llama_index.core.query_engine import CitationQueryEngine
import pymupdf

from dotenv import load_dotenv
import re
from dataclasses import dataclass
import os

load_dotenv()
key = os.environ['OPENAI_API_KEY']
document_file = os.environ["DOCUMENT_FILE"]
model = os.environ["LLM_MODEL_NAME"]
similarity_top_k = int(os.environ["SIMILARITY_TOP_K"])
similarity_cutoff = float(os.environ["SIMILARITY_CUTOFF"])

Settings.embed_model =OpenAIEmbedding()
Settings.llm = OpenAI(api_key=key, model=model)

@dataclass
class Input:
    query: str
    file_path: str

@dataclass
class Citation:
    source: str
    text: str

class Output(BaseModel):
    query: str
    response: str
    citations: list[Citation]

class DocumentService:

    """
    Service that loads PDF and parses each section into documents.

     """

    def create_documents(self) -> list[Document]:
        """
        Parses laws from PDF file. Laws are organized hierarchically (see example below):

        1. Law topic 1
            1.1 Law 1
            1.2 Law 2
                1.2.1 Law clause 2.1
                1.2.2 Law clause 2.2

        Each law (and law clause) are parsed into separate, individual documents.
        Each document will also contain its corresponding law topic as well as parent laws that they fall under
        (e.g. document for Law clause 1.2.1 will have metadata containing its topic (1. Law topic 1) as well as its parent law (1.2 Law))

        Args:
            None
        Returns:
            list[Documents]:
                List of Llama index documents for each law w/ hierarchy of laws in the metadata.
        """
        doc = pymupdf.open(document_file)

        # Concatenate text per page
        text = ""
        for page in doc:
            text += page.get_text()

        # Divide text into sections
        sections = []
        section_num_pattern = r'^(\d+\.)+'
        text_lines = text.split("\n")
        # print(text_lines)
        for i,line in enumerate(text_lines):
            if re.match(section_num_pattern, line):
                law_text = ""
                j = i + 1
                while j < len(text_lines) and not re.match(section_num_pattern, text_lines[j]) and not text_lines[j].startswith("Citations") and not text_lines[j].startswith("https"):
                    law_text += text_lines[j]
                    if law_text[-1].isalpha():
                        law_text += " "
                    j += 1
                sections.append((line, law_text.strip()))

        # Create documents
        documents = []
        stack = []
        law_topic_section_pattern = r'^\d+\.$'
        law_topic = ""
        for section_num, line in sections:
            # clear stack if new law topic reached
            if re.match(law_topic_section_pattern, section_num):
                law_topic = line
                stack = []
            else:
                # Create document
                # remove fully-explored laws from stack
                while stack and len(stack[-1][0]) >= len(section_num):
                    stack.pop(-1)

                # metadata = {"topic": law_topic} | {
                #     f"parent_law_{i+1}":parent_law[1] for i,parent_law in enumerate(stack)
                # }
                metadata = {"topic": law_topic, "section": section_num} | {
                    "parent_laws": [parent_law[1] for parent_law in stack]
                }
                doc = Document(
                    text=line,
                    metadata=metadata,
                    excluded_llm_metadata_keys=["parent_laws", "section"], # remove full hierarchy from LLM prompt,
                    excluded_embed_metadata_keys=["section"],
                )
                documents.append(doc)

                stack.append((section_num, line))

        # todo: filter out parent metadata for LLM call?
        # todo: save off documents?
        # for doc in documents:
        #     print("##### LAW #####")
        #     # print(doc.get_content(metadata_mode=MetadataMode.LLM))
        #     print(doc.get_content(metadata_mode=MetadataMode.EMBED))
        #     print("###############")
        #     print()
        return documents


class QdrantService:
    def __init__(self, k: int = similarity_top_k, similarity_cutoff: float = 0.75):
        self.index = None
        self.citation_query_engine = None
        self.similarity_postprocessor = None
        self.k = k
        self.similarity_cutoff = similarity_cutoff

    def connect(self) -> None:
        # create client
        client = qdrant_client.QdrantClient(location=":memory:")

        # create vector store
        vstore = QdrantVectorStore(client=client, collection_name='temp')

        # use gpt-4 as embedding model
        # settings = Settings.from_defaults(
        #     embed_model=OpenAIEmbedding(),
        #     llm=OpenAI(api_key=key, model="gpt-4")
        # )

        # create vector index from embedding model and vector store
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=vstore,
            # embed_model=OpenAIEmbedding(),
            # llm=OpenAI(api_key=key, model="gpt-4")
        )

        # Set up the simliarity post-processor - filter out retrieved laws less than threshold
        self.similarity_postprocessor = SimilarityPostprocessor(similarity_cutoff=self.similarity_cutoff)

        # create citationqueryengine
        self.citation_query_engine = CitationQueryEngine.from_args(index=self.index,
                                                                   similarity_top_k=self.k,
                                                                #    citation_chunk_size=512,
                                                                   node_postprocessors=[self.similarity_postprocessor]
                                                                   )

    def load(self, docs = list[Document]):
        self.index.insert_nodes(docs)

    def query(self, query_str: str) -> Output:

        """
        This method needs to initialize the query engine, run the query, and return
        the result as a pydantic Output class. This is what will be returned as
        JSON via the FastAPI endpount. Fee free to do this however you'd like, but
        a its worth noting that the llama-index package has a CitationQueryEngine...

        Also, be sure to make use of self.k (the number of vectors to return based
        on semantic similarity).

        # Example output object
        citations = [
            Citation(source="Law 1", text="Theft is punishable by hanging"),
            Citation(source="Law 2", text="Tax evasion is punishable by banishment."),
        ]

        output = Output(
            query=query_str,
            response=response_text,
            citations=citations
            )

        return output

        """
        # todo: prompt for llm call (system prompt, give query + retrieved laws, instruct to only answer question using laws given in context. 
        # todo: if it can't be answered by context, explain that there's no relevant info in the laws.
        response = self.citation_query_engine.query(query_str)

        # extract citations from response (i.e. only return sources that were referenced in the response to client)
        citation_pattern = r'\[\d+(?:,\d+)*\]'
        citation_idxs_raw = [idx_str[1:-1] for idx_str in re.findall(citation_pattern, response.response)]
        citation_idxs_parsed = list(chain.from_iterable([[int(idx)-1 for idx in idx_str.split(",")] for idx_str in citation_idxs_raw]))

        citation_nodes = [response.source_nodes[i] for i in citation_idxs_parsed]
        citations = [
            Citation(
                source=f"{node.metadata['topic']}: Section {node.metadata['section']}",
                text=node.text,
            )
            for node in citation_nodes
        ]

        return Output(query=query_str, response=response.response, citations=citations)


def initialize_rag_service() -> QdrantService:
    doc_service = DocumentService()
    docs = doc_service.create_documents()

    index = QdrantService(k = similarity_top_k, similarity_cutoff=similarity_cutoff)
    index.connect()
    index.load(docs)
    return index


if __name__ == "__main__":
    # Example workflow
    doc_service = DocumentService() # implemented
    docs = doc_service.create_documents() # NOT implemented

    index = QdrantService() # implemented
    index.connect() # implemented
    index.load(docs) # implemented

    response = index.query("what happens if I steal?")
    print(response, "\n")
    response = index.query("what happens if I have poach a slave?")
    print(response, "\n")
    response = index.query("what happens if I bake with sawdust in my flour?")
    print(response, "\n")
    response = index.query("what happens if I steal a car?")
    print(response, "\n")





