FROM python:3.9-slim

# Install piper-tts and its dependencies
RUN pip install --no-cache-dir piper-tts

# Create directories for input/output and models
RUN mkdir -p /input /output /models

# Set working directory
WORKDIR /models

# Set environment variable for model directory
ENV PIPER_MODEL_DIR=/models

# Default command (can be overridden)
CMD ["bash"] 