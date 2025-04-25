FROM python:3.9-slim-bullseye
 
# install wget, gnupg and certificates so we can add the Pi OS repo

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      wget \
      gnupg \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# add the Raspberry Pi OS repository & key

RUN wget -O - https://archive.raspberrypi.org/debian/raspberrypi.gpg.key \
      | apt-key add - \
&& echo "deb http://archive.raspberrypi.org/debian bullseye main" \
      > /etc/apt/sources.list.d/raspi.list

# now install camera apps, ffmpeg, build tools

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libcamera-apps \
      ffmpeg \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

# → the rest stays the same…

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
ENV PYTHONUNBUFFERED=1
CMD ["python", "run.py"]
