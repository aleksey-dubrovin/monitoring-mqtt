variable "yc_token" {
  description = "Yandex Cloud OAuth token"
  sensitive   = true
}

variable "yc_cloud_id" {
  description = "Yandex Cloud ID"
}

variable "yc_folder_id" {
  description = "Yandex Cloud Folder ID"
}

variable "yc_zone" {
  description = "Yandex Cloud availability zone"
  default     = "ru-central1-a"
}

variable "public_ssh_key_path" {
  description = "Path to public SSH key"
  default     = "~/.ssh/id_rsa.pub"
}

variable "use_preemptible" {
  description = "Use preemptible VMs (cheaper but can be stopped)"
  default     = true
}

variable "broker_vm_cores" {
  description = "Number of CPU cores for broker VM"
  default     = 2
}

variable "broker_vm_memory" {
  description = "Memory (GB) for broker VM"
  default     = 4
}

variable "broker_vm_disk_size" {
  description = "Disk size (GB) for broker VM"
  default     = 30
}

variable "monitoring_vm_cores" {
  description = "Number of CPU cores for monitoring VM"
  default     = 2
}

variable "monitoring_vm_memory" {
  description = "Memory (GB) for monitoring VM"
  default     = 4
}

variable "monitoring_vm_disk_size" {
  description = "Disk size (GB) for monitoring VM"
  default     = 30
}