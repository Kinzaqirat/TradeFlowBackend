"""Seed database with sample trading data for development."""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models.user import User
from app.models.trade import Trade
from app.utils.pnl_calculator import calculate_pnl, calculate_pnl_percent, classify_result


async def seed_database():
    """Create tables and seed sample data."""
    # Create engine and tables
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if user exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == "trader@example.com"))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id="user-001",
                email="trader@example.com",
                username="trader",
                hashed_password="$2b$12$abcdefghijklmnopqrstuvwxyz",  # dummy hash
            )
            session.add(user)
            await session.flush()
            print(f"✓ Created user: {user.email}")

        # Sample trades data
        now = datetime.now(timezone.utc)
        trades_data = [
            # Bitcoin trades
            ("BTC/USD", "LONG", 43000, 45200, 0.5, 100, "Strong uptrend, broke resistance"),
            ("BTC/USD", "LONG", 44500, 43800, 0.3, 50, "Failed breakout"),
            ("BTC/USD", "SHORT", 45000, 44500, 0.5, 100, "Overbought, sold high"),
            # Ethereum trades
            ("ETH/USD", "LONG", 2300, 2450, 2.0, 50, "Following Bitcoin momentum"),
            ("ETH/USD", "LONG", 2350, 2280, 1.5, 40, "Support break failed"),
            ("ETH/USD", "SHORT", 2400, 2350, 2.5, 60, "Resistance rejection"),
            # Apple stock trades
            ("AAPL", "LONG", 175, 182, 10, 25, "Earnings beat expectations"),
            ("AAPL", "LONG", 180, 177, 5, 15, "Technical pullback"),
            # Tesla trades
            ("TSLA", "LONG", 250, 268, 5, 50, "EV sector rally"),
            ("TSLA", "SHORT", 270, 265, 3, 40, "Overextended"),
            # Forex
            ("EUR/USD", "LONG", 1.0900, 1.0950, 100000, 30, "ECB dovish"),
            ("GBP/USD", "SHORT", 1.2800, 1.2750, 50000, 20, "BOE rate cut expectations"),
            # Commodities
            ("GOLD", "LONG", 2050, 2085, 5, 50, "Geopolitical uncertainty"),
            ("OIL", "LONG", 78, 82, 100, 200, "OPEC+ production cut"),
            ("COPPER", "SHORT", 4.30, 4.20, 10, 30, "Risk-off sentiment"),
        ]

        for i, (symbol, direction, entry_price, exit_price, quantity, fees, notes) in enumerate(trades_data):
            # Create trades spread across the last 45 days
            days_ago = i * 3  # Spread trades over time
            entry_dt = now - timedelta(days=days_ago, hours=10, minutes=30)
            exit_dt = entry_dt + timedelta(hours=4, minutes=15)

            entry_price_dec = Decimal(str(entry_price))
            exit_price_dec = Decimal(str(exit_price))
            qty_dec = Decimal(str(quantity))
            fees_dec = Decimal(str(fees))

            pnl = calculate_pnl(direction, entry_price_dec, exit_price_dec, qty_dec, fees_dec)
            pnl_pct = calculate_pnl_percent(pnl, entry_price_dec, qty_dec)
            result = classify_result(pnl)

            trade = Trade(
                id=f"trade-{i:03d}",
                user_id=user.id,
                symbol=symbol,
                direction=direction,
                entry_datetime=entry_dt,
                exit_datetime=exit_dt,
                entry_price=entry_price_dec,
                exit_price=exit_price_dec,
                quantity=qty_dec,
                fees=fees_dec,
                notes=notes,
                tags=[direction.lower(), symbol.split("/")[0].lower()],
                pnl=pnl,
                pnl_percent=pnl_pct,
                result=result,
            )
            session.add(trade)

        await session.commit()
        print(f"✓ Created {len(trades_data)} sample trades")

    await engine.dispose()
    print("\n✓ Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
