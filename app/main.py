from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from app.utils import Output, initialize_rag_service

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app_context = {}
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set up document service, citationqueryengine
    logging.info("Starting service - initializing document vector store and Qdrant RAG service...")
    try:
        index = initialize_rag_service()
        app_context["rag_service"] = index
        yield
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error - RAG service setup failure: {e}")

    logging.info("Shutting down service...")
    app_context.pop("rag_service")


app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Westeros Law Q&A Service"}

@app.get("/ask/")
async def get_answer(query: str) -> Output:
    logging.info(f"Received query: {query}")
    if query:
        logging.info(f"Passing query to RAG service...")
        try:
            response = app_context["rag_service"].query(query)
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error - error in querying service call: {e}")
    else:
        raise HTTPException(status_code=400, detail="Query was empty.")
