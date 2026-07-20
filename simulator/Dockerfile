FROM python:3.9-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulator.py .

ENV MQTT_BROKER_HOST=mosquitto
ENV SIMULATOR_INTERVAL=5

CMD ["python", "-u", "simulator.py"]