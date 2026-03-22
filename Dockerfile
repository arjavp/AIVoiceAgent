# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    libva-dev \
    curl \
    postgresql-client \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Copy dummy library into place (ensure it's available for agent.py)
# This folder is already part of the COPY ., but we make sure the entrypoint script is executable
RUN chmod +x docker-entrypoint.sh

# Expose the Django port
EXPOSE 8000

# Set the default entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command to run (will be overridden by docker-compose for the agent)
CMD ["python", "config/manage.py", "runserver", "0.0.0.0:8000"]
