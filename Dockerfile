# Use an official Python runtime as a base image
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file from your local project to the working directory in the container
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of your project files into the container
COPY . .

# Set environment variables for Django
ENV DJANGO_SETTINGS_MODULE=EC_Analysis.settings
ENV PYTHONUNBUFFERED=1

# Expose port 8000
EXPOSE 8000

# Remove migration and collectstatic steps since you're not using a database
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "EC_Analysis.wsgi:application"]
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
