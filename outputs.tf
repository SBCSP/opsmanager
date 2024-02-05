
output "sqlbox_ip" {
  description = "The IP address assigned to the sqlbox container"
  value       = proxmox_lxc.sqlbox.network[0].ip
}
