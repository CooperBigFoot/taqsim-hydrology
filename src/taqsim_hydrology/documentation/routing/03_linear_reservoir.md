# Linear Reservoir

```python
@dataclass(frozen=True)
class LinearReservoir:
    k: float
```

## Parameters

| Field | Type | Constraint | Default | Description |
|-------|------|-----------|---------|-------------|
| `k` | `float` | `k > 0` | required | Storage coefficient (timesteps). Ratio of storage to outflow at steady state. |

## Validation

- `k <= 0` raises `ValueError: "k must be positive, got {k}"`

## State

- State type: `float` (current storage volume)
- Initial state: `0.0`

## Routing Equations

- `c = exp(-1/k)`
- `S_new = S * c + I * k * (1 - c)`
- `Q = S + I - S_new`

Derived from the continuous linear reservoir equation `dS/dt = I - S/k`, solved analytically over one timestep.

## Storage

- `storage(state) -> state`

State is the storage value directly. No transformation needed.

## Behavior

| `k` value | Behavior |
|-----------|----------|
| Small (e.g., 0.5) | Fast response. Storage drains quickly, outflow closely follows inflow. |
| Large (e.g., 10.0) | Slow response. Storage accumulates, outflow is heavily smoothed. |

## Steady State

- At steady state: `Q = I` and `S = k * I`
- The system reaches steady state when inflow is constant for a sufficient number of timesteps (proportional to `k`).

## Mass Conservation

`Q = S + I - S_new` guarantees `S + I = Q + S_new` at every timestep. Total mass is conserved.
