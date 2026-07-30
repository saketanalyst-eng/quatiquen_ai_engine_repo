"""Decision repository implementation using SQLAlchemy."""

from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.infrastructure import DatabaseError
from src.core.logging.logger import get_logger
from src.domain.entities import Decision
from src.domain.repositories import IDecisionRepository
from src.infrastructure.persistence.mappers import DecisionMapper
from src.infrastructure.persistence.models import DecisionModel, RecommendationModel, ScoreDriversModel

logger = get_logger("quantiquan.infrastructure.decision_repo")


class DecisionRepository(IDecisionRepository):
    """SQLAlchemy implementation of IDecisionRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_finding_id(self, finding_id: UUID, tenant_id: UUID) -> Optional[Decision]:
        try:
            stmt = select(DecisionModel).where(
                DecisionModel.finding_id == str(finding_id),
                DecisionModel.tenant_id == str(tenant_id),
            )
            result = await self.session.execute(stmt)
            decision_model = result.scalar_one_or_none()
            if not decision_model:
                return None

            stmt2 = select(ScoreDriversModel).where(ScoreDriversModel.risk_score_id == decision_model.id)
            result2 = await self.session.execute(stmt2)
            driver_models = result2.scalars().all()

            stmt3 = select(RecommendationModel).where(RecommendationModel.finding_id == str(finding_id))
            result3 = await self.session.execute(stmt3)
            rec_model = result3.scalar_one_or_none()

            return DecisionMapper.to_domain(decision_model, driver_models, rec_model)
        except Exception as exc:
            logger.error("Failed to get decision", finding_id=str(finding_id), error=str(exc), exc_info=True)
            raise DatabaseError(f"Failed to get decision: {exc}", operation="get_by_finding_id") from exc

    async def save(self, decision: Decision) -> None:
        """Save a new decision (replaces existing)."""
        try:
            # Convert decision to models
            decision_model, driver_models, rec_model = DecisionMapper.to_model(decision)

            # Add decision model first and flush to generate ID
            self.session.add(decision_model)
            await self.session.flush()  # ✅ Generates decision_model.id

            # ✅ Now set risk_score_id on all driver models
            for dm in driver_models:
                dm.risk_score_id = decision_model.id

            # Add drivers and recommendation
            for dm in driver_models:
                self.session.add(dm)
            if rec_model:
                self.session.add(rec_model)

        except Exception as exc:
            logger.error("Failed to save decision", finding_id=str(decision.finding_id), error=str(exc), exc_info=True)
            raise DatabaseError(f"Failed to save decision: {exc}", operation="save") from exc

    async def update(self, decision: Decision) -> None:
        """Update an existing decision (replaces)."""
        # Same as save for simplicity (replace)
        await self.save(decision)

    async def get_recent_decisions(self, tenant_id: UUID, limit: int = 100) -> list[Decision]:
        try:
            stmt = (
                select(DecisionModel)
                .where(DecisionModel.tenant_id == str(tenant_id))
                .order_by(DecisionModel.computed_at.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            decisions = []
            for dm in models:
                stmt2 = select(ScoreDriversModel).where(ScoreDriversModel.risk_score_id == dm.id)
                result2 = await self.session.execute(stmt2)
                drivers = result2.scalars().all()
                stmt3 = select(RecommendationModel).where(RecommendationModel.finding_id == dm.finding_id)
                result3 = await self.session.execute(stmt3)
                rec = result3.scalar_one_or_none()
                decisions.append(DecisionMapper.to_domain(dm, drivers, rec))
            return decisions
        except Exception as exc:
            logger.error("Failed to get recent decisions", tenant_id=str(tenant_id), error=str(exc), exc_info=True)
            raise DatabaseError(f"Failed to get recent decisions: {exc}", operation="get_recent_decisions") from exc