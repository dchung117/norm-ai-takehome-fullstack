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

If the script runs successfully, there should be no error messages. Also, the following message should appear in the terminal:

```
Docker container '$CONTAINER_IMAGE' launched, mapped port $HOST_PORT to port 80.
```


### 3. Using the service


