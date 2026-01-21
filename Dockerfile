FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies one by one to see which fails
RUN pip install --no-cache-dir fastapi==0.104.1 && \
    pip install --no-cache-dir uvicorn[standard]==0.24.0 && \
    pip install --no-cache-dir python-dotenv==1.0.0 && \
    pip install --no-cache-dir pydantic==2.5.0 && \
    pip install --no-cache-dir python-multipart==0.0.6 && \
    pip install --no-cache-dir gitpython==3.1.40 && \
    pip install --no-cache-dir langchain==0.1.0 && \
    pip install --no-cache-dir langchain-community==0.0.10 && \
    pip install --no-cache-dir langchain-chroma==0.1.0 && \
    pip install --no-cache-dir langchain-huggingface==0.0.1 && \
    pip install --no-cache-dir langchain-groq==0.0.1 && \
    pip install --no-cache-dir chromadb==0.4.22 && \
    pip install --no-cache-dir sentence-transformers==2.2.2

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p chroma_db static

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
