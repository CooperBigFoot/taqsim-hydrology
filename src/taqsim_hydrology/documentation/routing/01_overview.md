# Routing Models

Routing models implement transport physics for `Reach` nodes in taqsim. They control delay, attenuation, and storage behavior of water moving through channels.

## `RoutingModel` Protocol

Defined in taqsim core:

```python
@runtime_checkable
class RoutingModel(Protocol):
    def initial_state(self, reach: Reach) -> Any: ...
    def route(self, reach: Reach, inflow: float, state: Any, t: Timestep) -> tuple[float, Any]: ...
    def storage(self, state: Any) -> float: ...
```

| Method | Signature | Purpose |
|--------|-----------|---------|
| `initial_state` | `(reach: Reach) -> Any` | Returns the initial routing state for a reach |
| `route` | `(reach: Reach, inflow: float, state: Any, t: Timestep) -> tuple[float, Any]` | Transforms inflow + state into (outflow, new_state) |
| `storage` | `(state: Any) -> float` | Returns volume of water currently in transit |

## State Ownership

- Each model defines its own state type (`NamedTuple`, `float`, `deque`, etc.).
- State is opaque to the `Reach` — only the model reads/writes it.
- `initial_state` creates the starting state; `route` returns updated state each timestep.
- State must be treated as immutable between calls (models may return new objects or mutate in place).

## Available Implementations

| Model | Module | Key Behavior |
|-------|--------|-------------|
| [Muskingum](02_muskingum.md) | `taqsim_hydrology.routing.muskingum` | Weighted inflow/outflow routing with attenuation |
| [LinearReservoir](03_linear_reservoir.md) | `taqsim_hydrology.routing.linear_reservoir` | Exponential decay storage-discharge |
| [Lag](04_lag.md) | `taqsim_hydrology.routing.lag` | Pure time delay via FIFO buffer |

## Integration with taqsim

Routing models attach to `Reach` nodes via the `routing_model` parameter. See [taqsim Reach documentation](../../taqsim_docs/nodes/08_reach.md) for the full update pipeline.

```python
from taqsim.node import Reach, NoReachLoss
from taqsim_hydrology.routing import Muskingum

reach = Reach(
    id="main-channel",
    routing_model=Muskingum(k=2.0, x=0.2),
    loss_rule=NoReachLoss(),
)
```

## Mass Conservation

All implementations in this package preserve mass conservation: `sum(inflows) = sum(outflows) + delta(storage)`.
