FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir flask flask-socketio eventlet numpy

# Create package directories
RUN mkdir -p environment mape_k utils

# Copy environment components
COPY services/environment/grid_world.py ./environment/
COPY services/environment/robot.py ./environment/

# Copy MAPE-K components
COPY services/knowledge/knowledge.py ./mape_k/
COPY services/monitor/monitor.py ./mape_k/
COPY services/analyze/analyze.py ./mape_k/
COPY services/plan/plan.py ./mape_k/
COPY services/execute/execute.py ./mape_k/

# Copy utils
COPY services/plan/pathfinding.py ./utils/

# Create __init__.py files
RUN touch environment/__init__.py mape_k/__init__.py utils/__init__.py

# Copy web app
COPY services/web/app.py .
COPY services/web/templates/ ./templates/

EXPOSE 5000
CMD ["python", "app.py"]