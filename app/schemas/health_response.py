from dataclasses import dataclass, asdict
from typing import Dict

from app.core.schemas.health_checks import HealthStatus, HealthChecks


@dataclass
class HealthResponse:
    status: HealthStatus
    checks: HealthChecks

    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "checks": asdict(self.checks),
        }
