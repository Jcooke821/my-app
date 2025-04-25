# 1. Base image: multi-arch Python 3.9 on Debian Bullseye
FROM python:3.9-slim-bullseye

# 2. Install OS packages needed for Pi camera and media
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libcamera-apps \
      ffmpeg \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

# 3. Set working dir inside the container
WORKDIR /usr/src/app

# 4. Copy only requirements first (leverages Docker layer cache)
COPY requirements.txt ./

# 5. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy your entire app source code
COPY . .

# 7. Expose the port your Flask app listens on
EXPOSE 5000

# 8. Don’t buffer Python stdout/stderr (helps with real-time logs)
ENV PYTHONUNBUFFERED=1

# 9. Command to run your app
CMD ["python", "run.py"]
