FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src ./src

# Create data directory
RUN mkdir -p /app/data

# Set Python path
ENV PYTHONPATH=/app/src

# Run the bot
CMD ["python", "-m", "secureclaw"]
