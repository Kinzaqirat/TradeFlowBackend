"""AI Chatbot router using Google Gemini with trade context injection."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import get_current_user
from app.models.trade import Trade
from app.models.user import User
from app.utils.gemini_client import send_message

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send user message to Gemini with trading context and return AI response."""
    # Fetch recent trades for context
    result = await db.execute(
        select(Trade)
        .where(and_(Trade.user_id == current_user.id, Trade.is_deleted == False))
        .order_by(Trade.exit_datetime.desc())
        .limit(20)
    )
    trades = result.scalars().all()

    # Build stats for context
    wins = [t for t in trades if t.result == "WIN"]
    total_pnl = sum(float(t.pnl) for t in trades)
    win_rate = (len(wins) / len(trades) * 100) if trades else 0

    trade_summary = "\n".join([
        f"- {t.symbol} ({t.direction}) | Entry: ${t.entry_price} | Exit: ${t.exit_price} | P/L: ${t.pnl} | {t.result}"
        for t in trades[:20]
    ])

    system_context = f"""You are a precise trading data analyst.

Trader: {current_user.username}
Recent Stats: {len(trades)} trades | {win_rate:.1f}% Win Rate | ${total_pnl:.2f} P/L

Recent Trade Data:
{trade_summary if trades else "No recent trades found."}

Instructions:
- Answer the question DIRECTLY and EXCLUSIVELY.
- Do NOT provide general advice, greetings, or filler unless asked.
- Use the provided trade data for context, but only if relevant to the question.
- Be extremely concise (1-2 sentences maximum if possible)."""

    try:
        response = await send_message(system_context, data.message)
        return {"response": response}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
