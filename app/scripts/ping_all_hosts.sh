#!/bin/bash

ansible-playbook -i inventory.ini ./playbooks/ping-playbook.yml
