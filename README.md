# Мониторинг парка транспортных средств (Prometheus + Grafana + MQTT)

[![Terraform](https://img.shields.io/badge/terraform-1.5+-blueviolet)](https://www.terraform.io/)
[![Docker](https://img.shields.io/badge/docker-20.10+-blue)](https://www.docker.com/)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-brightgreen)](https://github.com/features/actions)
[![Yandex Cloud](https://img.shields.io/badge/Yandex%20Cloud-COI-yellow)](https://yandex.cloud/ru/docs/cos/)

## 📋 Описание

Проект представляет собой готовое решение для развертывания системы мониторинга телеметрии парка транспортных средств (ТС) в реальном времени. Стек включает:

- **MQTT-брокер (Mosquitto)** – приём данных от ТС.
- **MQTT-экспортер (squirreldb-ingestor)** – преобразование MQTT-сообщений в метрики Prometheus.
- **Prometheus** – сбор и хранение метрик.
- **Grafana** – визуализация дашбордов.
- **Alertmanager** – обработка оповещений.
- **Симуляторы ТС** – генерация тестовых данных для всех типов техники (тракторы, погрузчики, роботы, тележки).

Инфраструктура разворачивается в **Yandex Cloud** с использованием **Terraform** и **Container Optimized Images (COI)**. Обновления конфигураций и кода выполняются автоматически через **GitHub Actions**.

---

## 🏗 Архитектура

Система состоит из двух виртуальных машин:

| ВМ | Роль | Компоненты |
|----|------|------------|
| **broker-vm** | Приём и обработка данных | Mosquitto, MQTT-экспортер, симуляторы ТС, Node Exporter |
| **monitoring-vm** | Хранение и визуализация | Prometheus, Grafana, Alertmanager, Node Exporter |

**Поток данных:**
1. Симуляторы (или реальные ТС) публикуют JSON-сообщения в MQTT-топики вида `<type>/<fuel>/<id>/telemetry`.
2. MQTT-экспортер подписывается на все топики, парсит JSON и преобразует метрики в формат Prometheus.
3. Prometheus (на ВМ мониторинга) собирает метрики с экспортера по HTTP.
4. Grafana визуализирует данные, Alertmanager отправляет оповещения.

---

## 🚀 Быстрый старт

### 1. Предварительные требования

- Учётная запись **Yandex Cloud** с активированным биллингом.
- Установленные **Terraform** (>= 1.5) и **YC CLI**.
- **Git** и **Docker** (для локальной разработки).
- **SSH-ключ** (публичный и приватный) для доступа к ВМ.
- **GitHub-репозиторий** (для CI/CD).

### 2. Клонирование репозитория

```bash
git clone https://github.com/aleksey-dubrovin/monitoring-mqtt.git
cd monitoring-mqtt
```

### 3. Настройка Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Отредактируйте `terraform.tfvars`, указав свои данные:
```hcl
yc_token         = "YOUR_OAUTH_TOKEN"
yc_cloud_id      = "YOUR_CLOUD_ID"
yc_folder_id     = "YOUR_FOLDER_ID"
yc_zone          = "ru-central1-a"
public_ssh_key_path = "~/.ssh/id_rsa.pub"
```

### 4. Развертывание инфраструктуры

```bash
terraform init
terraform plan
terraform apply -auto-approve
```

После успешного выполнения в выводе будут показаны:
- Публичные IP-адреса обеих ВМ.
- URL для доступа к Grafana и Prometheus.

> **Примечание:** Первичное развертывание занимает 3–5 минут. Cloud-init клонирует репозиторий и запускает `docker-compose`.

### 5. Проверка работоспособности

- Откройте Grafana: `http://<monitoring-public-ip>:3000` (логин `admin`, пароль `admin` – смените при первом входе).
- Проверьте, что в Prometheus (раздел Targets) все эндпоинты имеют статус **UP**.
- Через несколько секунд симуляторы начнут отправлять данные – на дашбордах появятся графики.

---

## 🔐 Настройка секретов GitHub

Для работы CI/CD необходимо добавить следующие секреты в репозиторий (**Settings → Secrets and variables → Actions**):

| Секрет | Описание |
|--------|----------|
| `YC_SA_JSON_KEY` | JSON-ключ сервисного аккаунта с правами на `container-registry.images.pusher` |
| `YC_CLOUD_ID` | ID облака |
| `YC_FOLDER_ID` | ID каталога |
| `YC_REGISTRY_ID` | ID созданного Container Registry (создаётся автоматически через Terraform или вручную) |
| `BROKER_VM_IP` | Публичный IP ВМ-брокера (из вывода Terraform) |
| `MONITORING_VM_IP` | Публичный IP ВМ-мониторинга |
| `VM_SSH_PRIVATE_KEY` | Приватный SSH-ключ (содержимое файла `~/.ssh/id_rsa`) |

> **Рекомендация:** Используйте **Yandex Lockbox** для хранения паролей и токенов вместо хранения их в коде или секретах GitHub. Пример настройки Lockbox есть в [документации](https://yandex.cloud/ru/docs/lockbox/).

---

## 🔄 CI/CD – Автоматические обновления

GitHub Actions настроены на триггеры при пуше в ветку `main`:

| Workflow | Триггер (изменения в) | Действие |
|----------|-----------------------|----------|
| **build-simulator** | `simulator/**` | Сборка и пуш образа симулятора в Container Registry, перезапуск контейнеров на broker-vm |
| **deploy-broker** | `docker-compose/broker.yml`, `mosquitto/**` | `git pull`, перезапуск брокерских контейнеров |
| **deploy-monitoring** | `docker-compose/monitoring.yml`, `prometheus/**`, `grafana/**`, `alertmanager/**` | `git pull`, перезапуск мониторинговых контейнеров |

Данные (метрики, дашборды, настройки) сохраняются благодаря использованию Docker-томов. При обновлениях тома не удаляются.

---

## 📂 Структура репозитория

```
.
├── .github/workflows/         # CI/CD пайплайны
├── terraform/                 # Инфраструктура как код
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars.example
│   ├── cloud-init-broker.yaml
│   └── cloud-init-monitoring.yaml
├── docker-compose/            # Docker Compose файлы для двух ВМ
│   ├── broker.yml
│   └── monitoring.yml
├── simulator/                 # Код симулятора ТС
│   ├── Dockerfile
│   ├── requirements.txt
│   └── simulator.py
├── prometheus/                # Конфигурация Prometheus
│   ├── prometheus.yml
│   └── alerts.yml
├── grafana/                   # Provisioning дашбордов и datasource
│   └── provisioning/
│       ├── datasources/
│       └── dashboards/
├── mosquitto/                 # Конфигурация MQTT брокера
│   └── config/
├── alertmanager/              # Конфигурация Alertmanager
│   └── alertmanager.yml
├── .gitignore
└── README.md
```

---

## 📊 Дашборды

В репозитории предустановлены базовые дашборды (Grafana provisioning). После запуска в Grafana появятся панели:

- **«Состояние парка»** – онлайн/офлайн статус ТС, последние GPS-координаты.
- **«Детальный статус трактора»** – графики скорости, температуры, уровня топлива и других метрик (доступно переключение по `device_id`).
- **«Серверная инфраструктура»** – загрузка CPU/RAM, состояние дисков, доступность сервисов.

Вы можете модифицировать дашборды в папке `grafana/dashboards/` – изменения автоматически подхватятся после пуша (если настроен `updateIntervalSeconds`).

---

## ⚠️ Алерты

В `prometheus/alerts.yml` предопределены следующие правила:

- Потеря связи с ТС > 5 минут (`VehicleOffline`)
- Температура вычислителя > 75°C (`HighTemperature`)
- Статус RTK = None более 30 секунд (`RtkLost`)
- Низкий заряд батареи (<20%) (`BatteryLow`)
- Высокая загрузка CPU (>90% на 5 мин) для серверов (`HighCpuUsage`)

Оповещения отправляются через Alertmanager. Для настройки Telegram-бота раскомментируйте соответствующий раздел в `alertmanager/alertmanager.yml` и укажите токен и chat_id.

---

## 🛠 Локальная разработка

Для тестирования симулятора локально (без облака):

```bash
cd simulator
pip install -r requirements.txt
python simulator.py
```

При необходимости можно запустить полный стек локально через Docker Compose:

```bash
docker-compose -f docker-compose/broker.yml up -d
docker-compose -f docker-compose/monitoring.yml up -d
```

---

## 📖 Полезные ссылки

- [Протокол телеметрии](Описание протокола телеметрии_v2.docx)
- [Yandex Cloud COI + Terraform](https://yandex.cloud/ru/docs/cos/tutorials/coi-with-terraform)
- [Mosquitto](https://mosquitto.org/)
- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)

---

## 🤝 Вклад

Если у вас есть предложения по улучшению проекта – создавайте issue или pull request. Мы открыты к сотрудничеству.

---

## 📄 Лицензия

Данный проект распространяется под лицензией MIT. Подробности см. в файле LICENSE.

---

**Удачного мониторинга!** 🚜📊