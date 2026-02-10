from __future__ import annotations

import pytest
from taqsim.node.reach import Reach
from taqsim.node.strategies import NoReachLoss
from taqsim.time import Frequency, Timestep

from taqsim_hydrology.routing.muskingum import Muskingum, MuskingumState


def _make_reach(k: float = 1.0, x: float = 0.0) -> Reach:
    model = Muskingum(k=k, x=x)
    return Reach(id="test-reach", routing_model=model, loss_rule=NoReachLoss())


def _ts(i: int = 0) -> Timestep:
    return Timestep(index=i, frequency=Frequency.MONTHLY)


class TestMuskingumValidation:
    def test_k_zero_raises(self):
        with pytest.raises(ValueError, match="k must be positive"):
            Muskingum(k=0)

    def test_k_negative_raises(self):
        with pytest.raises(ValueError, match="k must be positive"):
            Muskingum(k=-1.0)

    def test_x_negative_raises(self):
        with pytest.raises(ValueError, match=r"x must be in \[0, 0\.5\]"):
            Muskingum(k=1.0, x=-0.1)

    def test_x_above_half_raises(self):
        with pytest.raises(ValueError, match=r"x must be in \[0, 0\.5\]"):
            Muskingum(k=1.0, x=0.6)

    def test_x_exactly_half_is_valid(self):
        m = Muskingum(k=1.0, x=0.5)
        assert m.x == 0.5

    def test_x_exactly_zero_is_valid(self):
        m = Muskingum(k=1.0, x=0.0)
        assert m.x == 0.0

    def test_valid_construction(self):
        m = Muskingum(k=2.0, x=0.3)
        assert m.k == 2.0
        assert m.x == 0.3


class TestMuskingumFrozen:
    def test_cannot_set_k(self):
        m = Muskingum(k=1.0, x=0.2)
        with pytest.raises(AttributeError):
            m.k = 5.0  # type: ignore[misc]

    def test_cannot_set_x(self):
        m = Muskingum(k=1.0, x=0.2)
        with pytest.raises(AttributeError):
            m.x = 0.4  # type: ignore[misc]


class TestMuskingumInitialState:
    def test_returns_zero_state(self):
        reach = _make_reach()
        state = reach.routing_model.initial_state(reach)
        assert state == MuskingumState(0.0, 0.0)

    def test_state_is_named_tuple(self):
        reach = _make_reach()
        state = reach.routing_model.initial_state(reach)
        assert state.prev_inflow == 0.0
        assert state.prev_outflow == 0.0


class TestMuskingumRoute:
    def test_coefficients_with_x_zero(self):
        m = Muskingum(k=0.5, x=0.0)
        reach = Reach(id="r", routing_model=m, loss_rule=NoReachLoss())
        state = m.initial_state(reach)

        # denom = 2*0.5*(1-0) + 1 = 2
        # c0 = (1 - 0) / 2 = 0.5
        # c1 = (1 + 0) / 2 = 0.5
        # c2 = (2*0.5*1 - 1) / 2 = 0.0
        outflow, new_state = m.route(reach, 100.0, state, _ts())

        # outflow = 0.5*100 + 0.5*0 + 0.0*0 = 50
        assert outflow == pytest.approx(50.0)
        assert new_state == MuskingumState(prev_inflow=100.0, prev_outflow=50.0)

    def test_second_step_uses_previous_state(self):
        m = Muskingum(k=0.5, x=0.0)
        reach = Reach(id="r", routing_model=m, loss_rule=NoReachLoss())
        state = m.initial_state(reach)

        outflow1, state = m.route(reach, 100.0, state, _ts(0))
        outflow2, state = m.route(reach, 0.0, state, _ts(1))

        # c0=0.5, c1=0.5, c2=0.0
        # step2: 0.5*0 + 0.5*100 + 0.0*50 = 50
        assert outflow2 == pytest.approx(50.0)
        assert state == MuskingumState(prev_inflow=0.0, prev_outflow=50.0)

    def test_outflow_clamped_to_zero(self):
        m = Muskingum(k=2.0, x=0.5)
        reach = Reach(id="r", routing_model=m, loss_rule=NoReachLoss())

        # Start with a high prev_outflow, then feed zero inflow
        # denom = 2*2*(1-0.5) + 1 = 3
        # c0 = (1 - 2*2*0.5)/3 = (1-2)/3 = -1/3
        # c1 = (1 + 2*2*0.5)/3 = (1+2)/3 = 1
        # c2 = (2*2*0.5 - 1)/3 = (2-1)/3 = 1/3
        # With state (0, 0) and inflow 100: outflow = -1/3*100 + 1*0 + 1/3*0 = -33.33
        # That would be negative, so clamped to 0
        state = MuskingumState(prev_inflow=0.0, prev_outflow=0.0)
        outflow, _ = m.route(reach, 100.0, state, _ts())
        # Actually: c0*100 + c1*0 + c2*0 = -33.33 -> clamped to 0
        assert outflow == 0.0

    def test_zero_inflow_zero_state_produces_zero_outflow(self):
        m = Muskingum(k=1.0, x=0.2)
        reach = Reach(id="r", routing_model=m, loss_rule=NoReachLoss())
        state = m.initial_state(reach)

        outflow, new_state = m.route(reach, 0.0, state, _ts())
        assert outflow == 0.0
        assert new_state == MuskingumState(0.0, 0.0)

    def test_zero_inflow_decays_outflow(self):
        m = Muskingum(k=1.0, x=0.0)
        reach = Reach(id="r", routing_model=m, loss_rule=NoReachLoss())
        state = m.initial_state(reach)

        # Push water in for two steps so state settles
        _, state = m.route(reach, 100.0, state, _ts(0))
        outflow, state = m.route(reach, 0.0, state, _ts(1))
        assert outflow > 0.0

        # From step 2 onward with zero inflow, outflow should decay monotonically
        prev_outflow = outflow
        for i in range(2, 6):
            outflow, state = m.route(reach, 0.0, state, _ts(i))
            assert 0.0 <= outflow < prev_outflow
            prev_outflow = outflow


