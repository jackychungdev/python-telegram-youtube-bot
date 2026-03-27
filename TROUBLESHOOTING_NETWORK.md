# Telegram YouTube Bot - Network Error Troubleshooting Guide

## ❌ Error: `getaddrinfo failed` / Network Connection Error

This error means the bot **cannot connect to Telegram's API servers**.

### Common Causes & Solutions

#### 1. **Check Internet Connection**
First, verify your internet is working:
```bash
ping google.com
```

If this fails, fix your internet connection first.

#### 2. **Test Telegram Connectivity**
Check if you can reach Telegram's API:
```bash
ping api.telegram.org
```

- ✅ **If ping succeeds**: Network is fine, check firewall/proxy settings
- ❌ **If ping fails**: Telegram may be blocked in your network/region

#### 3. **Use a Proxy (Most Common Solution)**

If Telegram is blocked in your region, you need a proxy.

**Option A: HTTP Proxy**
```yaml
# config/config.yaml
bot:
  PROXY_URL: 'http://proxy.example.com:8080'
```

**Option B: SOCKS5 Proxy**
```yaml
# config/config.yaml
bot:
  PROXY_URL: 'socks5://user:pass@proxy.server:1080'
```

**Option C: Free Proxy Services** (for testing only)
- Sign up for services like:
  - Bright Data
  - Oxylabs
  - Smartproxy
  - IPRoyal

**Example Configuration:**
```yaml
bot:
  TOKEN: 'your-bot-token'
  ADMIN_CHAT_ID: 290569556
  PROXY_URL: 'http://username:password@proxy-server.com:port'
  LOCAL_API_URL: null
```

#### 4. **Firewall/Antivirus Issues**

Some firewalls block Telegram API access:

**Windows Firewall:**
1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Find Python and ensure both Private/Public are checked
4. Or temporarily disable firewall to test

**Antivirus:**
- Temporarily disable antivirus to test
- Add Python to antivirus whitelist

#### 5. **DNS Issues**

Try changing DNS servers:

**Windows:**
```powershell
# Set Google DNS
netsh interface ip set dns name="Ethernet" source=static addr=8.8.8.8
```

**Or use Cloudflare DNS:**
```powershell
netsh interface ip set dns name="Ethernet" source=static addr=1.1.1.1
```

#### 6. **Local Telegram Bot API Server** (Advanced)

For better performance and reliability, run your own Telegram Bot API server:

```yaml
# config/config.yaml
bot:
  LOCAL_API_URL: 'http://localhost:8081'
```

Then run the local Bot API server (requires Docker):
```bash
docker run -p 8081:8081 --restart unless-stopped \
  -e TELEGRAM_API_ID=your_api_id \
  -e TELEGRAM_API_HASH=your_api_hash \
  aiogram/telegram-bot-api
```

### Quick Test

After applying a solution, restart the bot:

```bash
taskkill /F /IM python.exe
cd c:\workspace\python-telegram-youtube-bot
python src\main.py
```

### Still Having Issues?

If none of the above works:

1. **Try mobile hotspot** - Rules out ISP blocking
2. **Use a VPN** - Bypasses regional restrictions
3. **Check Telegram status** - Visit https://t.me/TelegramStatus to see if there's an outage
4. **Contact network administrator** - If on corporate/school network

### Success Indicators

When fixed, you should see:
```
✅ telegram.ext.Application - INFO - Application started
✅ application.handlers.registration - INFO - All handlers registered successfully
```

The bot will then start receiving messages without network errors.
