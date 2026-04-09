FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY process.py .
COPY app.py .

# Create input/output directories
RUN mkdir -p /app/input /app/output

EXPOSE 8080

CMD ["python3", "app.py"]
