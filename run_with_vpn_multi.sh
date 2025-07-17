#!/bin/bash

COUNTRIES=("Japan" "India" "Brazil" "Singapore")

for COUNTRY in "${COUNTRIES[@]}"; do
    echo "\nMencoba VPN negara: $COUNTRY"
    curl -s https://www.vpngate.net/api/iphone/ | grep -i "$COUNTRY" | head -1 | awk -F',' '{print $15}' | base64 -d > vpngate_tmp.ovpn
    
    if [ ! -s vpngate_tmp.ovpn ]; then
        echo "Config VPN untuk $COUNTRY tidak ditemukan, lanjut negara berikutnya."
        continue
    fi

    sudo pkill openvpn 2>/dev/null
    sleep 2
    sudo openvpn --config vpngate_tmp.ovpn --daemon
    sleep 15

    for i in {1..5}; do
        if curl -s https://api.binance.com/api/v3/ping | grep -q '{}'; then
            echo "VPN aktif ($COUNTRY) dan Binance bisa diakses. Menjalankan bot..."
            cd arif_zip_extracted
            python3 bot.py
            exit 0
        else
            echo "Menunggu koneksi VPN ke Binance... ($COUNTRY, percobaan $i)"
            sleep 5
        fi
    done
    echo "Gagal konek ke Binance dengan VPN negara $COUNTRY. Mencoba negara berikutnya..."
done

echo "Tidak ada VPN yang berhasil konek ke Binance. Bot tidak dijalankan."