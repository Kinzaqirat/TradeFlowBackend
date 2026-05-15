"""Dashboard statistics aggregation endpoint."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from app.database import get_db
from app.dependencies import get_current_user
from app.models.trade import Trade
from app.models.user import User

router = APIRouter()


def get_period_start(period: str) -> datetime | None:
    now = datetime.now(timezone.utc)
    if period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "weekly":
        return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None  # all time


@router.get("/stats")
async def get_stats(
    period: str = Query("all", enum=["daily", "weekly", "monthly", "all"]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return comprehensive performance statistics for the user."""
    conditions = [Trade.user_id == current_user.id, Trade.is_deleted == False]
    period_start = get_period_start(period)
    if period_start:
        conditions.append(Trade.exit_datetime >= period_start)

    result = await db.execute(
        select(Trade).where(and_(*conditions)).order_by(Trade.exit_datetime.asc())
    )
    trades = result.scalars().all()

    if not trades:
        return {"summary": {}, "streaks": {}, "pnl_by_day": [], "pnl_by_symbol": [], "result_distribution": {}}

    wins = [t for t in trades if t.result == "WIN"]
    losses = [t for t in trades if t.result == "LOSS"]
    total_pnl = sum(float(t.pnl) for t in trades)
    gross_profit = sum(float(t.pnl) for t in wins)
    gross_loss = abs(sum(float(t.pnl) for t in losses))

    # Max drawdown
    cumulative = []
    running = 0
    for t in trades:
        running += float(t.pnl)
        cumulative.append(running)

    max_dd = 0
    peak = float('-inf')
    for val in cumulative:
        if val > peak:
            peak = val
        dd = val - peak
        if dd < max_dd:
            max_dd = dd

    # Streaks
    results_seq = [t.result for t in trades]
    current_streak, current_type = 1, results_seq[-1] if results_seq else "WIN"
    max_win, max_loss = 0, 0
    temp = 1
    for i in range(len(results_seq) - 1, 0, -1):
        if results_seq[i] == results_seq[i - 1]:
            if i == len(results_seq) - 1:
                current_streak += 1
            temp += 1
        else:
            temp = 1
        if results_seq[i] == "WIN":
            max_win = max(max_win, temp)
        else:
            max_loss = max(max_loss, temp)

    # P/L by day
    pnl_day: dict = defaultdict(lambda: {"pnl": 0, "trades": 0})
    for t in trades:
        day = t.exit_datetime.strftime("%Y-%m-%d")
        pnl_day[day]["pnl"] += float(t.pnl)
        pnl_day[day]["trades"] += 1

    pnl_by_symbol: dict = defaultdict(lambda: {"pnl": 0, "trades": 0})
    for t in trades:
        pnl_by_symbol[t.symbol]["pnl"] += float(t.pnl)
        pnl_by_symbol[t.symbol]["trades"] += 1

    return {
        "summary": {
            "total_trades": len(trades),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(len(wins) / len(trades) * 100, 2) if trades else 0,
            "avg_win": round(gross_profit / len(wins), 2) if wins else 0,
            "avg_loss": round(-gross_loss / len(losses), 2) if losses else 0,
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss else None,
            "max_drawdown": round(max_dd, 2),
        },
        "streaks": {
            "current_streak": current_streak,
            "current_streak_type": current_type,
            "max_win_streak": max_win,
            "max_loss_streak": max_loss,
        },
        "pnl_by_day": [
            {"date": d, "pnl": round(v["pnl"], 2), "trades": v["trades"]}
            for d, v in sorted(pnl_day.items())
        ],
        "pnl_by_symbol": sorted(
            [{"symbol": s, "pnl": round(v["pnl"], 2), "trades": v["trades"]} for s, v in pnl_by_symbol.items()],
            key=lambda x: abs(x["pnl"]), reverse=True
        )[:10],
        "result_distribution": {
            "WIN": len(wins),
            "LOSS": len(losses),
            "BREAKEVEN": len([t for t in trades if t.result == "BREAKEVEN"]),
        },
    }
