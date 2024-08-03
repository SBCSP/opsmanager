FROM ubuntu:22.04

# Set non-interactive frontend
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    software-properties-common \
    wget \
    tzdata \
    openssh-client

# Configure timezone (set your desired timezone)
RUN ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata

# Add Ansible repository and install Ansible
RUN apt-add-repository ppa:ansible/ansible -y && \
    apt-get update && \
    apt-get install -y ansible

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Create .ssh directory and set permissions
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run the application
CMD ["python3", "app.py"]