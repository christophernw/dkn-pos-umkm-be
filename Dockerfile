# Use an official Python image as the base
FROM python:3.10

# Create a non-root user and group
RUN groupadd -r myuser && useradd -r -g myuser myuser

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Change ownership of the working directory to the non-root user
RUN chown -R myuser:myuser /app

# Switch to the non-root user
USER myuser

# Run migrations and collect static files
RUN python manage.py collectstatic --noinput

# Expose the port Django runs on
EXPOSE 8000

# Command to run the app using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "backend.wsgi:application"]
