# Frontend Dockerfile (for containerized development)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Flet
RUN apt-get update && apt-get install -y \
    libgtk-3-0 \
    libglib2.0-0 \
    libgbm1 \
    libasound2 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    mpv \
    libmpv2 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/lib/x86_64-linux-gnu/libmpv.so.2 /usr/lib/x86_64-linux-gnu/libmpv.so.1 || true

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app /app/app

# Expose port for Flet web mode (if needed for testing)
EXPOSE 8550

# Run the application in web mode
CMD ["python", "-m", "app.main"]

