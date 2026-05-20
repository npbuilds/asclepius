"""Scorecard engine tests."""

from __future__ import annotations

import pytest

from app.domain import (
    AssetInput,
    DiligenceRecord,
    Modality,
    Phase,
    TherapeuticArea,
)
from app.modules.scorecard.engine import PILLAR_WEIGHTS, compute
from app.modules.scorecard.schemas import PillarInput, ScorecardInput
from app.registry import reset_registry_for_tests


def setup_module(_mod) -> None:
    reset_registry_for_tests()


def _record() -> DiligenceRecord:
    return DiligenceRecord(
        asset=AssetInput(
            asset_name="Test",
            phase=Phase.PHASE_2,
            therapeutic_area=TherapeuticArea.ONCOLOGY,
            modality=Modality.SMALL_MOLECULE,
        )
    )


def _all_equal(score: float, **flags) -> ScorecardInput:
    pi = PillarInput(score=score)
    return ScorecardInput(
        clinical=pi,
        regulatory=pi,
        competitive=pi,
        manufacturing=pi,
        ip=pi,
        financial=pi,
        team=pi,
        computational=pi,
        **flags,
    )


def test_pillar_weights_sum_to_one() -> None:
    assert abs(sum(PILLAR_WEIGHTS.values()) - 1.0) < 1e-9


def test_all_5s_gives_aggregate_5() -> None:
    out = compute(_record(), scorecard_input=_all_equal(5.0))
    assert out.aggregate_score == 5.0
    assert out.recommendation == "hold"


def test_all_9s_strong_buy() -> None:
    out = compute(_record(), scorecard_input=_all_equal(9.0))
    assert out.aggregate_score >= 8.0
    assert out.recommendation == "strong_buy"


def test_all_3s_avoid() -> None:
    out = compute(_record(), scorecard_input=_all_equal(3.0))
    assert out.aggregate_score < 3.5
    assert out.recommendation == "avoid"


def test_red_flag_caps_recommendation() -> None:
    """High aggregate with a red flag should auto-cap at 'cautious'."""
    out = compute(
        _record(),
        scorecard_input=_all_equal(9.0, red_flags=["going concern risk"]),
    )
    assert out.aggregate_score >= 8.0  # numeric aggregate unchanged
    assert out.recommendation == "cautious"  # but recommendation capped


def test_green_flags_boost_aggregate() -> None:
    base = compute(_record(), scorecard_input=_all_equal(6.0))
    boosted = compute(
        _record(),
        scorecard_input=_all_equal(
            6.0, green_flags=["insider buying >$500K", "Big Pharma partnership"]
        ),
    )
    assert boosted.aggregate_score > base.aggregate_score
    # +0.5 per green flag, 2 flags → +1.0
    assert abs(boosted.aggregate_score - (base.aggregate_score + 1.0)) < 0.001


def test_aggregate_clamped_to_10() -> None:
    """Even with high pillars + multiple green flags, aggregate caps at 10.0."""
    out = compute(
        _record(),
        scorecard_input=_all_equal(
            10.0,
            green_flags=["g1", "g2", "g3", "g4"],
        ),
    )
    assert out.aggregate_score == 10.0


def test_eight_pillars_returned_with_correct_weights() -> None:
    out = compute(_record(), scorecard_input=_all_equal(7.0))
    assert len(out.pillars) == 8
    names = [p.name for p in out.pillars]
    assert "computational" in names  # the novel 8th pillar
    for p in out.pillars:
        assert PILLAR_WEIGHTS[p.name] == p.weight


def test_missing_scorecard_input_raises() -> None:
    with pytest.raises(ValueError):
        compute(_record())  # no scorecard_input
