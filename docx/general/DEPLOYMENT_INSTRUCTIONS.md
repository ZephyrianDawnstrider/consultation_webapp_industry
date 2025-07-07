# Deployment Instructions for Render with MSSQL Database

This document provides instructions to deploy your Django app on Render using the provided Dockerfile and connect it to an MSSQL database.

## Prerequisites

- Render account and access to your Render dashboard.
- MSSQL database server accessible from Render.
- Dockerfile present in your project root (already created).

## Steps

### 1. Set Environment Variables on Render

In your Render service settings, set the following environment variables to configure the MSSQL database connection:

- `MSSQL_DB_NAME` - Your database name (e.g., softechconsultant)
- `MSSQL_DB_USER` - Your database username (e.g., sofcunsuser)
- `MSSQL_DB_PASSWORD` - Your database password (e.g., REDACTED)
- `MSSQL_DB_HOST` - Your database server IP or hostname (e.g., REDACTED)
- `MSSQL_DB_PORT` - (Optional) Database port if not default

### 2. Deploy Using Dockerfile

- Push your code including the Dockerfile to your Git repository connected to Render.
- In Render, create a new Web Service and select the Docker environment.
- Render will build the Docker image using the Dockerfile, which installs the ODBC Driver 17 for SQL Server.
- The app will run using Gunicorn as specified in the Dockerfile.

### 3. Run Migrations

After deployment, connect to your Render instance shell or use Render's dashboard console to run:

```bash
python manage.py migrate
```

This will create the necessary tables in your MSSQL database.

### 4. Verify Deployment

- Access your app URL on Render.
- Test key functionalities that interact with the database.
- Check logs for any errors related to database connectivity.

## Notes

- The Dockerfile installs the required ODBC driver for MSSQL.
- Ensure your MSSQL server allows connections from Render IPs.
- Use environment variables to keep credentials secure and configurable.

If you need assistance with any of these steps, please reach out.

---
