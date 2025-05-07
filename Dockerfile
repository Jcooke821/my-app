## Dockerfile for EchoTrace Application

# 1) Use official slim Python base image
FROM python:3.11-slim-bullseye

# 2) Create a non-root user for security
RUN addgroup --system app && adduser --system --ingroup app app

# 3) Set working directory
WORKDIR /app

# 4) Copy and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 5) Copy application source
COPY . /app

# 6) Switch to non-root user
USER app

# 7) Expose default application port (adjust if needed)
EXPOSE 5000

# 8) Application entrypoint
CMD ["python", "run.py"]

