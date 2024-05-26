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

- Python 3.10+
- PostgreSQL - Compose file database/postgres-compose.yml
- Ansible
- MSAL Python Library for Azure AD integration - Need an App Registered in your Azure Tenant
- Flask and its extensions (requirements.txt)

### Installation

   ```bash
   git clone https://github.com/yourrepository/myapp.git
   cd opsmanager
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env file to include DATABASE_URL=postgresql://opsmanager:opsmanager@localhost:5432/opsmanager
   
   flask db init
   flask db migrate -m "Initial setup"
   flask db upgrade

   ./startup.sh
   
   ```

# Setup

Once you've completed the installation steps. Navigate to the ip:5000 where the app is running and complete the setup.
- This is where you'll need your Azure App Registration details.
- Once you've Saved Configuration - you'll be routed to the app for signin!

![OpsManager Setup](./app/vault_items/OpsManagerSetup.png)


