# Dockerfile for WordPress MCP Server on Render
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen

# Copy application files
COPY . .

# Expose the port that Render will use
EXPOSE 10000

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=10000

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Command to run the server
CMD ["sh", "-c", "uv run python setup_render.py && uv run python wordpress_mcp_https.py --transport http --host 0.0.0.0 --port 10000"]
