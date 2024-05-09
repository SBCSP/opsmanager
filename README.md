# OpsManager

OpsManager is a comprehensive application designed for system administrators and DevOps engineers to manage and automate tasks across a network of servers. It integrates Ansible for configuration management and task automation, uses Azure Entra ID for authentication, and relies on a PostgreSQL database. The backend is powered by Flask and uses SQLAlchemy for object-relational mapping. The application also features a secure vault for file uploads and configurations.

## Features

- **Ansible Integration**: Automate configurations and management tasks across servers.
- **Azure Entra ID Authentication**: Secure user authentication leveraging Azure AD.
- **PostgreSQL Database**: Robust database management with PostgreSQL.
- **Flask Python Framework**: Lightweight and modular web server gateway interface application.
- **SQLAlchemy ORM**: Object-relational mapping for database access.
- **File Vault**: Secure storage for configuration files and sensitive data.

## Getting Started

### Prerequisites

- Docker Engine
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
   
   docker compose -f database/postgres-compose.yml up -d
   flask db init
   flask db migrate -m "Initial setup"
   flask db upgrade

   python app.py
   
```

# Setup

Once you've completed the installation steps. Navigate to the ip:5000 where the app is running and compelete the setup.
- This is where you'll need your Azure App Registration details.
- Once you've Saved Configuration - you'll be routed to the app for signin!

![OpsManager Setup](./app/vault_items/OpsManagerSetup.png)

