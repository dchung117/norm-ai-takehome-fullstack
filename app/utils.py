from pydantic import BaseModel
import qdrant_client
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.schema import Document, MetadataMode
from llama_index.core import (
    VectorStoreIndex,
    Settings
)
from llama_index.core.query_engine import CitationQueryEngine


import pymupdf
import re
from dataclasses import dataclass
import os

# todo: use pydotenv
key = os.environ['OPENAI_API_KEY']
document_file = os.environ["DOCUMENT_FILE"]

Settings.embed_model =OpenAIEmbedding()
Settings.llm = OpenAI(api_key=key, model="gpt-4")

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
    Update this service to load the pdf and extract its contents.
    The example code below will help with the data structured required
    when using the QdrantService.load() method below. Note: for this
    exercise, ignore the subtle difference between llama-index's
    Document and Node classes (i.e, treat them as interchangeable).

    # example code
    def create_documents() -> list[Document]:

        docs = [
            Document(
                metadata={"Section": "Law 1"},
                text="Theft is punishable by hanging",
            ),
            Document(
                metadata={"Section": "Law 2"},
                text="Tax evasion is punishable by banishment.",
            ),
        ]

        return docs

     """

    def create_documents(self) -> list[Document]:
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

                metadata = {"topic": law_topic} | {
                    f"parent_law_{i+1}":parent_law[1] for i,parent_law in enumerate(stack)
                }
                doc = Document(
                    text=line,
                    metadata=metadata
                )
                documents.append(doc)

                stack.append((section_num, line))

        # todo: filter out parent metadata for LLM call?
        # todo: save off documents?
        # for doc in documents:
        #     print("##### LAW #####")
        #     print(doc.get_content(metadata_mode=MetadataMode.LLM))
        #     # print(doc.get_content(metadata_mode=MetadataMode.EMBED))
        #     print("###############")
        #     print()
        return documents


class QdrantService:
    def __init__(self, k: int = 2):
        self.index = None
        self.citation_query_engine = None
        self.k = k

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

        # create citationqueryengine
        self.citation_query_engine = CitationQueryEngine.from_args(index=self.index)

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
        # if it can't be answered by context, explain that there's no relevant info in the laws.


if __name__ == "__main__":
    # Example workflow
    doc_service = DocumentService() # implemented
    docs = doc_service.create_documents() # NOT implemented

    index = QdrantService() # implemented
    index.connect() # implemented
    index.load(docs) # implemented

    # index.query("what happens if I steal?") # NOT implemented





