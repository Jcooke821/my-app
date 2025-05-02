# Dockerfile

# 1. Base image: Python 3.11 on Debian Bullseye
FROM python:3.11-slim-bullseye

# 2. Add Pi OS repo & install system deps for camera, CUPS, DBus, SMB, prctl,
#    Cairo, GPIO, and build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      wget \
      gnupg \
      ca-certificates && \
    wget -O - https://archive.raspberrypi.org/debian/raspberrypi.gpg.key \
      | apt-key add - && \
    echo "deb http://archive.raspberrypi.org/debian bullseye main" \
      > /etc/apt/sources.list.d/raspi.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      libcamera-apps \
      ffmpeg \
      python3-cups \
      python3-dbus \
      dbus-user-session \
      libsmbclient-dev \
      libcap-dev \
      libgpiod-dev \
      python3-libgpiod \
      pkg-config \
      build-essential \
      python3-dev \
      python3-cairo && \
    rm -rf /var/lib/apt/lists/*

# 3. Install your Python deps, removing the ones APT now provides
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN sed \
      -e '/^dbus-python==/d' \
      -e '/^cupshelpers==/d' \
      -e '/^pycups==/d' \
      -e '/^pycairo==/d' \
      -e '/^lgpio==/d' \
      requirements.txt > filtered-requirements.txt && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r filtered-requirements.txt

# 4. Copy your application code & set entrypoint
COPY . .
EXPOSE 5000
ENV PYTHONUNBUFFERED=1
CMD ["python", "run.py"]

