FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy all code first
COPY . .

# Install dependencies with uv
RUN uv pip install --system -r requirements.txt

# Set the command to use uvicorn directly (more reliable in Docker)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]