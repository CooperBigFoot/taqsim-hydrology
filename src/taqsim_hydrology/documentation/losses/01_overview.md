# Reach Losses

## Protocol

Reach loss models implement the `ReachLossRule` protocol defined in taqsim:

```python
@runtime_checkable
class ReachLossRule(Protocol):
    def calculate(self, reach: Reach, flow: float, t: Timestep) -> dict[LossReason, float]: ...
```

The `calculate` method receives the **routed outflow** (post-routing, pre-loss) and returns a dictionary mapping each `LossReason` to its loss amount. If total losses exceed outflow, taqsim scales them proportionally so net outflow is never negative.

See [taqsim Reach documentation](../../taqsim_docs/nodes/08_reach.md) for the full loss application pipeline.

## Planned Implementations

| Model | Module | Description | Status |
|-------|--------|-------------|--------|
| ConstantFraction | `taqsim_hydrology.losses.constant_fraction` | Fixed percentage loss per timestep | Not implemented |
| Evaporation | `taqsim_hydrology.losses.evaporation` | Temperature/PET-driven open channel evaporation | Not implemented |
| Seepage | `taqsim_hydrology.losses.seepage` | Infiltration losses through channel bed | Not implemented |
