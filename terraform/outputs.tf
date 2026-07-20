output "broker_public_ip" {
  value = yandex_vpc_address.broker_ip.external_ipv4_address[0].address
}

output "broker_private_ip" {
  value = yandex_compute_instance.broker_vm.network_interface[0].ip_address
}

output "monitoring_public_ip" {
  value = yandex_vpc_address.monitoring_ip.external_ipv4_address[0].address
}

output "monitoring_private_ip" {
  value = yandex_compute_instance.monitoring_vm.network_interface[0].ip_address
}

output "grafana_url" {
  value = "http://${yandex_vpc_address.monitoring_ip.external_ipv4_address[0].address}:3000"
}

output "prometheus_url" {
  value = "http://${yandex_vpc_address.monitoring_ip.external_ipv4_address[0].address}:9090"
}

output "ssh_broker" {
  value = "ssh ubuntu@${yandex_vpc_address.broker_ip.external_ipv4_address[0].address}"
}

output "ssh_monitoring" {
  value = "ssh ubuntu@${yandex_vpc_address.monitoring_ip.external_ipv4_address[0].address}"
}