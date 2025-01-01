# Use a lightweight Python image with Alpine as the base
FROM python:alpine3.12

# Set the working directory in the container
WORKDIR /app

# Copy the application files into the container
COPY requirements.txt .

# Install Flask and other dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


COPY . .

# Set environment variables
ENV FLASK_APP=app.py

# Command to start the Flask application
CMD ["flask", "run", "--host=0.0.0.0"]
