# PROVIDER
terraform {
  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = "3.0.1-rc1"
    }
  }
}

provider "proxmox" {
  pm_api_url          = var.proxmox_url
  pm_api_token_id     = var.proxmox_api_token_id
  pm_api_token_secret = var.proxmox_api_token_secret
  pm_tls_insecure     = true
  pm_debug            = true

}

resource "proxmox_lxc" "twingate_ha_1" {
  target_node  = var.target_node
  hostname     = "TWINGATE-HA-1"
  ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  password     = var.global_password
  cores        = 2
  memory       = 2048
  swap         = 512
  start        = true
  onboot       = true
  unprivileged = true
  vmid         = 299


  rootfs {
    size    = "20G"
    storage = var.local_storage
  }

  network {
    name   = var.eth0_interface
    bridge = var.network_bridge
    ip     = "dhcp"
    gw     = var.global_gw_ip
  }
}

resource "proxmox_lxc" "twingate_ha_2" {
  target_node  = var.target_node
  hostname     = "TWINGATE-HA-2"
  ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  password     = var.global_password
  cores        = 2
  memory       = 2048
  swap         = 512
  start        = true
  onboot       = true
  unprivileged = true
  vmid         = 300


  rootfs {
    size    = "20G"
    storage = var.local_storage
  }

  network {
    name   = var.eth0_interface
    bridge = var.network_bridge
    ip     = "dhcp"
    gw     = var.global_gw_ip
  }
}

resource "proxmox_lxc" "sandboxcsp_org_runner" {
  target_node  = var.target_node
  hostname     = "SANDBOXCSP-ORG-RUNNER"
  ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  password     = var.global_password
  cores        = 8
  memory       = 16384
  swap         = 2048
  start        = true
  onboot       = true
  unprivileged = true
  vmid         = 298


  rootfs {
    size    = "100G"
    storage = var.local_storage
  }

  network {
    name   = var.eth0_interface
    bridge = var.network_bridge
    ip     = "dhcp"
    gw     = var.global_gw_ip
  }

  features {
    nesting = true
    keyctl  = true
  }
}

resource "proxmox_lxc" "sqlbox" {
  target_node  = var.target_node
  hostname     = "SQLBOX"
  ostemplate   = "local:vztmpl/debian-12-turnkey-mysql_18.0-1_amd64.tar.gz"
  password     = var.global_password
  cores        = 2
  memory       = 4096
  swap         = 512
  start        = true
  onboot       = true
  unprivileged = true
  vmid         = 297


  rootfs {
    size    = "100G"
    storage = var.local_storage
  }

  network {
    name   = var.eth0_interface
    bridge = var.network_bridge
    ip     = "dhcp"
    gw     = var.piehole_dns
  }
}


resource "proxmox_lxc" "flagship" {
  target_node  = var.target_node
  hostname     = "FLAGSHIP"
  ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  password     = var.global_password
  cores        = 8
  memory       = 8192
  swap         = 2048
  start        = true
  onboot       = true
  unprivileged = true
  vmid         = 296

  rootfs {
    size    = "150G"
    storage = var.local_storage
  }

  network {
    name   = var.eth0_interface
    bridge = var.network_bridge
    ip     = "dhcp"
    gw     = var.piehole_dns
  }

  features {
    nesting = true
    keyctl  = true
  }
}

resource "proxmox_lxc" "mongo_db" {
  target_node  = var.target_node
  hostname     = "MONGO-DB"
  ostemplate   = "local:vztmpl/debian-10-turnkey-mongodb_16.1-1_amd64.tar.gz"
  password     = var.global_password
  cores        = 2
  memory       = 4096
  swap         = 512
  start        = true
  onboot       = true
  unprivileged = true
  vmid         = 201


  rootfs {
    size    = "100G"
    storage = var.local_storage
  }

  network {
    name   = var.eth0_interface
    bridge = var.network_bridge
    ip     = "dhcp"
    gw     = var.piehole_dns
  }
}

resource "proxmox_lxc" "piehole" {
  target_node  = var.target_node
  hostname     = "PIHOLE"
  ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  password     = var.global_password
  cores        = 8
  memory       = 4096
  swap         = 512
  start        = true
  onboot       = true
  unprivileged = true
  vmid         = 200
  ssh_public_keys = var.ssh_pub_key

  rootfs {
    size    = "15G"
    storage = var.local_storage
  }

  network {
    name   = var.eth0_interface
    bridge = var.network_bridge
    ip     = "192.168.0.19/24"
    gw     = var.global_gw_ip
  }
}

# resource "proxmox_lxc" "home_page" {
#   target_node  = var.target_node
#   hostname     = "HOME-PAGE"
#   ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
#   password     = var.global_password
#   cores        = 22
#   memory       = 4096
#   swap         = 512
#   start        = true
#   onboot       = true
#   unprivileged = true
#   vmid         = 199
#   ssh_public_keys = var.ssh_pub_key

#   rootfs {
#     size    = "25G"
#     storage = var.local_storage
#   }

#   network {
#     name   = var.eth0_interface
#     bridge = var.network_bridge
#     ip     = "dhcp"
#     gw     = var.piehole_dns
#   }

#   features {
#     nesting = true
#     keyctl  = true
#   }
# }

resource "proxmox_vm_qemu" "swarm_docker" {
  target_node = var.target_node
  name        = "SWARM-DOCKER"
  iso = "local:iso/ubuntu-22.04.3-live-server-amd64.iso"
  qemu_os = "l26"
  os_type = "ubuntu"
  sockets = 4
  cores = 8
  memory = 16384
  vmid = 119
  
  ipconfig0 = "dhcp"
}