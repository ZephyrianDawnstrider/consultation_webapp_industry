# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install dependencies for ODBC Driver 17 for SQL Server
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    apt-transport-https \
    unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/11/prod.list | tee /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get -o Dpkg::Options::="--force-overwrite" install -y msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Set environment variables for production
ENV DEBUG=False
ENV SECRET_KEY=django-insecure-production-key-change-this-in-production
ENV ALLOWED_HOSTS=consultant-webapp.onrender.com,*

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port 8000
EXPOSE 8000

# Run the Django development server
CMD ["gunicorn", "consultant_webapp.wsgi:application", "--bind", "0.0.0.0:8000"]
