# Muskingum

## Class Signature

```python
@dataclass(frozen=True)
class Muskingum:
    k: float
    x: float = 0.0
```

## Parameters

| Field | Type | Constraint | Default | Description |
|-------|------|------------|---------|-------------|
| `k` | `float` | `k > 0` | required | Storage-time constant (timesteps). Controls lag and attenuation. |
| `x` | `float` | `0 <= x <= 0.5` | `0.0` | Weighting factor. 0 = pure reservoir (max attenuation), 0.5 = pure translation (no attenuation). |

## Validation

| Condition | Error |
|-----------|-------|
| `k <= 0` | `ValueError: "k must be positive, got {k}"` |
| `x < 0` or `x > 0.5` | `ValueError: "x must be in [0, 0.5], got {x}"` |

## State

```python
class MuskingumState(NamedTuple):
    prev_inflow: float
    prev_outflow: float
```

Initial state: `MuskingumState(prev_inflow=0.0, prev_outflow=0.0)`

## Routing Equations

Coefficients are derived from `k` and `x`:

- `denom = 2k(1-x) + 1`
- `c0 = (1 - 2kx) / denom`
- `c1 = (1 + 2kx) / denom`
- `c2 = (2k(1-x) - 1) / denom`

Outflow at current timestep:

- `Q_out = max(c0 * I + c1 * I_prev + c2 * Q_prev, 0.0)`

Outflow is clamped to `0.0` to prevent negative flows.

Coefficients satisfy `c0 + c1 + c2 = 1` (mass conservation).

## Storage

- `S = k * (x * I_prev + (1-x) * Q_prev)`

Storage is computed from the most recent inflow and outflow values in state.

## Behavior

| `x` value | Behavior |
|-----------|----------|
| `0.0` | Pure linear reservoir. Maximum attenuation, no translation. |
| `0.5` | Pure translation. No attenuation, flow is shifted in time. |
| `0.0 < x < 0.5` | Mixed: partial attenuation and translation. |

Larger `k` increases both lag and attenuation. Smaller `k` produces faster, sharper response.

## Mass Conservation

`sum(inflows) = sum(outflows) + delta(storage)` holds across all timesteps.
