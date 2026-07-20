terraform {
  required_version = ">= 1.5.0"
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.85.0"
    }
  }
}

provider "yandex" {
  token     = var.yc_token
  cloud_id  = var.yc_cloud_id
  folder_id = var.yc_folder_id
  zone      = var.yc_zone
}

data "yandex_compute_image" "container-optimized-image" {
  family = "container-optimized-image"
}

# ======================== СЕТЬ ========================

resource "yandex_vpc_network" "monitoring" {
  name = "monitoring-network"
}

resource "yandex_vpc_subnet" "broker_subnet" {
  name           = "broker-subnet"
  zone           = var.yc_zone
  network_id     = yandex_vpc_network.monitoring.id
  v4_cidr_blocks = ["10.0.1.0/24"]
}

resource "yandex_vpc_subnet" "monitoring_subnet" {
  name           = "monitoring-subnet"
  zone           = var.yc_zone
  network_id     = yandex_vpc_network.monitoring.id
  v4_cidr_blocks = ["10.0.2.0/24"]
}

# ======================== ГРУППЫ БЕЗОПАСНОСТИ ========================

# Группа безопасности для ВМ-брокера
resource "yandex_vpc_security_group" "broker_sg" {
  name        = "broker-security-group"
  description = "Security group for MQTT broker VM"
  network_id  = yandex_vpc_network.monitoring.id

  ingress {
    protocol       = "TCP"
    description    = "SSH"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 22
  }

  ingress {
    protocol       = "TCP"
    description    = "MQTT (internal only)"
    v4_cidr_blocks = ["10.0.0.0/16"]   # только внутренние подсети
    port           = 1883
  }

  ingress {
    protocol       = "TCP"
    description    = "MQTT-Exporter metrics (for Prometheus)"
    v4_cidr_blocks = ["10.0.2.0/24"]   # только подсеть мониторинга
    port           = 9200
  }

  ingress {
    protocol       = "TCP"
    description    = "Node Exporter"
    v4_cidr_blocks = ["10.0.0.0/16"]
    port           = 9100
  }

  egress {
    protocol       = "ANY"
    description    = "Allow all outgoing"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# Группа безопасности для ВМ-мониторинга
resource "yandex_vpc_security_group" "monitoring_sg" {
  name        = "monitoring-security-group"
  description = "Security group for monitoring VM"
  network_id  = yandex_vpc_network.monitoring.id

  ingress {
    protocol       = "TCP"
    description    = "SSH"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 22
  }

  ingress {
    protocol       = "TCP"
    description    = "Grafana (public)"
    v4_cidr_blocks = ["0.0.0.0/0"]
    port           = 3000
  }

  ingress {
    protocol       = "TCP"
    description    = "Prometheus (internal only)"
    v4_cidr_blocks = ["10.0.0.0/16"]
    port           = 9090
  }

  ingress {
    protocol       = "TCP"
    description    = "Alertmanager (internal only)"
    v4_cidr_blocks = ["10.0.0.0/16"]
    port           = 9093
  }

  ingress {
    protocol       = "TCP"
    description    = "Node Exporter"
    v4_cidr_blocks = ["10.0.0.0/16"]
    port           = 9100
  }

  egress {
    protocol       = "ANY"
    description    = "Allow all outgoing"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# ======================== ПУБЛИЧНЫЕ IP ========================

resource "yandex_vpc_address" "broker_ip" {
  name = "broker-public-ip"
  external_ipv4_address {
    zone_id = var.yc_zone
  }
}

resource "yandex_vpc_address" "monitoring_ip" {
  name = "monitoring-public-ip"
  external_ipv4_address {
    zone_id = var.yc_zone
  }
}

# ======================== ВМ1: БРОКЕР ========================

resource "yandex_compute_instance" "broker_vm" {
  name        = "broker-vm"
  platform_id = "standard-v3"
  zone        = var.yc_zone

  resources {
    cores  = var.broker_vm_cores
    memory = var.broker_vm_memory
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.container-optimized-image.id
      size     = var.broker_vm_disk_size
      type     = "network-hdd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.broker_subnet.id
    nat                = true
    security_group_ids = [yandex_vpc_security_group.broker_sg.id]
  }

  metadata = {
    ssh-keys  = "ubuntu:${file(var.public_ssh_key_path)}"
    user-data = file("${path.module}/cloud-init-broker.yaml")
  }

  scheduling_policy {
    preemptible = var.use_preemptible
  }
}

# ======================== ВМ2: МОНИТОРИНГ ========================

resource "yandex_compute_instance" "monitoring_vm" {
  name        = "monitoring-vm"
  platform_id = "standard-v3"
  zone        = var.yc_zone

  resources {
    cores  = var.monitoring_vm_cores
    memory = var.monitoring_vm_memory
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.container-optimized-image.id
      size     = var.monitoring_vm_disk_size
      type     = "network-hdd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.monitoring_subnet.id
    nat                = true
    security_group_ids = [yandex_vpc_security_group.monitoring_sg.id]
  }

  metadata = {
    ssh-keys  = "ubuntu:${file(var.public_ssh_key_path)}"
    user-data = file("${path.module}/cloud-init-monitoring.yaml")
  }

  scheduling_policy {
    preemptible = var.use_preemptible
  }
}