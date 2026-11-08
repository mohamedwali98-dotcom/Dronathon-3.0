# SKYFORGE decision stack + ground station.
# Runs the full autonomous mission (orchestrator, planner, RTH, comms) in the 2D simulator,
# then serves the 4 detection maps.   docker compose up   ->  http://localhost:8000
# Webots (3D) runs on the host: see sim/webots/README.md.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 GROUND_HOST=0.0.0.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY comms/ comms/
COPY config/ config/
COPY drone/ drone/
COPY ground/ ground/
COPY sim/__init__.py sim/kinematic.py sim/scenario.py sim/

EXPOSE 8000
CMD ["python", "-m", "ground.demo"]
