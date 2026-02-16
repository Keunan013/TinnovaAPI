from dataclasses import dataclass
from typing import List

from app.domain.veiculo import Veiculo


@dataclass(frozen=True)
class PageResult:
    items: List[Veiculo]
    total: int
    page: int
    size: int
