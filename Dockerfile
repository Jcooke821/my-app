# 1. Base image: multi-arch Python 3.9 on Debian Bullseye
FROM python:3.9-slim-bullseye

# 2. Install Pi-OS repo tooling, add Pi-OS repo, then install camera, media, build deps, CUPS, DBus, GLib, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      wget \
      gnupg \
      ca-certificates && \
    wget -O - https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | apt-key add - && \
    echo "deb http://archive.raspberrypi.org/debian bullseye main" > /etc/apt/sources.list.d/raspi.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      libcamera-apps \
      ffmpeg \
      build-essential \
      pkg-config \
      libdbus-1-dev \
      libglib2.0-dev \
      python3-dev \
      python3-cups && \
    rm -rf /var/lib/apt/lists/*

# 3. App setup
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 4. Runtime config
EXPOSE 5000
ENV PYTHONUNBUFFERED=1
CMD ["python", "run.py"]

