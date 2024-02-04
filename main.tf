# PROVIDER
terraform {
  required_providers {
    proxmox = {
      source = "Telmate/proxmox"
      version = "3.0.1-rc1"
    }
  }
}

provider "proxmox" {
  pm_api_url = var.proxmox_url
  pm_api_token_id = var.proxmox_api_token_id
  pm_api_token_secret = var.proxmox_api_token_secret
  pm_tls_insecure = true
  pm_debug = true
  
}

resource "proxmox_lxc" "twingate_ha_1" {
  target_node = var.target_node
  hostname = "TWINGATE-HA-1"
  ostemplate = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  password = "890*()iopIOP890"
  cores = 2
  memory = 2048
  swap = 512
  start = true
  onboot = true
  unprivileged = true
  vmid = 299


  rootfs {
    size = "20G"
    storage = "local-lvm"
  }

  network {
    name = "eth0"
    bridge = var.network_bridge
    ip = "dhcp"
  }
}

resource "proxmox_lxc" "twingate_ha_2" {
  target_node = var.target_node
  hostname = "TWINGATE-HA-2"
  ostemplate = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  password = "890*()iopIOP890"
  cores = 2
  memory = 2048
  swap = 512
  start = true
  onboot = true
  unprivileged = true
  vmid = 300


  rootfs {
    size = "20G"
    storage = "local-lvm"
  }

  network {
    name = "eth0"
    bridge = var.network_bridge
    ip = "dhcp"
  }
}

resource "proxmox_lxc" "sandboxcsp_org_runner" {
  target_node = var.target_node
  hostname = "SANDBOXCSP-ORG-RUNNER"
  ostemplate = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  password = "890*()iopIOP890"
  cores = 8
  memory = 16384
  swap = 2048
  start = true
  onboot = true
  unprivileged = true
  vmid = 298


  rootfs {
    size = "100G"
    storage = "local-lvm"
  }

  network {
    name = "eth0"
    bridge = var.network_bridge
    ip = "dhcp"
  }
}

resource "proxmox_lxc" "sqlbox" {
  target_node = var.target_node
  hostname = "SQLBOX"
  ostemplate = "local:vztmpl/debian-12-turnkey-mysql_18.0-1_amd64.tar.gz"
  password = "890*()iopIOP890"
  cores = 8
  memory = 4096
  swap = 512
  start = true
  onboot = true
  unprivileged = true
  vmid = 297


  rootfs {
    size = "100G"
    storage = "local-lvm"
  }

  network {
    name = "eth0"
    bridge = var.network_bridge
    ip = "dhcp"
  }
}


resource "proxmox_lxc" "flagship" {
  target_node = var.target_node
  hostname = "FLAGSHIP"
  ostemplate = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  password = "890*()iopIOP890"
  cores = 8
  memory = 8192
  swap = 2048
  start = true
  onboot = true
  unprivileged = true
  vmid = 296

  rootfs {
    size = "150G"
    storage = "local-lvm"
  }

  network {
    name = "eth0"
    bridge = var.network_bridge
    ip = "dhcp"
  }
}

