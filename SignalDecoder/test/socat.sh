#!/bin/bash

# Check for correct number of arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <port1_path> <port2_path>"
    echo "Example: $0 /dev/ttyUSB0 /dev/ttyUSB1"
    exit 1
fi

PORT0=$1
PORT1=$2

# Function to clean up on exit
cleanup() {
    echo -e "\n[!] Shutting down socat and removing virtual links..."
    sudo rm -f "$PORT0" "$PORT1"
    # Kill the background socat process started by this script ($!)
    if [ -n "$SOCAT_PID" ]; then
        sudo kill "$SOCAT_PID"
    fi
    exit
}

# Trap interrupt signals (Ctrl+C)
trap cleanup SIGINT SIGTERM

# Check if ports already exist
if [ -e "$PORT0" ] || [ -e "$PORT1" ]; then
    echo "[!] Error: One or both ports already exist."
    exit 1
fi

echo "[*] Bridging $PORT0 <--> $PORT1 ..."

# Launch socat in the background
# user=$USER ensures the underlying PTY is owned by you
sudo socat -d -d \
    PTY,link="$PORT0",raw,echo=0,user=$USER \
    PTY,link="$PORT1",raw,echo=0,user=$USER &

# Save the PID of the background socat
SOCAT_PID=$!

# Wait for symlinks to appear
sleep 1

if [ -L "$PORT0" ] && [ -L "$PORT1" ]; then
    # Open permissions so your Go and Python apps don't need sudo
    sudo chmod 666 "$PORT0" "$PORT1"
    echo "[+] Bridge established. SOCAT PID: $SOCAT_PID"
    echo "[*] Press Ctrl+C to terminate."
    wait $SOCAT_PID
else
    echo "[!] Failed to create symlinks. Check permissions for the target directory."
    exit 1
fi
