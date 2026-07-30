"""Main orchestrator for the scoring pipeline."""

from typing import Optional

from src.application.ports import CachePort, EventPort, LLMPort, ThreatIntelPort
from src.core.logging.logger import get_logger
from src.domain.entities import Finding
from src.domain.repositories import IAssetRepository
from src.engine.config import DEFAULT_CONFIG, EngineConfig
from src.engine.engine_result import EngineResult
from src.engine.strategies.base_strategy import Strategy
from src.engine.strategies.default_strategy import DefaultStrategy
from src.engine.workflow import Workflow

logger = get_logger("quantiquan.engine.orchestrator")


class Orchestrator:
    """Main orchestrator that executes the scoring pipeline.

    The orchestrator creates a workflow, injects dependencies, and runs
    the pipeline for each finding.
    """

    def __init__(
        self,
        cache_port: CachePort,
        threat_intel_port: ThreatIntelPort,
        llm_port: LLMPort,
        event_port: EventPort,
        asset_repository: IAssetRepository,
        config: Optional[EngineConfig] = None,
        strategy: Optional[Strategy] = None,
    ) -> None:
        """Initialize orchestrator.

        Args:
            cache_port: Cache port for context caching.
            threat_intel_port: Threat intelligence port.
            llm_port: LLM port for summaries.
            event_port: Event port for publishing.
            asset_repository: Asset repository for business context.
            config: Engine configuration.
            strategy: Scoring strategy (default: DefaultStrategy).
        """
        self.cache_port = cache_port
        self.threat_intel_port = threat_intel_port
        self.llm_port = llm_port
        self.event_port = event_port
        self.asset_repository = asset_repository
        self.config = config or DEFAULT_CONFIG
        self.strategy = strategy or DefaultStrategy()
        self.logger = logger.bind(component="orchestrator")

    async def run(self, finding: Finding) -> EngineResult:
        """Execute the pipeline for a single finding.

        Args:
            finding: Finding entity to process.

        Returns:
            EngineResult: Pipeline result containing decision and metadata.
        """
        self.logger.info(
            "Starting pipeline",
            finding_id=str(finding.id),
            tenant_id=str(finding.tenant_id),
        )

        # Build workflow with dependencies
        workflow = Workflow(
            cache_port=self.cache_port,
            threat_intel_port=self.threat_intel_port,
            llm_port=self.llm_port,
            asset_repository=self.asset_repository,
            config=self.config,
            strategy=self.strategy,
            event_port=self.event_port,
        )

        result = await workflow.execute(finding)

        if result.has_error():
            self.logger.warning(
                "Pipeline completed with errors",
                finding_id=str(finding.id),
                errors=result.errors,
            )
        else:
            self.logger.info(
                "Pipeline completed successfully",
                finding_id=str(finding.id),
                tier=result.tier,
                bis=result.risk_score.final_bis if result.risk_score else None,
            )

        return result