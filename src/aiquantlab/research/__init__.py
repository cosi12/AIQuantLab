"""Reproducible market-behavior experiment framework."""

from aiquantlab.research.conditions import evaluate_event_definition
from aiquantlab.research.config import load_experiment_config, write_experiment_config
from aiquantlab.research.event_study import EventStudyResult, run_event_study
from aiquantlab.research.models import (
    BootstrapMethod,
    ConditionCombination,
    ConditionOperator,
    DatasetReference,
    EventCondition,
    EventDefinition,
    EventOverlapPolicy,
    EventStudySpecification,
    ExpectedDirection,
    ExperimentConfig,
    HypothesisDefinition,
    ReturnType,
    StatisticalReport,
    StatisticalSpecification,
)
from aiquantlab.research.registry import (
    ExperimentConclusion,
    ExperimentRegistry,
    RunStatus,
)
from aiquantlab.research.runner import ExperimentRunResult, run_experiment
from aiquantlab.research.statistics import build_statistical_report

__all__ = [
    "BootstrapMethod",
    "ConditionCombination",
    "ConditionOperator",
    "DatasetReference",
    "EventCondition",
    "EventDefinition",
    "EventOverlapPolicy",
    "EventStudyResult",
    "EventStudySpecification",
    "ExpectedDirection",
    "ExperimentConclusion",
    "ExperimentConfig",
    "ExperimentRegistry",
    "ExperimentRunResult",
    "HypothesisDefinition",
    "ReturnType",
    "RunStatus",
    "StatisticalReport",
    "StatisticalSpecification",
    "build_statistical_report",
    "evaluate_event_definition",
    "load_experiment_config",
    "run_event_study",
    "run_experiment",
    "write_experiment_config",
]

