## Мониторинг парка транспортных средств (Prometheus + Grafana + MQTT)

[![Terraform](https://img.shields.io/badge/terraform-1.5+-blueviolet)](https://www.terraform.io/)
[![Docker](https://img.shields.io/badge/docker-20.10+-blue)](https://www.docker.com/)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-brightgreen)](https://github.com/features/actions)
[![Yandex Cloud](https://img.shields.io/badge/Yandex%20Cloud-COI-yellow)](https://yandex.cloud/ru/docs/cos/)

## Описание

Проект представляет собой готовое решение для развертывания системы мониторинга телеметрии парка транспортных средств (ТС) в реальном времени. Стек включает:

- MQTT-брокер (Mosquitto) – приём данных от ТС.
- MQTT-экспортер (mqtt2prometheus) – преобразование MQTT-сообщений в метрики Prometheus.
- Prometheus – сбор и хранение метрик.
- Grafana – визуализация дашбордов.
- Alertmanager – обработка оповещений.
- MAX Bot – отправка уведомлений в мессенджер MAX.
- Симуляторы ТС – генерация тестовых данных для всех типов техники (тракторы, погрузчики, роботы, тележки).

Инфраструктура разворачивается в Yandex Cloud с использованием Terraform и Container Optimized Images (COI). Обновления конфигураций и кода выполняются автоматически через GitHub Actions.

---

## Архитектура

Система состоит из двух виртуальных машин:

| ВМ | Роль | Компоненты |
|----|------|------------|
| broker-vm | Приём и обработка данных | Mosquitto, MQTT-экспортер, симуляторы ТС, Node Exporter |
| monitoring-vm | Хранение и визуализация | Prometheus, Grafana, Alertmanager, MAX Bot, Node Exporter |

**Поток данных:**
1. Симуляторы (или реальные ТС) публикуют JSON-сообщения в MQTT-топики вида `<type>/<fuel>/<id>/telemetry`.
2. MQTT-экспортер подписывается на все топики, парсит JSON и преобразует метрики в формат Prometheus.
3. Prometheus (на ВМ мониторинга) собирает метрики с экспортера по HTTP.
4. Grafana визуализирует данные, Alertmanager отправляет уведомления в MAX и на email.

---

## Быстрый старт

### 1. Предварительные требования

- Учётная запись Yandex Cloud с активированным биллингом.
- Установленные Terraform (>= 1.5) и YC CLI.
- Git и Docker (для локальной разработки).
- SSH-ключ (публичный и приватный) для доступа к ВМ.
- GitHub-репозиторий (для CI/CD).

### 2. Клонирование репозитория

```bash
git clone https://github.com/aleksey-dubrovin/monitoring-mqtt2.git
cd monitoring-mqtt2
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
yc_registry_id   = "crp12345"

public_ssh_key_path = "~/.ssh/id_rsa.pub"
use_preemptible     = true

broker_vm_cores     = 2
broker_vm_memory    = 4
broker_vm_disk_size = 30
monitoring_vm_cores = 2
monitoring_vm_memory    = 4
monitoring_vm_disk_size = 30

grafana_password = "admin"
yandex_email     = "aleksey.vladch@yandex.ru"
yandex_app_password  = ""   # Заполните паролем приложения Яндекс.Почты
max_bot_token    = ""       # Заполните токеном MAX бота
max_chat_id      = ""       # Заполните chat_id из MAX
max_use_bearer   = false
```

**Важно:** файл `terraform.tfvars` содержит секреты и не должен попадать в Git (он уже в `.gitignore`).

### 4. Развертывание инфраструктуры

```bash
terraform init
terraform plan
terraform apply -auto-approve
```

После успешного выполнения в выводе будут показаны:
- Публичные IP-адреса обеих ВМ.
- URL для доступа к Grafana и Prometheus.

> **Примечание:** Первичное развертывание занимает 3–5 минут. Cloud-init клонирует репозиторий, создаёт `.env` файлы и запускает `docker-compose`.

### 5. Проверка работоспособности

- Откройте Grafana: `https://<monitoring-public-ip>:3000` (логин `admin`, пароль `admin` – смените при первом входе).
- Проверьте, что в Prometheus (раздел Targets) все эндпоинты имеют статус UP.
- Через несколько секунд симуляторы начнут отправлять данные – на дашбордах появятся графики.

---

## Настройка секретов GitHub

Для работы CI/CD необходимо добавить следующие секреты в репозиторий (**Settings -> Secrets and variables -> Actions**):

| Секрет | Описание |
|--------|----------|
| `YC_SA_JSON_CREDENTIALS` | JSON-ключ сервисного аккаунта с правами на `container-registry.images.pusher` |
| `YC_CLOUD_ID` | ID облака |
| `YC_FOLDER_ID` | ID каталога |
| `YC_REGISTRY_ID` | ID созданного Container Registry |
| `BROKER_VM_IP` | Публичный IP ВМ-брокера (из вывода Terraform) |
| `MONITORING_VM_IP` | Публичный IP ВМ-мониторинга |
| `VM_SSH_PRIVATE_KEY` | Приватный SSH-ключ (содержимое файла `~/.ssh/id_rsa`) |

> **Рекомендация:** Используйте Yandex Lockbox для хранения паролей и токенов вместо хранения их в коде или секретах GitHub.

---

## CI/CD – Автоматические обновления

GitHub Actions настроены на триггеры при пуше в ветку `main`:

| Workflow | Триггер (изменения в) | Действие |
|----------|-----------------------|------------|
| build-simulator | `simulator/**` | Сборка и пуш образа симулятора в Container Registry, перезапуск контейнеров на broker-vm |
| build-max-bot | `max-bot/**` | Сборка и пуш образа MAX Bot в Container Registry, перезапуск контейнеров на monitoring-vm |
| deploy-broker | `docker-compose/broker.yml`, `mosquitto/**` | git pull, перезапуск брокерских контейнеров |
| deploy-monitoring | `docker-compose/monitoring.yml`, `prometheus/**`, `grafana/**`, `alertmanager/**` | git pull, перезапуск мониторинговых контейнеров |

Данные (метрики, дашборды, настройки) сохраняются благодаря использованию Docker-томов.

---

## Структура репозитория

```
monitoring-mqtt2/
├── .github/workflows/         # CI/CD пайплайны
├── terraform/                 # Инфраструктура как код
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars.example
│   ├── cloud-init-broker.tpl
│   └── cloud-init-monitoring.tpl
├── docker-compose/            # Docker Compose файлы для двух ВМ
│   ├── broker.yml
│   └── monitoring.yml
├── simulator/                 # Код симулятора ТС
│   ├── Dockerfile
│   ├── requirements.txt
│   └── simulator.py
├── max-bot/                   # Сервис для отправки в MAX
│   ├── Dockerfile
│   ├── max_bot.py
│   └── requirements.txt
├── prometheus/                # Конфигурация Prometheus
│   ├── prometheus.yml
│   └── alerts.yml
├── grafana/                   # Provisioning дашбордов и datasource
│   ├── grafana.ini
│   ├── provisioning/
│   │   ├── datasources/
│   │   ├── dashboards/
│   │   └── alerting/
│   └── dashboards/
├── mosquitto/                 # Конфигурация MQTT брокера
│   └── config/
├── alertmanager/              # Конфигурация Alertmanager
│   └── alertmanager.yml
├── mqtt2prometheus/           # Конфигурация MQTT-экспортера
│   └── config.yaml
├── .gitignore
└── README.md
```

---

## Дашборды

В репозитории предустановлены дашборды (Grafana provisioning):

- **Состояние парка** – общая статистика по всем ТС (количество, активность, средняя скорость, заряд батарей).
- **Детальный статус ТС** – анализ конкретного ТС с выбором по `sensor`. Включает графики скорости, GPS-трека, температуры, статуса RTK, уровня топлива/заряда, угла поворота, сигнала LTE.
- **Серверная инфраструктура** – загрузка CPU/RAM/Disk для обеих ВМ, доступность сервисов.

Дашборды интерактивны: есть фильтры по времени, выбор ТС (`$sensor`), возможность детализации.

---

## Алерты

В `prometheus/alerts.yml` предопределены правила:

- **VehicleOffline** – потеря связи с ТС > 5 минут (critical)
- **HighCpuTemperature** – температура CPU > 75°C (warning)
- **RtkLost** – статус RTK = None более 30 секунд (warning)
- **LowBattery** – заряд батареи < 20% (warning)
- **LowFuel** – уровень топлива < 15% (warning)
- **HighCpuUsage** – загрузка CPU > 90% (critical)
- **ServiceDown** – сервис недоступен (critical)

Уведомления отправляются через Alertmanager. Настроены два канала:

1. **MAX Bot** – основной канал для всех алертов.
2. **Email** – дублирование critical алертов на `aleksey.vladch@yandex.ru` (требуется пароль приложения Яндекс.Почты).

Для настройки MAX Bot:

1. Создайте бота в MAX и получите токен и `chat_id`.
2. Заполните переменные `max_bot_token` и `max_chat_id` в `terraform.tfvars`.
3. После развертывания проверьте логи: `docker logs max-bot`.

---

## Переменные окружения

Все чувствительные данные вынесены в переменные окружения (`.env` файлы на ВМ и в `terraform.tfvars`).

На ВМ мониторинга создаётся `/opt/monitoring/docker-compose/.env` со следующим содержимым (генерируется cloud-init):

```bash
GRAFANA_PASSWORD=admin
YANDEX_APP_PASSWORD=пароль_приложения
MAX_BOT_TOKEN=токен_бота
MAX_CHAT_ID=chat_id
MAX_USE_BEARER=false
YANDEX_EMAIL=aleksey.vladch@yandex.ru
```

На ВМ брокера:

```bash
YC_REGISTRY_ID=crpc19jo0hah8k1p37dj
MONITORING_PRIVATE_IP=monitoring   # используется имя хоста вместо IP
```

---

## Безопасность

- Метаданные ВМ содержат `user-data` (cloud-init) и `ssh-keys`.
- Security Groups ограничивают доступ:
  - MQTT (1883) – только внутренние подсети.
  - MQTT-экспортер (9200) – только подсеть мониторинга.
  - SSH (22) – открыт по необходимости.
- Grafana HTTPS – включён с использованием самоподписанного сертификата (генерируется в cloud-init).
- Docker-контейнеры работают от непривилегированных пользователей.
- .gitignore исключает файлы с секретами (`terraform.tfvars`, `*.env`, `*.tfstate`, `ddns/`, `max-bot/`).

---

## Тестирование уведомлений

Для проверки отправки алертов:

```bash
# Отправить тестовый алерт в Alertmanager
curl -X POST -H "Content-Type: application/json" \
  -d '[{"status":"firing","labels":{"alertname":"TestAlert","severity":"warning"},"annotations":{"summary":"Test","description":"Check MAX"}}]' \
  http://localhost:9093/api/v2/alerts
```

Проверьте логи MAX Bot и почту.

---

## Устранение неполадок

| Проблема | Действие |
|----------|----------|
| Cloud-init не выполняется | Проверьте логи: `sudo cat /var/log/cloud-init-output.log` |
| Контейнеры не запускаются | Проверьте логи: `docker logs <container>` |
| Нет данных в дашбордах | Убедитесь, что симуляторы работают и MQTT-экспортер собирает метрики |
| MAX Bot не отправляет | Проверьте токен и chat_id в `.env` |
| Ошибка `permission denied` в Grafana | Исправьте права: `sudo chown -R 472:472 /opt/monitoring/grafana` |

---

## Вклад

Если у вас есть предложения по улучшению проекта – создавайте issue или pull request.

---

## Лицензия

Проект распространяется под лицензией MIT. Подробности см. в файле LICENSE.
