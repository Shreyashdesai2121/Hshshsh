# Dhan API Integration Guide

## 🔑 **Step 1: Get Your Dhan API Credentials**

1. **Login to Dhan** at https://dhan.co/
2. **Navigate to API section** in your account dashboard
3. **Generate API Key and Secret**
4. **Note down the API base URL** (check their documentation)

## 📝 **Step 2: Update Environment Variables**

Edit your `.env` file with your actual Dhan credentials:

```env
# Dhan Configuration
USE_DHAN=true
USE_ZERODHA=false
DHAN_API_KEY=your_actual_dhan_api_key_here
DHAN_API_SECRET=your_actual_dhan_api_secret_here

# Trading Configuration
MODE=dry_run
QUANTITY=1
ONE_TRADE_PER_DAY=true
TRADING_START=09:15
TRADING_END=15:30
```

## 🔧 **Step 3: Find Dhan API Endpoints**

You need to find the actual API endpoints from Dhan documentation. Common patterns:

### **Authentication**
- **Endpoint**: `POST /auth/login` or `/api/auth/login`
- **Headers**: `Content-Type: application/json`
- **Body**: `{"api_key": "...", "api_secret": "..."}`

### **Market Data**
- **Quote**: `GET /market/quote` or `/api/market/quote`
- **Historical**: `GET /market/historical` or `/api/market/historical`
- **Headers**: `Authorization: Bearer {access_token}`

### **Orders**
- **Place Order**: `POST /orders/place` or `/api/orders/place`
- **Order Status**: `GET /orders/{order_id}` or `/api/orders/{order_id}`
- **Cancel Order**: `DELETE /orders/{order_id}` or `/api/orders/{order_id}`

### **Account**
- **Margin**: `GET /user/margin` or `/api/user/margin`
- **Positions**: `GET /user/positions` or `/api/user/positions`

## 🛠️ **Step 4: Update Dhan Adapter**

Replace the placeholder URLs in `broker/dhan_adapter.py`:

```python
# Update these with actual Dhan API endpoints
self.base_url = "https://api.dhan.co"  # Replace with actual base URL

# Update authentication endpoint
auth_url = f"{self.base_url}/auth/login"  # Replace with actual auth endpoint

# Update market data endpoint
spot_url = f"{self.base_url}/market/quote"  # Replace with actual quote endpoint
```

## 📊 **Step 5: Understand Dhan API Response Format**

Dhan API responses typically look like this (adjust based on actual format):

### **Authentication Response**
```json
{
  "status": "success",
  "access_token": "your_access_token",
  "user_id": "your_user_id",
  "expires_in": 3600
}
```

### **Market Data Response**
```json
{
  "status": "success",
  "data": {
    "symbol": "NIFTY50",
    "last_price": 18500.50,
    "open": 18450.00,
    "high": 18520.00,
    "low": 18400.00,
    "close": 18500.50,
    "volume": 1000000
  }
}
```

### **Order Response**
```json
{
  "status": "success",
  "order_id": "ORD123456",
  "status": "placed",
  "message": "Order placed successfully"
}
```

## 🧪 **Step 6: Test Your Integration**

### **Test Authentication**
```python
# Test in Python console
import asyncio
from broker.dhan_adapter import DhanAdapter

async def test_auth():
    adapter = DhanAdapter("your_api_key", "your_api_secret")
    result = await adapter.authenticate()
    print(f"Auth result: {result.success}")
    if result.success:
        print(f"Access token: {adapter.access_token}")

asyncio.run(test_auth())
```

### **Test Market Data**
```python
async def test_spot():
    adapter = DhanAdapter("your_api_key", "your_api_secret")
    await adapter.authenticate()
    result = await adapter.get_spot("NIFTY50")
    print(f"Spot price: {result.data}")

asyncio.run(test_spot())
```

## 🚀 **Step 7: Run the System**

1. **Start Backend**
   ```bash
   uvicorn app_backend:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test in Dry Run Mode**
   - Open http://localhost:3000
   - Click "Start Strategy"
   - Monitor logs for API calls

## 🔍 **Step 8: Debug Common Issues**

### **Authentication Failed**
- Check API key and secret
- Verify API endpoint URL
- Check request headers and body format

### **Market Data Not Working**
- Verify authentication is successful
- Check symbol format (NIFTY50 vs NIFTY 50)
- Verify market data endpoint URL

### **Orders Not Placing**
- Check order placement endpoint
- Verify order parameters format
- Check if market is open

## 📞 **Getting Help**

1. **Check Dhan API Documentation** for exact endpoints
2. **Contact Dhan Support** for API access issues
3. **Test with Postman** before implementing in code
4. **Check logs** in `logs/strategy.log` for detailed errors

## ⚠️ **Important Notes**

- **Always test in dry run mode first**
- **Dhan API might have rate limits**
- **Some endpoints might require different authentication**
- **Market data might be delayed in free tier**
- **Check Dhan's API terms and conditions**

## 🎯 **Next Steps After Integration**

1. **Test authentication** with your credentials
2. **Verify market data** is coming through
3. **Test order placement** in dry run mode
4. **Run strategy** for a few days in dry run
5. **Monitor performance** and logs
6. **Go live** only after thorough testing

---

**Need help with specific Dhan API endpoints? Share the Dhan API documentation link and I'll help you implement the exact integration!**