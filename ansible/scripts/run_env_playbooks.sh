#!/bin/bash

ansible-playbook -i ../inventory.yml ../playbooks/update_lxc_ct.yml -K