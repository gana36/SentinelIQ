from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, WatchlistItem
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.watchlist import WatchlistItemIn, WatchlistItemOut

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItemOut])
async def get_watchlist(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WatchlistItem).where(WatchlistItem.user_id == current_user.id))
    return result.scalars().all()


@router.post("", response_model=WatchlistItemOut, status_code=status.HTTP_201_CREATED)
async def add_ticker(
    body: WatchlistItemIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticker = body.ticker.upper()
    existing = await db.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == current_user.id, WatchlistItem.ticker == ticker)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"{ticker} already in watchlist")

    item = WatchlistItem(user_id=current_user.id, ticker=ticker)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_ticker(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        delete(WatchlistItem).where(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.ticker == ticker.upper(),
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Ticker not found in watchlist")
