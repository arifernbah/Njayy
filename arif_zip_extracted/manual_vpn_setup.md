# Manual VPN Setup untuk Trading Real Binance Futures

## ⚠️ **PENTING: Testnet TIDAK untuk Trading Real**

Testnet hanya untuk testing dengan uang virtual. Untuk trading real, Anda perlu akses ke main Binance.

## 🔧 **Solusi Manual untuk Trading Real:**

### **Opsi 1: VPN Manual Setup**

#### **Step 1: Install VPN Client**
```bash
# Install OpenVPN
sudo apt-get update
sudo apt-get install openvpn

# Atau install VPN client lain
sudo apt-get install network-manager-openvpn
```

#### **Step 2: Download VPN Config**
- Kunjungi: https://www.vpngate.net/
- Pilih server Singapore atau Hong Kong
- Download file .ovpn

#### **Step 3: Connect VPN**
```bash
# Connect dengan file config
sudo openvpn --config your_vpn_config.ovpn --daemon

# Check connection
curl -I https://fapi.binance.com/fapi/v1/ping
```

### **Opsi 2: Cloudflare WARP (Gratis)**
```bash
# Install Cloudflare WARP
curl -fsSL https://pkg.cloudflareclient.com/install.sh | sudo sh

# Connect WARP
warp-cli register
warp-cli connect
```

### **Opsi 3: Proxy Setup**
```bash
# Set proxy environment
export https_proxy=http://your_proxy:port
export http_proxy=http://your_proxy:port

# Test connection
curl -I https://fapi.binance.com/fapi/v1/ping
```

### **Opsi 4: DNS Override**
```bash
# Edit hosts file
sudo nano /etc/hosts

# Add these lines:
185.199.108.153 fapi.binance.com
185.199.109.153 fapi.binance.com
185.199.110.153 fapi.binance.com
185.199.111.153 fapi.binance.com
```

## 🚀 **Setelah VPN Berhasil:**

### **Test Koneksi:**
```bash
python3 test_connection.py
```

### **Jalankan Bot:**
```bash
python3 bot.py
```

### **Verifikasi Trading Real:**
- Bot akan menggunakan main Binance endpoint
- Orders akan masuk ke akun real Anda
- Balance dan positions akan real

## 📱 **Telegram Commands untuk Monitoring:**

- `/test` - Test koneksi Binance
- `/balance` - Cek balance real
- `/diagnostics` - Status koneksi detail
- `/help` - Lihat semua commands

## ⚠️ **Peringatan Penting:**

1. **Pastikan VPN stabil** sebelum trading
2. **Monitor koneksi** secara berkala
3. **Backup API keys** Anda
4. **Test dengan amount kecil** dulu
5. **Monitor positions** di Binance web/app

## 🔍 **Troubleshooting:**

### **Jika VPN tidak stabil:**
```bash
# Check VPN status
sudo systemctl status openvpn

# Restart VPN
sudo systemctl restart openvpn

# Check routing
ip route show
```

### **Jika masih HTTP 451:**
1. Coba VPN server berbeda
2. Restart network
3. Clear DNS cache
4. Coba provider VPN lain

## 📞 **Support:**

Jika masih bermasalah:
1. Cek status Binance: https://status.binance.com/
2. Coba dari network berbeda
3. Contact Binance support
4. Gunakan mobile hotspot

**Setelah VPN berhasil, bot Anda akan bisa trading real di Binance Futures!** 🎯