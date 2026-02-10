from collections import deque

import pytest
from taqsim.node.reach import Reach
from taqsim.node.strategies import NoReachLoss
from taqsim.time import Frequency, Timestep

from taqsim_hydrology.routing.lag import Lag


def _make_reach(lag: Lag) -> Reach:
    return Reach(id="test-reach", routing_model=lag, loss_rule=NoReachLoss())


def _ts(i: int) -> Timestep:
    return Timestep(index=i, frequency=Frequency.MONTHLY)


def _run_sequence(lag: Lag, inflows: list[float]) -> list[float]:
    reach = _make_reach(lag)
    state = lag.initial_state(reach)
    outflows: list[float] = []
    for i, inflow in enumerate(inflows):
        outflow, state = lag.route(reach, inflow, state, _ts(i))
        outflows.append(outflow)
    return outflows


class TestLag:
    def test_negative_lag_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="lag must be non-negative"):
            Lag(lag=-1)

    def test_zero_lag_is_pass_through(self) -> None:
        lag = Lag(lag=0)
        outflows = _run_sequence(lag, [100.0, 200.0, 300.0])
        assert outflows == [100.0, 200.0, 300.0]

    def test_exact_delay_of_three(self) -> None:
        lag = Lag(lag=3)
        outflows = _run_sequence(lag, [100.0, 200.0, 300.0, 400.0, 500.0])
        assert outflows == [0.0, 0.0, 0.0, 100.0, 200.0]

    def test_initial_state_returns_zero_deque_with_correct_length(self) -> None:
        lag = Lag(lag=4)
        reach = _make_reach(lag)
        state = lag.initial_state(reach)
        assert isinstance(state, deque)
        assert len(state) == 4
        assert state.maxlen == 4
        assert list(state) == [0.0, 0.0, 0.0, 0.0]

    def test_initial_state_zero_lag_has_zero_maxlen(self) -> None:
        lag = Lag(lag=0)
        reach = _make_reach(lag)
        state = lag.initial_state(reach)
        assert isinstance(state, deque)
        assert len(state) == 0
        assert state.maxlen == 0

    def test_mass_conservation(self) -> None:
        lag = Lag(lag=3)
        reach = _make_reach(lag)
        state = lag.initial_state(reach)
        inflows = [100.0, 200.0, 300.0, 400.0, 500.0]
        total_outflow = 0.0
        for i, inflow in enumerate(inflows):
            outflow, state = lag.route(reach, inflow, state, _ts(i))
            total_outflow += outflow
        total_inflow = sum(inflows)
        remaining_storage = lag.storage(state)
        assert total_outflow + remaining_storage == pytest.approx(total_inflow)

    def test_storage_returns_sum_of_buffered_values(self) -> None:
        lag = Lag(lag=3)
        reach = _make_reach(lag)
        state = lag.initial_state(reach)
        # Route a few values to populate the buffer
        _, state = lag.route(reach, 100.0, state, _ts(0))
        _, state = lag.route(reach, 200.0, state, _ts(1))
        assert lag.storage(state) == pytest.approx(100.0 + 200.0 + 0.0)

    def test_storage_after_buffer_is_full(self) -> None:
        lag = Lag(lag=2)
        reach = _make_reach(lag)
        state = lag.initial_state(reach)
        _, state = lag.route(reach, 50.0, state, _ts(0))
        _, state = lag.route(reach, 75.0, state, _ts(1))
        # Buffer is now [50, 75], both zero-slots replaced
        assert lag.storage(state) == pytest.approx(125.0)

    def test_frozen_instance_is_immutable(self) -> None:
        lag = Lag(lag=5)
        with pytest.raises(AttributeError):
            lag.lag = 10  # type: ignore[misc]

    def test_lag_of_one_outputs_previous_inflow(self) -> None:
        lag = Lag(lag=1)
        outflows = _run_sequence(lag, [10.0, 20.0, 30.0, 40.0])
        assert outflows == [0.0, 10.0, 20.0, 30.0]

    def test_constant_inflow_reaches_steady_state(self) -> None:
        lag_amount = 4
        lag = Lag(lag=lag_amount)
        constant = 42.0
        inflows = [constant] * 10
        outflows = _run_sequence(lag, inflows)
        # First `lag` timesteps produce 0, then constant thereafter
        assert outflows[:lag_amount] == [0.0] * lag_amount
        assert all(o == pytest.approx(constant) for o in outflows[lag_amount:])
