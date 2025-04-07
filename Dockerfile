FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make sure the firebase key is in the right place
RUN mkdir -p firebase
COPY firebase/firebase-key.json firebase/

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD ["uvicorn", "mcp_network_server:app", "--host", "0.0.0.0", "--port", "8080"]
