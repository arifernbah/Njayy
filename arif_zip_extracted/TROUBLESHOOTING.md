# ICT Bot Troubleshooting Guide

## HTML Error Response Issue

If you're seeing HTML error responses from Binance instead of JSON, this guide will help you diagnose and fix the issue.

### Symptoms
- Error messages like: `Invalid JSON error message from Binance: <!DOCTYPE html>`
- Bot health checks failing
- API calls returning HTML instead of JSON data

### Common Causes

1. **Rate Limiting**
   - Too many API calls in a short time
   - Solution: Wait a few minutes and restart the bot

2. **Network Issues**
   - Poor internet connection
   - Firewall blocking requests
   - Solution: Check your internet connection

3. **API Key Issues**
   - Invalid or expired API keys
   - Insufficient permissions
   - Solution: Verify your API keys in Binance

4. **Binance Server Issues**
   - Temporary server problems
   - Maintenance windows
   - Solution: Check Binance status page

### Diagnostic Steps

#### Step 1: Run Connection Test
```bash
python test_connection.py
```

This will test:
- Basic connectivity to Binance
- API credentials
- Specific endpoints

#### Step 2: Use Telegram Commands
Send these commands to your bot:

- `/test` - Test Binance connection
- `/diagnostics` - Get detailed connection info

#### Step 3: Check Environment Variables
Ensure your `.env` file contains:
```
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET=your_api_secret_here
TELEGRAM_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Solutions

#### Immediate Fixes

1. **Restart the Bot**
   ```bash
   # Stop the bot and restart
   python bot.py
   ```

2. **Check Rate Limits**
   - The bot has built-in rate limiting (50 calls/minute)
   - If you're hitting limits, wait 1-2 minutes

3. **Verify API Permissions**
   - Ensure your API key has Futures trading permissions
   - Check if IP restrictions are configured

#### Advanced Troubleshooting

1. **Check Binance Status**
   - Visit: https://status.binance.com/
   - Look for any ongoing issues

2. **Test with Different Network**
   - Try running the bot from a different location
   - Check if it's a regional issue

3. **Update Dependencies**
   ```bash
   pip install --upgrade python-binance
   pip install --upgrade requests
   ```

### Prevention

1. **Monitor Rate Limits**
   - The bot automatically tracks API calls
   - Use `/diagnostics` to check current usage

2. **Regular Health Checks**
   - The bot performs health checks every minute
   - Failed checks are logged and reported

3. **Backup API Keys**
   - Consider having backup API keys ready
   - Rotate keys periodically

### Error Codes Reference

| Error | Meaning | Solution |
|-------|---------|----------|
| HTML Response | Server returning error page | Check network/restart |
| 429 | Rate limit exceeded | Wait and retry |
| 401 | Invalid API key | Check credentials |
| 403 | Insufficient permissions | Check API permissions |
| 500 | Server error | Wait and retry |

### Getting Help

If the issue persists:

1. Run the diagnostic script: `python test_connection.py`
2. Check the logs for specific error messages
3. Use `/diagnostics` command in Telegram
4. Check Binance status page
5. Contact support with error details

### Log Analysis

Look for these patterns in your logs:

```
# Good - Normal operation
2025-07-18 07:42:10,366 - ICTBot - INFO - Health check passed

# Bad - HTML error
2025-07-18 07:42:10,366 - ICTBot - WARNING - Health check failed: HTML error response

# Bad - Rate limiting
2025-07-18 07:42:10,366 - ICTBot - WARNING - Rate limit hit (429)
```

### Emergency Procedures

If the bot is stuck in a loop:

1. **Stop the bot immediately**
2. **Check for stuck positions** using `/diagnostics`
3. **Manually verify positions** on Binance
4. **Restart with connection test**

### Contact Information

For urgent issues:
- Check Binance status: https://status.binance.com/
- Binance support: https://support.binance.com/
- API documentation: https://binance-docs.github.io/apidocs/futures/en/