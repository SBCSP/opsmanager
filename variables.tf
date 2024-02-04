
variable "proxmox_url" {
    type = string
    default = "https://192.168.0.240:8006/api2/json"
    nullable = false
}

variable "proxmox_api_token_id" {
    type = string
    default = "terraform-prov@pve!proxmox-api-token"
    nullable = false
}

variable "proxmox_api_token_secret" {
    type = string
    default = "74597722-6018-4146-87b7-2148b642fd95"
    nullable = false
}

variable "target_node" {
    type = string
    default = "pve"
    nullable = false
}

variable "ubuntu_iso" {
    type = string
    default = "local:iso/ubuntu-22.04.3-live-server-amd64.iso"
    nullable = false
}

variable "local_storage" {
    type = string
    default = "local-lvm"
    nullable = false
}

variable "network_bridge" {
    type = string
    default = "vmbr0"
    nullable = false
}

variable "cloud_init_template" {
    type = string
    default = "ubuntu-cloud"
    nullable = false
}

variable "global_password" {
    type = string
    default = "890*()iopIOP890"
    nullable = false
}