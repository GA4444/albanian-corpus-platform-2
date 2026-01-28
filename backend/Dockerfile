FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-sqi \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install requirements, but make PaddleOCR optional (it may fail on some systems)
# First install all requirements except PaddleOCR
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
    "numpy<2"

# Try to install PaddleOCR (optional - OCR will work with Tesseract only if this fails)
RUN pip install --no-cache-dir paddlepaddle==2.6.2 paddleocr==2.7.3 || \
    echo "Warning: PaddleOCR installation failed - OCR will use Tesseract only"

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
