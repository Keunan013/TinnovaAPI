from dataclasses import dataclass

from app.core.enums.health_status import HealthStatus


@dataclass
class HealthChecks:
    database: HealthStatus
    redis: HealthStatus
    fx_provider: HealthStatus