class TestMuskingumMultiStep:
    def test_pulse_attenuation(self):
        m = Muskingum(k=1.0, x=0.0)
        reach = Reach(id="r", routing_model=m, loss_rule=NoReachLoss())
        state = m.initial_state(reach)

        inflows = [100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        outflows: list[float] = []

        for i, inflow in enumerate(inflows):
            outflow, state = m.route(reach, inflow, state, _ts(i))
            outflows.append(outflow)

        # Peak outflow should be less than peak inflow (attenuation)
        assert max(outflows) < 100.0

        # Outflow should be positive in early steps
        assert outflows[0] > 0.0

        # Outflows should decay monotonically after the first step
        for j in range(1, len(outflows) - 1):
            assert outflows[j] >= outflows[j + 1]

    def test_pulse_delay_with_x_half(self):
        m = Muskingum(k=1.0, x=0.5)
        reach = Reach(id="r", routing_model=m, loss_rule=NoReachLoss())
        state = m.initial_state(reach)

        # denom = 2*1*(1-0.5)+1 = 2
        # c0 = (1-2*1*0.5)/2 = 0, c1 = (1+2*1*0.5)/2 = 1, c2 = (2*1*0.5-1)/2 = 0
        # Pure translation: outflow at step i = inflow at step i-1
        inflows = [0.0, 100.0, 50.0, 0.0, 0.0]
        outflows: list[float] = []

        for i, inflow in enumerate(inflows):
            outflow, state = m.route(reach, inflow, state, _ts(i))
            outflows.append(outflow)

        assert outflows[0] == pytest.approx(0.0)
        assert outflows[1] == pytest.approx(0.0)
        assert outflows[2] == pytest.approx(100.0)
        assert outflows[3] == pytest.approx(50.0)
        assert outflows[4] == pytest.approx(0.0)


class TestMuskingumMassConservation:
    def test_total_outflow_equals_total_inflow(self):
        m = Muskingum(k=1.0, x=0.2)
        reach = Reach(id="r", routing_model=m, loss_rule=NoReachLoss())
        state = m.initial_state(reach)

        inflows = [100.0, 200.0, 50.0, 0.0] + [0.0] * 50
        total_inflow = sum(inflows)
        total_outflow = 0.0

        for i, inflow in enumerate(inflows):
            outflow, state = m.route(reach, inflow, state, _ts(i))
            total_outflow += outflow

        remaining_storage = m.storage(state)

        assert total_outflow + remaining_storage == pytest.approx(total_inflow, abs=1e-6)

    def test_long_run_drains_storage(self):
        m = Muskingum(k=2.0, x=0.1)
        reach = Reach(id="r", routing_model=m, loss_rule=NoReachLoss())
        state = m.initial_state(reach)

        inflows = [500.0] + [0.0] * 200
        total_outflow = 0.0

        for i, inflow in enumerate(inflows):
            outflow, state = m.route(reach, inflow, state, _ts(i))
            total_outflow += outflow

        assert m.storage(state) == pytest.approx(0.0, abs=1e-3)
        assert total_outflow == pytest.approx(500.0, abs=1e-3)


class TestMuskingumStorage:
    def test_storage_at_initial_state_is_zero(self):
        m = Muskingum(k=1.0, x=0.2)
        reach = Reach(id="r", routing_model=m, loss_rule=NoReachLoss())
        state = m.initial_state(reach)

        assert m.storage(state) == 0.0

    def test_storage_formula(self):
        m = Muskingum(k=2.0, x=0.3)
        state = MuskingumState(prev_inflow=100.0, prev_outflow=80.0)

        # K * (X*I + (1-X)*Q) = 2 * (0.3*100 + 0.7*80) = 2 * (30 + 56) = 172
        assert m.storage(state) == pytest.approx(172.0)

    def test_storage_with_pure_reservoir_x_zero(self):
        m = Muskingum(k=3.0, x=0.0)
        state = MuskingumState(prev_inflow=50.0, prev_outflow=40.0)

        # K * (0*50 + 1*40) = 3 * 40 = 120
        assert m.storage(state) == pytest.approx(120.0)

    def test_storage_after_routing(self):
        m = Muskingum(k=1.0, x=0.2)
        reach = Reach(id="r", routing_model=m, loss_rule=NoReachLoss())
        state = m.initial_state(reach)

        _, state = m.route(reach, 100.0, state, _ts(0))

        # Storage should be positive after receiving inflow
        assert m.storage(state) > 0.0
