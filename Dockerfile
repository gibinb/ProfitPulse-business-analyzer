# Use official Python 3.13 base image
FROM python:3.13

# Set working directory inside the container
WORKDIR /app

# Copy all your project files into the container
COPY . .

# Install all dependencies
RUN pip install -r requirements.txt

# Tell Docker which port Streamlit runs on
EXPOSE 8501

# Command to run the app when the container starts
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]