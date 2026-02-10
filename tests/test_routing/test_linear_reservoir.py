from __future__ import annotations

import math

import pytest
from taqsim.node.reach import Reach
from taqsim.node.strategies import NoReachLoss
from taqsim.time import Frequency, Timestep

from taqsim_hydrology.routing.linear_reservoir import LinearReservoir


def _make_reach(k: float) -> Reach:
    model = LinearReservoir(k=k)
    return Reach(id="test-reach", routing_model=model, loss_rule=NoReachLoss())


def _ts(i: int) -> Timestep:
    return Timestep(index=i, frequency=Frequency.MONTHLY)


class TestLinearReservoir:
    def test_k_zero_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="k must be positive"):
            LinearReservoir(k=0)

    def test_k_negative_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="k must be positive"):
            LinearReservoir(k=-5)

    def test_initial_state_is_zero(self) -> None:
        reach = _make_reach(k=2.0)
        state = reach.routing_model.initial_state(reach)
        assert state == 0.0

    def test_exponential_decay_after_pulse(self) -> None:
        k = 3.0
        model = LinearReservoir(k=k)
        reach = _make_reach(k=k)
        c = math.exp(-1.0 / k)

        state = model.initial_state(reach)
        inflow = 100.0
        _, state = model.route(reach, inflow, state, _ts(0))

        outflows: list[float] = []
        for i in range(1, 20):
            outflow, state = model.route(reach, 0.0, state, _ts(i))
            outflows.append(outflow)

        for i in range(1, len(outflows)):
            ratio = outflows[i] / outflows[i - 1]
            assert ratio == pytest.approx(c, rel=1e-10)

    def test_steady_state_convergence(self) -> None:
        k = 2.0
        model = LinearReservoir(k=k)
        reach = _make_reach(k=k)
        state = model.initial_state(reach)
        inflow = 50.0

        for i in range(200):
            outflow, state = model.route(reach, inflow, state, _ts(i))

        assert outflow == pytest.approx(inflow, rel=1e-6)
        assert model.storage(state) == pytest.approx(inflow * k, rel=1e-6)

    def test_mass_conservation(self) -> None:
        k = 3.0
        model = LinearReservoir(k=k)
        reach = _make_reach(k=k)
        state = model.initial_state(reach)

        inflows = [100.0] * 5 + [0.0] * 50
        total_inflow = sum(inflows)
        total_outflow = 0.0

        for i, inflow in enumerate(inflows):
            outflow, state = model.route(reach, inflow, state, _ts(i))
            total_outflow += outflow

        final_storage = model.storage(state)
        assert total_outflow + final_storage == pytest.approx(total_inflow, rel=1e-10)

    def test_small_k_fast_response(self) -> None:
        k = 0.1
        model = LinearReservoir(k=k)
        reach = _make_reach(k=k)
        state = model.initial_state(reach)
        inflow = 100.0

        outflow, state = model.route(reach, inflow, state, _ts(0))

        assert outflow > inflow * 0.85
        # After just a few steps, outflow is nearly equal to inflow
        for i in range(1, 5):
            outflow, state = model.route(reach, inflow, state, _ts(i))
        assert outflow == pytest.approx(inflow, rel=1e-4)

    def test_large_k_slow_response(self) -> None:
        k = 10.0
        model = LinearReservoir(k=k)
        reach = _make_reach(k=k)
        state = model.initial_state(reach)
        inflow = 100.0

        outflow, state = model.route(reach, inflow, state, _ts(0))

        assert outflow < inflow * 0.2

    def test_storage_returns_state_directly(self) -> None:
        model = LinearReservoir(k=2.0)
        assert model.storage(0.0) == 0.0
        assert model.storage(42.5) == 42.5
        assert model.storage(999.0) == 999.0

    def test_frozen_instance(self) -> None:
        model = LinearReservoir(k=2.0)
        with pytest.raises(AttributeError):
            model.k = 5.0  # type: ignore[misc]

    def test_zero_inflow_with_existing_storage(self) -> None:
        k = 2.0
        model = LinearReservoir(k=k)
        reach = _make_reach(k=k)

        state = model.initial_state(reach)
        _, state = model.route(reach, 100.0, state, _ts(0))
        assert state > 0.0

        outflow, new_state = model.route(reach, 0.0, state, _ts(1))

        assert outflow > 0.0
        assert new_state < state
        assert outflow + new_state == pytest.approx(state, rel=1e-10)
