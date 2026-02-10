# taqsim-hydrology — Project Goals

## What is this?

A companion package for [taqsim](https://github.com/hydrosolutions/taqsim) that provides hydrology-specific implementations: routing models for river reaches, loss functions for channels and reservoirs, and utilities for wiring [pydrology](https://github.com/CooperBigFoot/pydrology) rainfall-runoff models into taqsim simulations.

## Why a separate repo?

taqsim core is domain-agnostic — it defines the simulation engine, node types, event sourcing, and optimization framework. It exposes protocols (`RoutingModel`, `ReachLossRule`, `LossRule`) but ships only no-op defaults (`NoRouting`, `NoReachLoss`, `NoLoss`). This repo provides the real hydrology.

## Scope

### 1. Routing Models (satisfy taqsim's `RoutingModel` protocol)

Three channel routing models for use in `Reach` nodes:

| Model | What it does | Parameters | State |
|---|---|---|---|
| **Muskingum** | Classic linear storage-discharge routing | K (travel time), X (weighting 0–0.5) | Previous inflow + outflow |
| **Linear Reservoir** | Exponential decay, Q = S/K | K (storage constant) | Current storage volume |
| **Lag** | Pure time delay using a deque | lag (integer timesteps) | Deque of buffered inflows |

All three are frozen dataclasses implementing:
```python
initial_state(reach) -> state
route(reach, inflow, state, t) -> (outflow, new_state)
storage(state) -> float
```

### 2. Loss Functions

**For reaches** (satisfy `ReachLossRule` — losses applied to routed outflow):
- **Constant fraction** — `loss = flow * fraction`

**For storage nodes** (satisfy `LossRule` — losses applied to stored water):
- **Evaporation** — temperature-dependent, reads from `auxiliary_data["temperature"]`
- **Seepage** — proportional to stored volume, `loss = rate * current_storage`

### 3. Source Precompute Utilities

Functions that run pydrology rainfall-runoff models and return a taqsim `TimeSeries`, ready to plug into a `Source` node:

- Takes pydrology `ForcingData` + model parameters
- Runs the model (GR6J, GR2M, HBV-Light, GR6J-CemaNeige)
- Returns `TimeSeries(values=streamflow.tolist())`

This is a **pre-compute** approach — hydrological model parameters are NOT optimizable within taqsim's loop. The trade-off is simplicity: zero changes to taqsim core, and the user calibrates their hydro model separately (via pydrology's own calibration framework) before feeding results into taqsim.

## Architecture

```
src/taqsim_hydrology/
├── routing/
│   ├── muskingum.py
│   ├── linear_reservoir.py
│   └── lag.py
├── losses/
│   ├── constant_fraction.py    (ReachLossRule)
│   ├── evaporation.py          (LossRule — Storage)
│   └── seepage.py              (LossRule — Storage)
└── sources/
    └── precompute.py           (pydrology model → TimeSeries)
```

## Dependencies

- **taqsim** — protocols, node types, TimeSeries
- **pydrology** — rainfall-runoff models (GR6J, GR2M, HBV-Light, GR6J-CemaNeige)

## Key Contracts (from taqsim)

All implementations are **frozen dataclasses** (physical models, not optimizable strategies). They satisfy taqsim protocols via structural typing — no inheritance from taqsim classes required.

```python
# RoutingModel protocol
class RoutingModel(Protocol):
    def initial_state(self, reach: Reach) -> Any: ...
    def route(self, reach: Reach, inflow: float, state: Any, t: Timestep) -> tuple[float, Any]: ...
    def storage(self, state: Any) -> float: ...

# ReachLossRule protocol
class ReachLossRule(Protocol):
    def calculate(self, reach: Reach, flow: float, t: Timestep) -> dict[LossReason, float]: ...

# LossRule protocol (Storage)
class LossRule(Protocol):
    def calculate(self, node: Storage, t: Timestep) -> dict[LossReason, float]: ...
```
