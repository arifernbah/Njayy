#!/bin/bash

# Download Singapore VPN config from VPNGate
curl -s https://www.vpngate.net/api/iphone/ | grep -i "Singapore" | head -1 | awk -F',' '{print $15}' | base64 -d > vpngate_sg.ovpn

# Start OpenVPN in background
echo "Starting OpenVPN..."
sudo openvpn --config vpngate_sg.ovpn --daemon

# Wait for VPN to establish
sleep 15

# Test Binance connectivity
for i in {1..10}; do
    if curl -s https://api.binance.com/api/v3/ping | grep -q '{}'; then
        echo "VPN active and Binance accessible."
        break
    else
        echo "Waiting for VPN connection to Binance... ($i)"
        sleep 5
    fi
done

# Run the bot if Binance is accessible
if curl -s https://api.binance.com/api/v3/ping | grep -q '{}'; then
    cd arif_zip_extracted
    python3 bot.py
else
    echo "Failed to connect to Binance. Bot not started."
fi