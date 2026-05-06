FROM python:3.11-slim-bookworm

# 1. Performance & Timezone Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ="Asia/Kolkata"

WORKDIR /app

# 2. Install Essentials + FFmpeg (Crucial for Bots)
# gcc, python3-dev: uvloop और tgcrypto को कंपाइल करने के लिए
# ffmpeg: वीडियो थंबनेल और स्क्रीनशॉट के लिए
# git: कुछ python libraries के लिए
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    python3-dev \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 3. Upgrade Pip & Install Requirements
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# 4. Copy Application Code
COPY . .

# 5. Expose Web Server Port (वेब डैशबोर्ड के लिए ज़रूरी)
EXPOSE 8000

# 6. Run with Optimization (-O removes asserts for speed)
CMD ["python", "-O", "bot.py"]
