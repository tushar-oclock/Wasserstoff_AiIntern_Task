FROM python:3.11-slim

WORKDIR /app

# Install tesseract and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Prepare directories
RUN mkdir -p data/uploads data/processed data/chroma_db

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_ENV=production

EXPOSE 7860

# Start the app
CMD ["python", "app.py"]
