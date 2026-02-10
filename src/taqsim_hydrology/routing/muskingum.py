from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from taqsim.node.reach import Reach
    from taqsim.time import Timestep


class MuskingumState(NamedTuple):
    prev_inflow: float
    prev_outflow: float


@dataclass(frozen=True)
class Muskingum:
    k: float
    x: float = 0.0

    def __post_init__(self) -> None:
        if self.k <= 0:
            raise ValueError(f"k must be positive, got {self.k}")
        if not 0 <= self.x <= 0.5:
            raise ValueError(f"x must be in [0, 0.5], got {self.x}")

    def initial_state(self, reach: Reach) -> MuskingumState:
        return MuskingumState(prev_inflow=0.0, prev_outflow=0.0)

    def route(self, reach: Reach, inflow: float, state: MuskingumState, t: Timestep) -> tuple[float, MuskingumState]:
        denom = 2 * self.k * (1 - self.x) + 1
        c0 = (1 - 2 * self.k * self.x) / denom
        c1 = (1 + 2 * self.k * self.x) / denom
        c2 = (2 * self.k * (1 - self.x) - 1) / denom

        outflow = max(c0 * inflow + c1 * state.prev_inflow + c2 * state.prev_outflow, 0.0)
        return outflow, MuskingumState(prev_inflow=inflow, prev_outflow=outflow)

    def storage(self, state: MuskingumState) -> float:
        return self.k * (self.x * state.prev_inflow + (1 - self.x) * state.prev_outflow)
