#!/bin/zsh

# Check if CONTAINER_IMAGE is set
if [ -z "$CONTAINER_IMAGE" ]; then
  echo "Error: CONTAINER_IMAGE environment variable is not set."
  exit 1
fi

# Check if HOST_PORT is set
if [ -z "$HOST_PORT" ]; then
  echo "Error: HOST_PORT environment variable is not set."
  exit 1
fi

docker run -d -p $HOST_PORT:80 --name "${CONTAINER_IMAGE%:*}-container" "$CONTAINER_IMAGE"
echo "Docker container '$CONTAINER_IMAGE' launched, mapped port $HOST_PORT to port 80."