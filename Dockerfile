# Use an official Python image as the base
FROM python:3.10

# Add version argument
ARG VERSION=development
ENV APP_VERSION=$VERSION

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Add version label to the image
LABEL version=$VERSION

# Run migrations and collect static files
RUN python manage.py collectstatic --noinput

# Expose the port Django runs on
EXPOSE 8000

# Command to run the app using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "backend.wsgi:application"]