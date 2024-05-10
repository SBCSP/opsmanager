# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system and Ansible dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    ssh \
    rsync \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install Python packages from requirements.txt + Ansible
RUN pip install --no-cache-dir -r requirements.txt gunicorn ansible

# Expose port 5000 for the application
EXPOSE 5000

# Environment variables for Flask
ENV FLASK_APP=app.py

# Start the gunicorn server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]