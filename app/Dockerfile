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

# Install Miniconda
RUN mkdir -p /opt/miniconda3 && \
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /opt/miniconda3/miniconda.sh && \
    bash /opt/miniconda3/miniconda.sh -b -u -p /opt/miniconda3 && \
    rm -rf /opt/miniconda3/miniconda.sh

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Create and activate conda environment, then install requirements
RUN /opt/miniconda3/bin/conda create -y -n opsmanager python=3.8 && \
    /opt/miniconda3/bin/conda init bash && \
    echo "source /opt/miniconda3/bin/activate opsmanager" >> ~/.bashrc && \
    /bin/bash -c "source /opt/miniconda3/bin/activate opsmanager && pip install --no-cache-dir -r requirements.txt"

# Create .ssh directory and set permissions
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV PATH="/opt/miniconda3/envs/opsmanager/bin:/opt/miniconda3/bin:${PATH}"

# Run the application
CMD ["bash", "-c", "source /opt/miniconda3/bin/activate opsmanager && python3 app.py"]
