FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir paho-mqtt==1.6.1

COPY services/shared /app/shared
COPY services/environment/service.py /app/service.py

CMD ["python", "-u", "service.py"]