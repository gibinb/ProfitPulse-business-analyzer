# Use official Python 3.13 slim image (smaller & faster)
FROM python:3.13-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (better layer caching)
COPY requirements.txt .

# Install all dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Tell Docker which port Streamlit runs on
EXPOSE 8501

# Command to run the app when the container starts
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]