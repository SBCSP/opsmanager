# OpsManager

OpsManager is a comprehensive application designed for system administrators and DevOps engineers to manage and automate tasks across a network of servers. It integrates Ansible for configuration management and task automation, uses Azure Entra ID for authentication, and relies on a PostgreSQL database. The backend is powered by Flask and uses SQLAlchemy for object-relational mapping. The application also features a secure vault for file uploads and configurations.

# Coming Soon 🎉🎈
Exciting new features are on the way:

- Deploying and Managing Docker Containers: Simplify your Docker operations with integrated management tools.
- ClamAV Setup and Monitoring: Enhance security with automated virus scanning setups and monitoring.
- Porting over Kronosys Code for Server Monitoring: Implement comprehensive server monitoring from Kronosys.
- Stay tuned for these updates and more enhancements to improve your administrative workflows!

## Features

- **Ansible Integration**: Automate configurations and management tasks across servers.
- **Azure Entra ID Authentication**: Secure user authentication leveraging Azure AD.
- **PostgreSQL Database**: Robust database management with PostgreSQL.
- **Flask Python Framework**: Lightweight and modular web server gateway interface application.
- **SQLAlchemy ORM**: Object-relational mapping for database access.
- **File Vault**: Secure storage for configuration files and sensitive data.

## Getting Started

### Prerequisites

- Docker Engine (Docker Compose v2)
- Python 3.10+ (App was built using Miniconda Environments: https://docs.anaconda.com/free/miniconda/#quick-command-line-install)
- PostgreSQL - Compose file database/postgres-compose.yml
- Ansible (ansible [core 2.16.6])
- MSAL Python Library for Azure AD integration - Need an App Registered in your Azure Tenant
- Flask and its extensions (requirements.txt)

### Installation

   ```bash
   # Setup Miniconda environment
   conda create -n opsmanager python=3.10
   conda activate opsmanager

   # Clone repo
   git clone https://github.com/yourrepository/myapp.git
   cd opsmanager

   # Install dependencies 
   pip install -r requirements.txt
   cp .env.example .env

   docker compose -f database/postgres-compose.yml up -d
   # Edit .env file to include DATABASE_URL=postgresql://opsmanager:opsmanager@localhost:5432/opsmanager
   
   # Initialize database
   flask db init
   flask db migrate -m "Initial setup"
   flask db upgrade

   # Start application
   ./startup.sh
   
   ```

# Setup

Once you've completed the installation steps. Navigate to the ip:5000 where the app is running and complete the setup.
- This is where you'll need your Azure App Registration details.
- Once you've Saved Configuration - you'll be routed to the app for signin!

![OpsManager Setup](./app/static/OpsManagerSetup.png)


# Troubleshooting

- If you used the ./startup.sh script to start the OpsManager application. 
- A log file called flask_app.log will be created "/app/flask_app.log"
- This log is active while the app is running. All logged activities are here.

![FlaskApp Logs](./app/static/flask_app_log.png)