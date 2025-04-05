#!/bin/bash

set -e  # Exit on error

IMAGE_NAME=botcoin
ENV_FILE=.env  # Path to your .env file

# Check if the image already exists
if docker images -q $IMAGE_NAME; then
    echo "⚠️ Image '$IMAGE_NAME' already exists. Deleting old image..."
    docker rmi -f $IMAGE_NAME
else
    echo "✅ No existing image found."
fi

# Build the new Docker image
echo "🛠️ Building Docker image: $IMAGE_NAME"
docker build -t $IMAGE_NAME .

# Run the container with environment variables from .env
echo "🚀 Running Docker container with environment variables..."
docker run --rm --env-file $ENV_FILE $IMAGE_NAME
