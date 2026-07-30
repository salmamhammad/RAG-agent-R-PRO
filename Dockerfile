FROM python:3.11-slim

# Install system dependencies (for PDF, CHM, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libchm-dev \
    p7zip-full \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Additional pip installs 
RUN pip install --no-cache-dir \
    pychm \
    Pillow

# Copy the entire project 
COPY . .

# Create necessary directories
RUN mkdir -p data logs chroma_db storage static widget/dist

# Expose the FastAPI port 
EXPOSE 8000


# Use the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]