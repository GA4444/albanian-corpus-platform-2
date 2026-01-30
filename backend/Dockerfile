FROM python:3.9-slim

WORKDIR /app

# Install system dependencies with retry logic
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Try to install Albanian language pack (optional, continue if fails)
RUN apt-get update && apt-get install -y tesseract-ocr-sqi || echo "Albanian language pack not available, continuing..."

# Copy requirements first for better caching
COPY requirements.txt .

# Install requirements (excluding PaddleOCR - it's optional and causes slow builds)
# PaddleOCR can be installed manually if needed, but Tesseract works fine for most cases
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    sqlalchemy==2.0.23 \
    pydantic==2.5.0 \
    passlib[bcrypt]==1.7.4 \
    python-multipart==0.0.6 \
    python-dotenv==1.1.1 \
    gtts==2.4.0 \
    SpeechRecognition==3.10.0 \
    pydub==0.25.1 \
    pytesseract==0.3.13 \
    "pillow>=10.0.0" \
    azure-cognitiveservices-speech==1.34.0 \
    "requests>=2.31.0" \
    "openai>=1.3.0" \
    "anthropic>=0.8.0" \
    numpy==1.26.4 \
    psycopg2-binary==2.9.9

# Note: PaddleOCR is intentionally excluded from Docker build to speed up deployment
# The OCR functionality works perfectly with Tesseract (already installed above)
# If PaddleOCR is needed later, it can be added manually or via a separate step

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
ENV PORT=8000

# Expose port (Render uses PORT env variable)
EXPOSE 8000

# Run the application using shell form to allow environment variable expansion
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
