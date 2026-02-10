from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from taqsim.node.reach import Reach
    from taqsim.time import Timestep


@dataclass(frozen=True)
class LinearReservoir:
    k: float

    def __post_init__(self) -> None:
        if self.k <= 0:
            raise ValueError(f"k must be positive, got {self.k}")

    def initial_state(self, reach: Reach) -> float:
        return 0.0

    def route(self, reach: Reach, inflow: float, state: float, t: Timestep) -> tuple[float, float]:
        c = math.exp(-1.0 / self.k)
        new_storage = state * c + inflow * self.k * (1 - c)
        outflow = state + inflow - new_storage
        return outflow, new_storage

    def storage(self, state: float) -> float:
        return state
