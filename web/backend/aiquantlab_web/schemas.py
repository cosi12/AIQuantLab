"""API 响应契约。

这是前后端唯一的契约面；前端 TypeScript 类型与本模块一一对应。
已发布字段只新增、不重命名，也不改变语义。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------
# 数据集
# --------------------------------------------------------------------------


class QualityIssue(ApiModel):
    code: str
    severity: str
    message: str
    count: int | None = None
    samples: list[str] = []


class QualityReport(ApiModel):
    passed: bool | None = None
    row_count: int | None = None
    start: datetime | None = None
    end: datetime | None = None
    expected_candle_count: int | None = None
    missing_candle_count: int | None = None
    issues: list[QualityIssue] = []
    error_count: int = 0
    warning_count: int = 0
    generated_at: datetime | None = None


class DatasetProvenance(ApiModel):
    """数据来源与解释方式；缺少这些信息的数据集不可安全使用。"""

    symbol: str | None = None
    source: str | None = None
    timeframe: str | None = None
    source_timezone: str | None = None
    canonical_timezone: str | None = None
    timestamp_convention: str | None = None
    price_basis: str | None = None
    volume_type: str | None = None
    calendar_policy: str | None = None
    notes: list[str] = []
    created_at: datetime | None = None


class FeatureContract(ApiModel):
    """单个 causal feature 的契约，含 lookback 与 leakage 说明。"""

    name: str | None = None
    family: str | None = None
    input_columns: list[str] = []
    lookback_bars: int | None = None
    uses_current_bar: bool | None = None
    warm_up_bars: int | None = None
    output_dtype: str | None = None
    economic_meaning: str | None = None
    leakage_notes: str | None = None


class FeatureBundle(ApiModel):
    bundle_id: str | None = None
    revision: int | None = None
    features: list[FeatureContract] = []


class DatasetSummary(ApiModel):
    dataset_id: str
    kind: str
    data_file: str
    symbol: str | None = None
    timeframe: str | None = None
    source: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    row_count: int | None = None
    sha256: str | None = None
    column_count: int
    quality_passed: bool | None = None
    error_count: int
    warning_count: int
    missing_candle_count: int | None = None
    data_file_exists: bool
    created_at: datetime | None = None
    source_dataset_id: str | None = None
    provenance_inherited: bool = False


class DatasetDetail(DatasetSummary):
    schema_version: int | None = None
    columns: list[str] = []
    provenance: DatasetProvenance
    quality_report: QualityReport
    manifest_path: str
    data_path: str
    data_file_size_bytes: int | None = None
    used_by_experiments: list[str] = []
    derived_dataset_ids: list[str] = []
    feature_columns: list[str] = []
    feature_bundle: FeatureBundle | None = None
    feature_bundle_sha256: str | None = None
    source_ohlcv_sha256: str | None = None
    validity_column: str | None = None
    warm_up_bars: int | None = None
    code_version: str | None = None


class DatasetIntegrity(ApiModel):
    """按需 checksum 校验结果；不随列表请求自动执行。"""

    dataset_id: str
    expected_sha256: str | None = None
    actual_sha256: str | None = None
    matches: bool
    data_file_size_bytes: int | None = None
    checked_at: datetime


class DatasetPreview(ApiModel):
    dataset_id: str
    position: str
    limit: int
    row_count: int
    columns: list[str]
    rows: list[dict[str, Any]]


class QualityReportEntry(ApiModel):
    dataset_id: str
    kind: str
    symbol: str | None = None
    timeframe: str | None = None
    row_count: int | None = None
    quality_report: QualityReport


# --------------------------------------------------------------------------
# 实验
# --------------------------------------------------------------------------


class EventCondition(ApiModel):
    left_column: str | None = None
    operator: str | None = None
    right_column: str | None = None
    value: Any = None
    left_lag_bars: int | None = None
    right_lag_bars: int | None = None


class EventDefinition(ApiModel):
    name: str | None = None
    description: str | None = None
    combination: str | None = None
    conditions: list[EventCondition] = []


class HypothesisView(ApiModel):
    statement: str | None = None
    rationale: str | None = None
    null_hypothesis: str | None = None
    alternative_hypothesis: str | None = None
    expected_direction: str | None = None
    falsification_criteria: list[str] = []


class DatasetReferenceView(ApiModel):
    path: str | None = None
    sha256: str | None = None
    symbol: str | None = None
    timeframe: str | None = None
    sample_start: datetime | None = None
    sample_end: datetime | None = None
    dataset_id: str | None = None


class FeatureDatasetView(ApiModel):
    manifest_path: str | None = None
    manifest_sha256: str | None = None
    feature_bundle_sha256: str | None = None
    source_ohlcv_sha256: str | None = None
    validity_column: str | None = None


class EventStudyView(ApiModel):
    event: EventDefinition | None = None
    eligibility: EventDefinition | None = None
    price_column: str | None = None
    high_column: str | None = None
    low_column: str | None = None
    horizons_bars: list[int] = []
    return_type: str | None = None
    overlap_policy: str | None = None


class StatisticalSpecificationView(ApiModel):
    confidence_level: float | None = None
    bootstrap_method: str | None = None
    bootstrap_samples: int | None = None
    block_size: int | None = None
    random_seed: int | None = None
    minimum_sample_size: int | None = None


class DistributionSummary(ApiModel):
    count: int | None = None
    mean: float | None = None
    median: float | None = None
    standard_deviation: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    quantile_05: float | None = None
    quantile_25: float | None = None
    quantile_75: float | None = None
    quantile_95: float | None = None
    positive_probability: float | None = None


class HorizonStatistics(ApiModel):
    horizon_bars: int | None = None
    event_forward_return: DistributionSummary
    baseline_forward_return: DistributionSummary
    maximum_upside_return: DistributionSummary
    maximum_downside_return: DistributionSummary
    time_to_first_positive_bar: DistributionSummary
    time_to_first_negative_bar: DistributionSummary
    excess_mean_return: float | None = None
    excess_mean_confidence_interval: tuple[float, float] | None = None
    standardized_effect: float | None = None
    bootstrap_p_value: float | None = None
    adjusted_q_value: float | None = None
    warnings: list[str] = []
    confidence_interval_includes_zero: bool | None = None
    passes_significance_threshold: bool | None = None


class StatisticalReport(ApiModel):
    experiment_id: str | None = None
    revision: int | None = None
    config_sha256: str | None = None
    expected_direction: str | None = None
    confidence_level: float | None = None
    bootstrap_method: str | None = None
    bootstrap_samples: int | None = None
    random_seed: int | None = None
    multiple_testing_adjustment: str | None = None
    significance_threshold: float
    horizons: list[HorizonStatistics] = []
    warnings: list[str] = []


class RunIntegrity(ApiModel):
    """可复现性链：配置、数据、代码与全部 artifact 的 checksum。"""

    run_id: str | None = None
    config_sha256: str | None = None
    dataset_sha256: str | None = None
    frame_sha256: str | None = None
    code_version: str | None = None
    feature_manifest_sha256: str | None = None
    raw_event_count: int | None = None
    selected_event_count: int | None = None
    eligible_observation_count: int | None = None
    artifact_sha256: dict[str, str] = {}
    created_at: datetime | None = None


class ArtifactFile(ApiModel):
    name: str
    size_bytes: int | None = None
    recorded_sha256: str | None = None
    is_json: bool
    path: str


class RunSummary(ApiModel):
    run_id: str
    status: str | None = None
    code_version: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    frame_sha256: str | None = None
    error: str | None = None
    artifact_directory: str | None = None
    artifacts_available: bool


class ExperimentSummary(ApiModel):
    experiment_id: str
    revision: int
    title: str
    hypothesis_statement: str | None = None
    conclusion: str
    conclusion_notes: str | None = None
    registered_at: datetime | None = None
    config_sha256: str | None = None
    dataset_sha256: str | None = None
    symbol: str | None = None
    timeframe: str | None = None
    event_name: str | None = None
    horizons_bars: list[int] = []
    run_count: int
    completed_run_count: int
    failed_run_count: int
    latest_run_status: str | None = None
    registry_name: str


class ExperimentDetail(ExperimentSummary):
    registry_path: str
    hypothesis: HypothesisView | None = None
    dataset: DatasetReferenceView | None = None
    feature_dataset: FeatureDatasetView | None = None
    event_study: EventStudyView | None = None
    statistics: StatisticalSpecificationView | None = None
    tags: list[str] = []
    evidence_run_id: str | None = None
    statistical_report: StatisticalReport | None = None
    run_integrity: RunIntegrity | None = None
    runs: list[RunSummary] = []
    related_finding_ids: list[str] = []
    config_schema_version: int | None = None


# --------------------------------------------------------------------------
# 研究发现
# --------------------------------------------------------------------------


class SourceEvidence(ApiModel):
    experiment_id: str | None = None
    revision: int | None = None
    run_id: str | None = None
    config_sha256: str | None = None
    dataset_sha256: str | None = None
    statistical_report_sha256: str | None = None
    conclusion: str | None = None


class FindingSummary(ApiModel):
    finding_id: str
    title: str
    status: str
    symbol: str | None = None
    timeframe: str | None = None
    event_name: str | None = None
    source_experiment_id: str | None = None
    source_conclusion: str | None = None
    reviewed_at: datetime | None = None
    limitation_count: int
    non_claim_count: int


class FindingDetail(FindingSummary):
    market_behavior_claim: str | None = None
    evidence_summary: str | None = None
    economic_rationale: str | None = None
    human_reviewer_notes: str | None = None
    limitations: list[str] = []
    explicit_non_claims: list[str] = []
    applicable_event: EventDefinition | None = None
    source_evidence: SourceEvidence
    artifact_path: str
    derived_candidate_ids: list[str] = []


# --------------------------------------------------------------------------
# 策略候选与验证
# --------------------------------------------------------------------------


class PositionSizing(ApiModel):
    method: str | None = None
    fraction: float | None = None


class RiskRules(ApiModel):
    maximum_concurrent_positions: int | None = None
    stop_loss_fraction: float | None = None
    take_profit_fraction: float | None = None


class BacktestSummary(ApiModel):
    trade_count: int | None = None
    cumulative_return: float | None = None
    mean_trade_return: float | None = None
    median_trade_return: float | None = None
    standard_deviation_trade_return: float | None = None
    win_rate: float | None = None
    maximum_drawdown: float | None = None
    total_execution_cost_return: float | None = None


class ChronologicalSplit(ApiModel):
    name: str | None = None
    role: str | None = None
    start: datetime | None = None
    end: datetime | None = None


class SplitValidationResult(ApiModel):
    split: ChronologicalSplit
    primary: BacktestSummary
    stress: BacktestSummary
    criteria_passed: bool | None = None
    failures: list[str] = []


class ValidationCriteria(ApiModel):
    minimum_trades_per_evaluation_split: int | None = None
    require_positive_mean_return: bool | None = None
    maximum_drawdown_limit: float | None = None
    stress_slippage_bps_per_side: float | None = None


class ValidationPlan(ApiModel):
    plan_id: str | None = None
    candidate_sha256: str | None = None
    dataset_sha256: str | None = None
    frozen_before_validation: bool | None = None
    research_gate_passed: bool | None = None
    criteria: ValidationCriteria
    primary_execution_model: dict[str, Any] = {}
    splits: list[ChronologicalSplit] = []
    artifact_path: str


class ValidationReport(ApiModel):
    assessment: str | None = None
    research_gate_passed: bool | None = None
    plan_sha256: str | None = None
    candidate_sha256: str | None = None
    dataset_sha256: str | None = None
    split_results: list[SplitValidationResult] = []
    warnings: list[str] = []
    generated_at: datetime | None = None
    artifact_path: str


class CandidateSummary(ApiModel):
    candidate_id: str
    revision: int
    title: str
    symbol: str | None = None
    timeframe: str | None = None
    direction: str | None = None
    purpose: str | None = None
    research_gate_passed: bool | None = None
    source_finding_id: str | None = None
    source_finding_status: str | None = None
    source_evidence_sha256: str | None = None
    validation_assessment: str | None = None
    validated_at: datetime | None = None
    display_status: str
    holding_bars: int | None = None
    entry_event_name: str | None = None
    validated: bool


class CandidateDetail(CandidateSummary):
    signal_semantics: str | None = None
    execution_timing: str | None = None
    entry_event: EventDefinition | None = None
    position_sizing: PositionSizing
    risk_rules: RiskRules
    assumptions: list[str] = []
    validation_plan: ValidationPlan | None = None
    validation_report: ValidationReport | None = None
    validation_manifest: dict[str, Any] | None = None
    trade_ledgers: list[ArtifactFile] = []
    artifact_path: str
    artifact_directory: str


# --------------------------------------------------------------------------
# 报告
# --------------------------------------------------------------------------


class ReportSummary(ApiModel):
    report_id: str
    title: str
    file_name: str
    size_bytes: int
    modified_at: datetime
    path: str


class ReportDetail(ReportSummary):
    content: str


# --------------------------------------------------------------------------
# 总览与健康检查
# --------------------------------------------------------------------------


class OverviewCounts(ApiModel):
    datasets: int
    experiments: int
    experiment_runs: int
    findings: int
    strategy_candidates: int
    reports: int


class StatusTally(ApiModel):
    label: str
    count: int


class SystemCheck(ApiModel):
    name: str
    ok: bool
    detail: str


class LatestResult(ApiModel):
    """最新研究结果；status 使用 artifact 原始值，不做乐观改写。"""

    kind: str
    identifier: str
    title: str
    status: str
    detail: str | None = None
    occurred_at: datetime | None = None
    link: str


class Overview(ApiModel):
    counts: OverviewCounts
    experiments_by_conclusion: list[StatusTally] = []
    findings_by_status: list[StatusTally] = []
    candidates_by_display_status: list[StatusTally] = []
    recent_experiments: list[ExperimentSummary] = []
    latest_results: list[LatestResult] = []
    system_checks: list[SystemCheck] = []
    dataset_warning_total: int
    notices: list[str] = []
    generated_at: datetime


class Health(ApiModel):
    status: str
    version: str
    repository_root: str
    roots: dict[str, dict[str, Any]]
