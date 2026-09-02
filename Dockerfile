FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole project
COPY . /app

# Expose port (Cloud Run uses PORT environment variable, defaults to 8080)
ENV PORT 8080

# Command to run the FastAPI app
CMD uvicorn pre_build.api.main:app --host 0.0.0.0 --port ${PORT}
