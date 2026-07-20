#!/usr/bin/env python3
import json
import random
import time
import logging
import os
import threading
from typing import Dict, Any, List, Optional
import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VehicleSimulator:
    """
    Симулятор транспортного средства согласно протоколу телеметрии.
    Поддерживает: tractor, forklift, cart, robot.
    """

    VEHICLE_TYPES = {
        "tractor": {
            "fuel_types": ["diesel"],
            "specific_metrics": ["engine_rpm", "fuel_level_pct", "temp_c", "oil_pressure_bar", "engine_hours"]
        },
        "forklift": {
            "fuel_types": ["electric"],
            "specific_metrics": ["battery_soc_pct", "battery_temp_c", "current_a", "voltage_v"]
        },
        "cart": {
            "fuel_types": ["electric"],
            "specific_metrics": ["battery_soc_pct", "battery_temp_c", "current_a", "voltage_v"]
        },
        "robot": {
            "fuel_types": ["electric"],
            "specific_metrics": [
                "mode", "mission_status", "mission_id", "estop_status",
                "rtk_status", "steering_angle_deg", "temp_cpu_c", "lte_rssi"
            ]
        }
    }

    def __init__(self, vehicle_id: int, vehicle_type: str, fuel_type: str):
        self.vehicle_id = str(vehicle_id)
        self.vehicle_type = vehicle_type
        self.fuel_type = fuel_type
        self.topic = f"{vehicle_type}/{fuel_type}/{vehicle_id}/telemetry"

        if fuel_type not in self.VEHICLE_TYPES.get(vehicle_type, {}).get("fuel_types", []):
            logger.warning(
                f"Нестандартная комбинация: {vehicle_type}/{fuel_type}. "
                f"Допустимые: {self.VEHICLE_TYPES.get(vehicle_type, {}).get('fuel_types', [])}"
            )

        self.base_lat = 55.7558 + random.uniform(-0.05, 0.05)
        self.base_lon = 37.6173 + random.uniform(-0.05, 0.05)
        self.is_moving = True
        self.direction = random.uniform(0, 360)

        logger.info(f"Инициализирован симулятор: {self.topic}")

    def generate_common_metrics(self) -> Dict[str, Any]:
        if self.is_moving:
            self.base_lat += random.uniform(-0.0005, 0.0005)
            self.base_lon += random.uniform(-0.0005, 0.0005)

        return {
            "gps_lat": round(self.base_lat, 6),
            "gps_lon": round(self.base_lon, 6),
            "gps_alt": round(random.uniform(10, 25), 1),
            "speed_kmh": round(random.uniform(0, 30) if self.is_moving else 0, 1),
            "engine_status": "on" if self.is_moving else random.choice(["on", "off"])
        }

    def generate_specific_metrics(self) -> Dict[str, Any]:
        if self.vehicle_type == "tractor":
            return {
                "engine_rpm": random.randint(800, 2200),
                "fuel_level_pct": random.randint(10, 95),
                "temp_c": round(random.uniform(60, 95), 1),
                "oil_pressure_bar": round(random.uniform(1.5, 4.0), 1),
                "engine_hours": round(random.uniform(1000, 5000), 1)
            }
        elif self.vehicle_type in ["forklift", "cart"]:
            return {
                "battery_soc_pct": random.randint(20, 100),
                "battery_temp_c": round(random.uniform(20, 45), 1),
                "current_a": round(random.uniform(10, 200), 1),
                "voltage_v": round(random.uniform(24, 52), 1)
            }
        elif self.vehicle_type == "robot":
            modes = ["idle", "human", "teleop", "supervis", "autonom"]
            mission_statuses = ["none", "pause", "run", "complete", "abort"]
            rtk_statuses = ["fix", "float", "none"]
            return {
                "mode": random.choice(modes),
                "mission_status": random.choice(mission_statuses),
                "mission_id": str(random.randint(1, 100)),
                "estop_status": random.choice(["on", "off"]),
                "rtk_status": random.choice(rtk_statuses),
                "steering_angle_deg": round(random.uniform(-30, 30), 1),
                "temp_cpu_c": round(random.uniform(40, 80), 1),
                "lte_rssi": random.randint(-90, -40)
            }
        return {}

    def generate_events(self) -> List[Dict[str, Any]]:
        events = []
        if random.random() < 0.1:
            event_types_map = {
                "tractor": ["fuel_low", "engine_overheat", "oil_pressure_low"],
                "forklift": ["battery_low", "motor_overheat", "charger_fault"],
                "cart": ["battery_low", "motor_overheat"],
                "robot": ["estop_triggered", "mission_failed", "rtk_lost", "battery_low"]
            }
            severities = ["info", "warning", "error", "critical"]
            weights = [0.4, 0.3, 0.2, 0.1]

            event_type = random.choice(event_types_map.get(self.vehicle_type, ["general"]))
            severity = random.choices(severities, weights=weights)[0]

            descriptions = {
                "fuel_low": "Уровень топлива ниже 10%",
                "engine_overheat": "Температура двигателя превышает норму",
                "oil_pressure_low": "Давление масла ниже нормы",
                "battery_low": "Уровень заряда батареи ниже 20%",
                "motor_overheat": "Температура мотора превышает норму",
                "charger_fault": "Ошибка зарядного устройства",
                "estop_triggered": "Аварийная остановка активирована",
                "mission_failed": "Ошибка выполнения миссии",
                "rtk_lost": "Потеря RTK сигнала",
                "general": "Общее событие"
            }

            event = {
                "event_type": event_type,
                "severity": severity,
                "timestamp": int(time.time() * 1000),
                "description": descriptions.get(event_type, "Сгенерированное событие"),
                "code": random.randint(1000, 9999)
            }
            events.append(event)
        return events

    def generate_payload(self) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "vehicle_id": self.vehicle_id,
            "vehicle_type": self.vehicle_type,
            "fuel_type": self.fuel_type,
            "timestamp": int(time.time() * 1000),
            "metrics": {
                **self.generate_common_metrics(),
                **self.generate_specific_metrics()
            },
            "events": self.generate_events()
        }

    def run(self, broker_host: str = "mosquitto", interval: int = 5):
        client = mqtt.Client()
        try:
            client.connect(broker_host, 1883, 60)
        except Exception as e:
            logger.error(f"Не удалось подключиться к MQTT брокеру {broker_host}: {e}")
            return

        logger.info(f"Симулятор {self.topic} подключен к MQTT брокеру")

        while True:
            try:
                payload = self.generate_payload()
                client.publish(self.topic, json.dumps(payload))
                logger.debug(f"Отправлено в {self.topic}")
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Ошибка в симуляторе {self.topic}: {e}")
                time.sleep(interval)


