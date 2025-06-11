FROM python:3.11.12

# Set environment variable for non-interactive apt-get installs
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Add requirements.txt and install Python dependencies
ADD requirements.txt /
RUN pip install -U pip --no-cache-dir
RUN pip install -r /requirements.txt --no-cache-dir

# Add application script
ADD app.py /

# Set environment variable for unbuffered Python output (good for logging)
ENV PYTHONUNBUFFERED=1

CMD ["python", "./app.py"]
