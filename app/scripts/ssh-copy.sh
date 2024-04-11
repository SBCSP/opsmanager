#!/bin/bash

# Change directory to where the script is located
cd "$(dirname "$0")" || exit

# Check if inventory.ini exists
if [ ! -f "../inventory.ini" ]; then
    echo "Error: inventory.ini file not found."
    exit 1
fi

# Read the list of remote servers from inventory.ini
while IFS= read -r server; do
    # Check if the line is not a comment or empty
    if [[ ! $server =~ ^\s*# && -n $server ]]; then
        # Extract server details (format: hostname user)
        read -r hostname user <<< "$server"
        
        # Copy SSH public key to the remote server
        ssh-copy-id -i ~/.ssh/id_ed25519.pub "$user@$hostname"
        
        # Check if ssh-copy-id command succeeded
        if [ $? -eq 0 ]; then
            echo "SSH key copied to $hostname"
        else
            echo "Failed to copy SSH key to $hostname"
        fi
    fi
done < "../inventory.ini"
