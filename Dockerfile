FROM python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file from your local project to the working directory in the container
COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=EC_Analysis.settings
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "EC_Analysis.wsgi:application"]
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
