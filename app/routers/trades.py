"""Trade CRUD router with filtering, pagination, and CSV export."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
from decimal import Decimal
import csv
import io

from app.database import get_db
from app.dependencies import get_current_user
from app.models.trade import Trade
from app.models.user import User
from app.schemas.trade import TradeCreate, TradeUpdate, TradeResponse
from app.utils.pnl_calculator import calculate_pnl, calculate_pnl_percent, classify_result

router = APIRouter()


@router.post("/", response_model=TradeResponse, status_code=201)
async def create_trade(
    data: TradeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new trade with auto-calculated P/L."""
    pnl = calculate_pnl(data.direction, data.entry_price, data.exit_price, data.quantity, data.fees)
    pnl_pct = calculate_pnl_percent(pnl, data.entry_price, data.quantity)

    trade = Trade(
        user_id=current_user.id,
        symbol=data.symbol,
        direction=data.direction,
        entry_datetime=data.entry_datetime,
        exit_datetime=data.exit_datetime,
        entry_price=data.entry_price,
        exit_price=data.exit_price,
        quantity=data.quantity,
        fees=data.fees,
        notes=data.notes,
        tags=data.tags,
        pnl=pnl,
        pnl_percent=pnl_pct,
        result=classify_result(pnl),
    )
    db.add(trade)
    await db.flush()
    await db.refresh(trade)
    return trade


@router.get("/", response_model=dict)
async def list_trades(
    symbol: str | None = Query(None),
    direction: str | None = Query(None),
    result: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("entry_datetime"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List trades with optional filters and pagination."""
    conditions = [Trade.user_id == current_user.id, Trade.is_deleted == False]

    if symbol:
        conditions.append(Trade.symbol == symbol.upper())
    if direction:
        conditions.append(Trade.direction == direction.upper())
    if result:
        conditions.append(Trade.result == result.upper())
    if date_from:
        conditions.append(Trade.entry_datetime >= date_from)
    if date_to:
        conditions.append(Trade.entry_datetime <= date_to)

    sort_col = getattr(Trade, sort_by, Trade.entry_datetime)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()

    query = select(Trade).where(and_(*conditions)).order_by(order)
    result_all = await db.execute(query)
    all_trades = result_all.scalars().all()

    total = len(all_trades)
    start = (page - 1) * page_size
    paginated = all_trades[start : start + page_size]

    return {
        "data": [TradeResponse.model_validate(t) for t in paginated],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/export/csv")
async def export_csv(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export all trades as CSV download."""
    result = await db.execute(
        select(Trade).where(Trade.user_id == current_user.id, Trade.is_deleted == False)
        .order_by(Trade.entry_datetime.desc())
    )
    trades = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Symbol", "Direction", "Entry Date", "Exit Date",
                     "Entry Price", "Exit Price", "Quantity", "Fees", "P/L", "P/L%", "Result", "Notes"])

    for t in trades:
        writer.writerow([
            t.id, t.symbol, t.direction,
            t.entry_datetime.isoformat(), t.exit_datetime.isoformat(),
            t.entry_price, t.exit_price, t.quantity, t.fees,
            t.pnl, t.pnl_percent, t.result, t.notes or "",
        ])

    output.seek(0)
    filename = f"trades_export_{datetime.now().strftime('%Y-%m-%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Trade).where(Trade.id == trade_id, Trade.user_id == current_user.id, Trade.is_deleted == False)
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.put("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: str,
    data: TradeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Trade).where(Trade.id == trade_id, Trade.user_id == current_user.id, Trade.is_deleted == False)
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(trade, field, value)

    # Recalculate P/L
    pnl = calculate_pnl(trade.direction, trade.entry_price, trade.exit_price, trade.quantity, trade.fees)
    trade.pnl = pnl
    trade.pnl_percent = calculate_pnl_percent(pnl, trade.entry_price, trade.quantity)
    trade.result = classify_result(pnl)

    await db.flush()
    await db.refresh(trade)
    return trade


@router.delete("/{trade_id}", status_code=204)
async def delete_trade(
    trade_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Trade).where(Trade.id == trade_id, Trade.user_id == current_user.id, Trade.is_deleted == False)
    )
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    trade.is_deleted = True
    await db.flush()
