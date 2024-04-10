# Use an official Python runtime as a parent image
FROM python:3.8-slim-buster
# FROM python:3.8.18-slim-bookworm
# FROM ubuntu:latest

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN apt-get update && \
    apt-get install -y python3-dev default-libmysqlclient-dev build-essential pkg-config && \
    apt-get install -y python3-pip && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Expose port 5000 for the Flask app to listen on
EXPOSE 5000

# Define the command to run your Flask app
CMD ["python3", "app.py", "--host=0.0.0.0"]