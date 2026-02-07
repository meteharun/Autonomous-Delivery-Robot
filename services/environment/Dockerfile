FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir paho-mqtt==1.6.1
COPY config.json /app/config.json
COPY services/environment/service.py /app/service.py
CMD ["python", "-u", "service.py"]