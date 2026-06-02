#!/bin/bash
# Transfer script - credentials removed for security
# Set SSHPASS environment variable or use ssh key authentication

if [ -z "$SSHPASS" ]; then
    echo "Error: SSHPASS environment variable not set"
    echo "Usage: export SSHPASS='your_password' && ./transfer_bundle.sh <bundle_file>"
    exit 1
fi

TARGET_HOST="${TARGET_HOST:-your-host-here}"
TARGET_USER="${TARGET_USER:-your-user-here}"
TARGET_PATH="${TARGET_PATH:-~/Jakes-agent/}"

if command -v sshpass &> /dev/null; then
    sshpass -e scp -o StrictHostKeyChecking=no "$1" ${TARGET_USER}@${TARGET_HOST}:${TARGET_PATH}
else
    # Fallback: use Python paramiko
    python3 << 'PYEND'
import paramiko
import os
import sys

bundle = sys.argv[1] if len(sys.argv) > 1 else None
if not bundle or not os.path.exists(bundle):
    print("Bundle not found")
    sys.exit(1)

# Get credentials from environment
password = os.environ.get('SSHPASS')
target_host = os.environ.get('TARGET_HOST', 'your-host-here')
target_user = os.environ.get('TARGET_USER', 'your-user-here')
target_path = os.environ.get('TARGET_PATH', '~/Jakes-agent/')

if not password:
    print("Error: SSHPASS environment variable not set")
    sys.exit(1)

# SSH connection
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(target_host, username=target_user, password=password)
    
    # Ensure directory exists
    stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {target_path}')
    stdout.channel.recv_exit_status()
    
    # Transfer file
    sftp = ssh.open_sftp()
    remote_path = f'{target_path}/dish-chat-bundle.tar.gz'
    print(f"Transferring {bundle} to {remote_path}...")
    sftp.put(bundle, remote_path)
    sftp.close()
    print("✅ Transfer complete")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
finally:
    ssh.close()
PYEND
fi
