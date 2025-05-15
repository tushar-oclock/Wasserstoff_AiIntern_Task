FROM python:3.11-slim

WORKDIR /app

# Install tesseract-ocr for image processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for uploads and processed files
RUN mkdir -p data/uploads data/processed data/chroma_db

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=backend/app/main.py
ENV FLASK_ENV=production

# Expose port
EXPOSE 5000

# Start the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "backend.app.main:app"]