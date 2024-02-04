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
  pm_api_url = "https://192.168.0.240:8006/api2/json"
  pm_api_token_id = "terraform-prov@pve!proxmox-api-token"
  pm_api_token_secret = "74597722-6018-4146-87b7-2148b642fd95"
  pm_tls_insecure = true
  pm_debug = true
  
}

resource "proxmox_lxc" "twingate_ha_1" {
  target_node = "pve"
  hostname = "TWINGATE-HA-1"
  description = "Twingate Connector 1 for SandboxCSP"
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
    bridge = "vmbr0"
    ip = "dhcp"
  }
}

resource "proxmox_lxc" "twingate_ha_2" {
  target_node = "pve"
  hostname = "TWINGATE-HA-2"
  description = "Twingate Connector 2 for SandboxCSP"
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
    bridge = "vmbr0"
    ip = "dhcp"
  }
}

resource "proxmox_lxc" "sandboxcsp_org_runner" {
  target_node = "pve"
  hostname = "SANDBOXCSP-ORG-RUNNER"
  description = "SandboxCSP Organizational Runner"
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
    bridge = "vmbr0"
    ip = "dhcp"
  }
}

resource "proxmox_lxc" "sqlbox" {
  target_node = "pve"
  hostname = "SQLBOX"
  description = "SQLBox for SandboxCSP"
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
    bridge = "vmbr0"
    ip = "dhcp"
  }
}
