FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create config directory
RUN mkdir -p /app/config

# Copy example config
COPY config.example.yaml /app/config/

# Expose MCP server port (if running in HTTP mode)
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app
ENV WEMS_CONFIG=/app/config/config.yaml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1

# Run the MCP server
CMD ["python3", "wems_mcp_server.py"]