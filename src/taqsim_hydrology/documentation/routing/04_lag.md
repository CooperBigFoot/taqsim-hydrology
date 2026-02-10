# Lag

Pure time-delay routing model. Shifts inflow forward by a fixed number of timesteps with no attenuation.

## Class Signature

```python
@dataclass(frozen=True)
class Lag:
    lag: int
```

## Parameters

| Field | Type | Constraint | Default | Description |
|-------|------|------------|---------|-------------|
| `lag` | `int` | `lag >= 0` | required | Number of timesteps to delay flow. |

## Validation

| Condition | Error |
|-----------|-------|
| `lag < 0` | `ValueError: "lag must be non-negative, got {lag}"` |

## State

- **Type**: `deque[float]` with `maxlen=lag`
- **Initial state (lag > 0)**: `deque([0.0] * lag, maxlen=lag)`
- **Initial state (lag == 0)**: `deque(maxlen=0)`

The deque acts as a fixed-size FIFO buffer. When a new value is appended and the deque is at capacity, the oldest value is automatically dropped.

## Routing Algorithm

**Case `lag == 0`**: pass-through. Returns `(inflow, state)` unchanged.

**Case `lag > 0`**:

1. `outflow = state[0]` -- oldest value exits the buffer
2. `state.append(inflow)` -- new inflow enters; deque auto-drops the oldest due to `maxlen`
3. Return `(outflow, state)`

Flow exits exactly `lag` timesteps after entering.

## Storage

```
storage(state) = sum(state)
```

Total volume currently held in the delay buffer.

## Behavior

| `lag` value | Behavior |
|-------------|----------|
| `0` | Pass-through. Outflow equals inflow. No delay, no storage. |
| `1` | One-step delay. Outflow at time `t` equals inflow at time `t-1`. |
| `n` | n-step delay. Outflow at time `t` equals inflow at time `t-n`. |

## Properties

- **No attenuation.** Peak flows pass through unchanged, only shifted in time.
- **Exact flow preservation.** Every inflow value appears as outflow exactly once, after `lag` timesteps.
- **Mass conservation.** `sum(inflows) = sum(outflows) + sum(state)` at any point.

## See Also

- [Routing Overview](01_overview.md)
- [Muskingum](02_muskingum.md)
- [Linear Reservoir](03_linear_reservoir.md)
