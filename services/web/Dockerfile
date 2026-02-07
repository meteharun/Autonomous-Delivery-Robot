FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir flask flask-socketio eventlet paho-mqtt==1.6.1
COPY config.json /app/config.json
COPY services/web/service.py /app/service.py
COPY services/web/templates /app/templates
EXPOSE 5000
CMD ["python", "-u", "service.py"]