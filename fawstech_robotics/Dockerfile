# D:\production\fawstech_website\fawstech_robotics\Dockerfile

FROM python:3.9

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000


CMD ["sh", "-c", "python3.9 manage.py makemigrations && python3.9 manage.py migrate && python3.9 manage.py runserver 0.0.0.0:8000"]

# CMD ["sh", "-c", "python3.9 manage.py runserver 0.0.0.0:8000"]




