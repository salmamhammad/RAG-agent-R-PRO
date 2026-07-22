FROM python:3.11-slim

# Install system dependencies (for PDF, CHM, etc.)
RUN apt-get update && apt-get install -y \
    libchm-dev \
    p7zip-full \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project (this will be overridden by volume mounts in dev)
COPY . .

# Create necessary directories
RUN mkdir -p data logs chroma_db storage static widget/dist

# Copy entrypoint script and make it executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose the FastAPI port
EXPOSE 8000

# Use the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]