def get_fleet_config() -> List[Dict[str, Any]]:
    fleet = [
        {"id": 1, "type": "tractor", "fuel": "diesel"},
        {"id": 2, "type": "tractor", "fuel": "diesel"},
        {"id": 3, "type": "tractor", "fuel": "diesel"},
        {"id": 4, "type": "forklift", "fuel": "electric"},
        {"id": 5, "type": "forklift", "fuel": "electric"},
        {"id": 6, "type": "robot", "fuel": "electric"},
        {"id": 7, "type": "robot", "fuel": "electric"},
        {"id": 8, "type": "robot", "fuel": "electric"},
        {"id": 9, "type": "cart", "fuel": "electric"},
        {"id": 10, "type": "cart", "fuel": "electric"},
    ]
    env_config = os.getenv("FLEET_CONFIG")
    if env_config:
        try:
            fleet = json.loads(env_config)
            logger.info(f"Конфигурация парка загружена из переменной окружения: {len(fleet)} ТС")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга FLEET_CONFIG: {e}. Использую стандартную конфигурацию.")
    return fleet


def main():
    broker_host = os.getenv("MQTT_BROKER_HOST", "mosquitto")
    interval = int(os.getenv("SIMULATOR_INTERVAL", "5"))

    fleet = get_fleet_config()
    logger.info(f"Запуск {len(fleet)} симуляторов. Брокер: {broker_host}, интервал: {interval}с")

    threads = []
    for vehicle_config in fleet:
        simulator = VehicleSimulator(
            vehicle_id=vehicle_config["id"],
            vehicle_type=vehicle_config["type"],
            fuel_type=vehicle_config["fuel"]
        )
        thread = threading.Thread(
            target=simulator.run,
            args=(broker_host, interval),
            daemon=True
        )
        thread.start()
        threads.append(thread)
        logger.info(f"Запущен симулятор: {vehicle_config['type']} #{vehicle_config['id']}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Остановка симуляторов...")


if __name__ == "__main__":
    main()