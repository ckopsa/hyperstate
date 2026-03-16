from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.hyperstate.response import ActorContext, HyperStateResponse
from app.infrastructure.database import get_db
from app.infrastructure.repositories.portfolio_photo_repo import PortfolioPhotoRepository
from app.projection.lessons.portfolio_gallery import PortfolioGalleryProjection
from app.web.deps import get_current_actor

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=HyperStateResponse)
async def portfolio_gallery(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    repo = PortfolioPhotoRepository(db)
    photos = await repo.list_all()
    return PortfolioGalleryProjection(photos, actor).build()
