"""Decision repository implementation using SQLAlchemy."""

from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import delete, select, func
from sqlalchemy.dialects.postgresql import insert
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
        """
        Save a decision using PostgreSQL UPSERT (Idempotency).
        
        If a decision with the same (finding_id, job_id) already exists,
        this updates it instead of creating a duplicate.
        """
        try:
            # 1. Convert decision to models
            decision_model, driver_models, rec_model = DecisionMapper.to_model(decision)

            # 2. Explicitly set the new fields (safety net if mapper misses them)
            decision_model.job_id = str(decision.job_id)
            decision_model.trace_id = str(decision.trace_id)
            decision_model.knowledge_version = decision.knowledge_version

            # 3. Ensure ID is generated if not provided
            if decision_model.id is None:
                decision_model.id = str(uuid4())

            # 4. Prepare the data dict for the UPSERT
            #    created_at and updated_at are omitted so the DB uses server_default
            model_dict = {
                'id': decision_model.id,
                'finding_id': decision_model.finding_id,
                'tenant_id': decision_model.tenant_id,
                'job_id': decision_model.job_id,
                'trace_id': decision_model.trace_id,
                'knowledge_version': decision_model.knowledge_version,
                'bis': decision_model.bis,
                'tier': decision_model.tier,
                'confidence': decision_model.confidence,
                'computed_at': decision_model.computed_at,
                'version': decision_model.version,
                # created_at and updated_at are removed – DB defaults will apply
            }

            # 5. PostgreSQL UPSERT: ON CONFLICT (finding_id, job_id) DO UPDATE
            stmt = insert(DecisionModel).values(**model_dict)
            stmt = stmt.on_conflict_do_update(
                constraint='uq_risk_scores_finding_job',
                set_={
                    'tenant_id': stmt.excluded.tenant_id,
                    'bis': stmt.excluded.bis,
                    'tier': stmt.excluded.tier,
                    'confidence': stmt.excluded.confidence,
                    'computed_at': stmt.excluded.computed_at,
                    'version': stmt.excluded.version,
                    'trace_id': stmt.excluded.trace_id,
                    'knowledge_version': stmt.excluded.knowledge_version,
                    'updated_at': func.now(),  # Always update timestamp on conflict
                }
            ).returning(DecisionModel.id)

            # Execute the UPSERT and retrieve the final decision ID
            result = await self.session.execute(stmt)
            decision_id = result.scalar_one()

            # 6. Clean up old drivers and recommendation for this decision
            await self.session.execute(
                delete(ScoreDriversModel).where(ScoreDriversModel.risk_score_id == decision_id)
            )
            await self.session.execute(
                delete(RecommendationModel).where(RecommendationModel.finding_id == decision_model.finding_id)
            )

            # 7. Add the new drivers
            for dm in driver_models:
                dm.risk_score_id = decision_id
                self.session.add(dm)

            # 8. Add the new recommendation (if it exists)
            if rec_model:
                rec_model.finding_id = decision_model.finding_id
                self.session.add(rec_model)

        except Exception as exc:
            logger.error("Failed to save decision", finding_id=str(decision.finding_id), error=str(exc), exc_info=True)
            raise DatabaseError(f"Failed to save decision: {exc}", operation="save") from exc

    async def update(self, decision: Decision) -> None:
        """Update an existing decision (replaces)."""
        # Same as save for simplicity (upsert handles both insert and update)
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