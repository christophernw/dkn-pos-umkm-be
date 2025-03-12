# Use an official Python image as the base
FROM python:3.10

# Set the working directory in the container
WORKDIR /app

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy the dependencies file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files, relying on .dockerignore to exclude sensitive data
COPY manage.py .
COPY *.py .
COPY */ */

# Run migrations and collect static files
RUN python manage.py collectstatic --noinput

# Set proper permissions for the new user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose the port Django runs on
EXPOSE 8000

# Command to run the app
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "backend.wsgi:application"]