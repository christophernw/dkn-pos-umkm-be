# Stage 1: Build dependencies
FROM python:3.10 AS builder

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Final runtime image
FROM python:3.10-slim

# Create non-root user
RUN useradd -m appuser

# Set working directory
WORKDIR /app

# Copy wheels from builder stage
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy project files
# Copy files that change less frequently first
COPY manage.py .
COPY backend/ backend/
COPY authentication/ authentication/
COPY produk/ produk/
COPY transaksi/ transaksi/
COPY media/ media/

# Set correct permissions
RUN chown -R appuser:appuser /app
RUN mkdir -p /app/media && chown -R appuser:appuser /app/media

# Switch to non-root user
USER appuser

# Run collectstatic
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Command to run the app using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "backend.wsgi:application"]