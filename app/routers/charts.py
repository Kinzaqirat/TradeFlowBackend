"""Historical price chart data router using Alpha Vantage."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from datetime import datetime
from app.database import get_db
from app.dependencies import get_current_user
from app.models.trade import Trade
from app.models.user import User
from app.config import settings

router = APIRouter()

# Simple in-memory cache for demo purposes
chart_cache = {}


@router.get("/{trade_id}/chart-data")
async def get_chart_data(
    trade_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch Alpha Vantage price data and return with trade markers."""
    # Fetch trade
    result = await db.execute(
        select(Trade).where(Trade.id == trade_id, Trade.user_id == current_user.id)
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    symbol = trade.symbol
    if symbol in chart_cache and (datetime.now() - chart_cache[symbol]["ts"]).seconds < 3600:
        prices = chart_cache[symbol]["data"]
    else:
        # Fetch from Alpha Vantage
        if not settings.ALPHA_VANTAGE_API_KEY:
            # Mock data if no key
            prices = [
                {"date": "2024-01-01", "close": 150.0},
                {"date": "2024-01-02", "close": 155.0},
                # ...
            ]
        else:
            # Try stock daily first
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={settings.ALPHA_VANTAGE_API_KEY}"
            async with httpx.AsyncClient() as client:
                res = await client.get(url)
                data = res.json()
                
                if "Time Series (Daily)" in data:
                    raw_prices = data["Time Series (Daily)"]
                    prices = [
                        {"date": d, "close": float(v["4. close"])}
                        for d, v in sorted(raw_prices.items())
                    ]
                else:
                    # Try crypto daily if stock fails
                    crypto_url = f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={symbol}&market=USD&apikey={settings.ALPHA_VANTAGE_API_KEY}"
                    res = await client.get(crypto_url)
                    data = res.json()
                    
                    if "Time Series (Digital Currency Daily)" in data:
                        raw_prices = data["Time Series (Digital Currency Daily)"]
                        prices = [
                            {"date": d, "close": float(v["4b. close (USD)"])}
                            for d, v in sorted(raw_prices.items())
                        ]
                    else:
                        raise HTTPException(status_code=503, detail="Alpha Vantage API quota exceeded or symbol not found")
                
                chart_cache[symbol] = {"ts": datetime.now(), "data": prices}

    return {
        "prices": prices,
        "entry": {"date": trade.entry_datetime.strftime("%Y-%m-%d"), "price": float(trade.entry_price)},
        "exit": {"date": trade.exit_datetime.strftime("%Y-%m-%d"), "price": float(trade.exit_price)},
    }


@router.get("/price-data/{symbol}")
async def get_symbol_price_data(
    symbol: str,
    current_user: User = Depends(get_current_user),
):
    """Fetch Alpha Vantage price data for a general symbol (Stock or Crypto)."""
    if symbol in chart_cache and (datetime.now() - chart_cache[symbol]["ts"]).seconds < 3600:
        prices = chart_cache[symbol]["data"]
    else:
        # Fetch from Alpha Vantage
        if not settings.ALPHA_VANTAGE_API_KEY:
            # Mock data if no key
            prices = [
                {"date": "2024-01-01", "close": 150.0 + i}
                for i in range(30)
            ]
        else:
            async with httpx.AsyncClient() as client:
                # Try stock daily first
                url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={settings.ALPHA_VANTAGE_API_KEY}"
                res = await client.get(url)
                data = res.json()
                
                if "Time Series (Daily)" in data:
                    raw_prices = data["Time Series (Daily)"]
                    prices = [
                        {"date": d, "close": float(v["4. close"])}
                        for d, v in sorted(raw_prices.items())
                    ]
                else:
                    # Try crypto daily if stock fails
                    crypto_url = f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={symbol}&market=USD&apikey={settings.ALPHA_VANTAGE_API_KEY}"
                    res = await client.get(crypto_url)
                    data = res.json()
                    
                    if "Time Series (Digital Currency Daily)" in data:
                        raw_prices = data["Time Series (Digital Currency Daily)"]
                        prices = [
                            {"date": d, "close": float(v["4b. close (USD)"])}
                            for d, v in sorted(raw_prices.items())
                        ]
                    else:
                        raise HTTPException(status_code=503, detail="Alpha Vantage API quota exceeded or symbol not found")
                
                chart_cache[symbol] = {"ts": datetime.now(), "data": prices}

    return {"symbol": symbol, "prices": prices}
