# Norm Ai Westeros Seven Kingdoms Law Q&A Service

This repository contains backend and frontend code to host an AI-powered Q&A service for the laws governing the Seven Kingdoms of Westeros.

## Setup

### 1. Environmental variables
After cloning the repository, create a `.env` file that contains the following variables:

1. OPENAI_API_KEY (str): API key for sending RAG queries to LLMs hosted in OpenAI API.
2. DOCUMENT_FILE (str): Relative path to the file containing the laws to populate our document vector store. Some important assumptions are listed below:
    a. The document parser expects all relevant laws to be contained in a single file - please pass only a single file, not a directory.
    b. The parser assumes that the law document is in PDF format - please format the relevant document file as PDF.
3. LLM_MODEL_NAME (str): OpenAI LLM alias to use for generating RAG responses to questions (default: `gpt-4`).
4. SIMILARITY_TOP_K (int): Vector retrieval hyperparameter that sets how many documents are retrieved from the vector store as candidates to populate the LLM prompt context. (default: `10`)
5. SIMILARITY_CUTOFF (float): Vector retrieval post-processing hyperparameter applied during document retrieval to filter out less relevant documents before they are passed as context to the LLM for generation. Values are between `0.0-1.0` - higher values are more restrictive on similarity and filters out more documents (default: `0.8`).

See example below:
```
OPENAI_API_KEY="your-api-key"
DOCUMENT_FILE="docs/laws.pdf"
LLM_MODEL_NAME="gpt-4"
SIMILARITY_TOP_K=10
SIMILARITY_CUTOFF=0.75
```

### 2. Building Docker image and launching service locally

Once the `.env` file is created, please run the convenience script `launch_app.sh` that builds the Docker image for the service and launches a container locally.

Before running the script, two more environmental variables must be set:

1. CONTAINER_IMAGE (str): the name of the image and container that will be locally built and launched, respectively.
2. HOST_PORT (str): the host port number to expose for the backend service. The container exposed port is port 80.

See example below:

```
export CONTAINER_IMAGE="norm-fullstack"
export HOST_PORT=80
```

If the script runs successfully, there should be no error messages. Also, the image hash and the following message should appear in the terminal:

```
Docker container '$CONTAINER_IMAGE' launched, mapped port $HOST_PORT to port 80.
```

### 3. Using the service

Since the server is built using FastAPI, the Q&A service can be accessed via the Swagger documentation page. After launching the containerized service locally in step 2, open a web browser and navigate to `localhost:$HOST_PORT/docs` in the search bar. The `HOST_PORT` is the value of `HOST_PORT` that you set as an environment variable in part 2.

The endpoint for passing questions to the Q&A service is the `GET /ask` endpoint. It is the second drop-down tab under the `default` endpoints tab:

![alt text](docs/images/ask_endpoint.png)

The endpoint expects a mandatory query argument `query` - a question about any of the laws of the Seven Kingdoms (e.g. what happens if I steal?). Successful responses will return the answer to the user's question including citations that reference the corresponding laws from the law document passed in `DOCUMENT_FILE`:

![alt text](docs/images/ask_endpoint_success_response.png)

Some interesting edge cases to also try out:
    1. Empty query - the service should return a 400 response w/ the detail `Query was empty.`
    2. Queries regarding laws not contained in the document (e.g. `what happens if I steal a car?`) - the response should explain that no relevant laws explain what happens if a car is stolen.

## Appendix

The appendix contains some assumptions and design choices made (with justifications) for the different components of the Q&A service.

### 1. Law document vector store initialization

todo: explain assumptions about format of the law document
todo: explain why a PDF parser was used vs an LLM to parse out individual laws from document
todo: explain why each document contained a particular law -> citations ideally should reference individual laws, not necessarily a collection of laws.
todo: explain metadata construction (law topic, section number, parent laws) -> explain why parent laws were used in retrieval but not generation step. explain how parent laws were appended to metadata (treat each law section as a tree; dfs algorithm to append each individual law w/ its parent law hierarchy)

### 2. Document retrieval implementation

todo: explain why a larger value for similarity_top_k was selected -> some questions need to reference laws from different sections (e.g. what happens if I steal? -> mentioned in thievery and watch), too small values of k would exclude the information in watch, which is still relevant. this would create retrievals that would have likely collect all relevant laws but would also contain a lot of noise; similarity score cutoff was used to filter out the "noisier" documents after retrieval. This hyperparameter can be tuned.'

### 3. Citation response post-processing

todo: explain why not all retrieved citations were included in response -> the answer to the client's question doesn't cite every source retrieved by the index. in order to avoid confusion by the client/user, we select the laws that were directly cited in the response and pass those back to the client.