/**
 * 与后端 aiquantlab_web/schemas.py 一一对应的契约类型。
 * 后端字段只新增不重命名；此文件必须与之同步修改。
 */

export interface QualityIssue {
  code: string;
  severity: string;
  message: string;
  count: number | null;
  samples: string[];
}

export interface QualityReport {
  passed: boolean | null;
  row_count: number | null;
  start: string | null;
  end: string | null;
  expected_candle_count: number | null;
  missing_candle_count: number | null;
  issues: QualityIssue[];
  error_count: number;
  warning_count: number;
  generated_at: string | null;
}

export interface DatasetProvenance {
  symbol: string | null;
  source: string | null;
  timeframe: string | null;
  source_timezone: string | null;
  canonical_timezone: string | null;
  timestamp_convention: string | null;
  price_basis: string | null;
  volume_type: string | null;
  calendar_policy: string | null;
  notes: string[];
  created_at: string | null;
}

export interface FeatureContract {
  name: string | null;
  family: string | null;
  input_columns: string[];
  lookback_bars: number | null;
  uses_current_bar: boolean | null;
  warm_up_bars: number | null;
  output_dtype: string | null;
  economic_meaning: string | null;
  leakage_notes: string | null;
}

export interface FeatureBundle {
  bundle_id: string | null;
  revision: number | null;
  features: FeatureContract[];
}

export interface DatasetSummary {
  dataset_id: string;
  kind: string;
  data_file: string;
  symbol: string | null;
  timeframe: string | null;
  source: string | null;
  start: string | null;
  end: string | null;
  row_count: number | null;
  sha256: string | null;
  column_count: number;
  quality_passed: boolean | null;
  error_count: number;
  warning_count: number;
  missing_candle_count: number | null;
  data_file_exists: boolean;
  created_at: string | null;
  source_dataset_id: string | null;
  provenance_inherited: boolean;
}

export interface DatasetDetail extends DatasetSummary {
  schema_version: number | null;
  columns: string[];
  provenance: DatasetProvenance;
  quality_report: QualityReport;
  manifest_path: string;
  data_path: string;
  data_file_size_bytes: number | null;
  used_by_experiments: string[];
  derived_dataset_ids: string[];
  feature_columns: string[];
  feature_bundle: FeatureBundle | null;
  feature_bundle_sha256: string | null;
  source_ohlcv_sha256: string | null;
  validity_column: string | null;
  warm_up_bars: number | null;
  code_version: string | null;
}

export interface DatasetIntegrity {
  dataset_id: string;
  expected_sha256: string | null;
  actual_sha256: string | null;
  matches: boolean;
  data_file_size_bytes: number | null;
  checked_at: string;
}

export interface DatasetPreview {
  dataset_id: string;
  position: string;
  limit: number;
  row_count: number;
  columns: string[];
  rows: Record<string, unknown>[];
}

export interface QualityReportEntry {
  dataset_id: string;
  kind: string;
  symbol: string | null;
  timeframe: string | null;
  row_count: number | null;
  quality_report: QualityReport;
}

export interface EventCondition {
  left_column: string | null;
  operator: string | null;
  right_column: string | null;
  value: unknown;
  left_lag_bars: number | null;
  right_lag_bars: number | null;
}

export interface EventDefinition {
  name: string | null;
  description: string | null;
  combination: string | null;
  conditions: EventCondition[];
}

export interface HypothesisView {
  statement: string | null;
  rationale: string | null;
  null_hypothesis: string | null;
  alternative_hypothesis: string | null;
  expected_direction: string | null;
  falsification_criteria: string[];
}

export interface DatasetReferenceView {
  path: string | null;
  sha256: string | null;
  symbol: string | null;
  timeframe: string | null;
  sample_start: string | null;
  sample_end: string | null;
  dataset_id: string | null;
}

export interface FeatureDatasetView {
  manifest_path: string | null;
  manifest_sha256: string | null;
  feature_bundle_sha256: string | null;
  source_ohlcv_sha256: string | null;
  validity_column: string | null;
}

export interface EventStudyView {
  event: EventDefinition | null;
  eligibility: EventDefinition | null;
  price_column: string | null;
  high_column: string | null;
  low_column: string | null;
  horizons_bars: number[];
  return_type: string | null;
  overlap_policy: string | null;
}

export interface StatisticalSpecificationView {
  confidence_level: number | null;
  bootstrap_method: string | null;
  bootstrap_samples: number | null;
  block_size: number | null;
  random_seed: number | null;
  minimum_sample_size: number | null;
}

export interface DistributionSummary {
  count: number | null;
  mean: number | null;
  median: number | null;
  standard_deviation: number | null;
  minimum: number | null;
  maximum: number | null;
  quantile_05: number | null;
  quantile_25: number | null;
  quantile_75: number | null;
  quantile_95: number | null;
  positive_probability: number | null;
}

export interface HorizonStatistics {
  horizon_bars: number | null;
  event_forward_return: DistributionSummary;
  baseline_forward_return: DistributionSummary;
  maximum_upside_return: DistributionSummary;
  maximum_downside_return: DistributionSummary;
  time_to_first_positive_bar: DistributionSummary;
  time_to_first_negative_bar: DistributionSummary;
  excess_mean_return: number | null;
  excess_mean_confidence_interval: [number, number] | null;
  standardized_effect: number | null;
  bootstrap_p_value: number | null;
  adjusted_q_value: number | null;
  warnings: string[];
  confidence_interval_includes_zero: boolean | null;
  passes_significance_threshold: boolean | null;
}

export interface StatisticalReport {
  experiment_id: string | null;
  revision: number | null;
  config_sha256: string | null;
  expected_direction: string | null;
  confidence_level: number | null;
  bootstrap_method: string | null;
  bootstrap_samples: number | null;
  random_seed: number | null;
  multiple_testing_adjustment: string | null;
  significance_threshold: number;
  horizons: HorizonStatistics[];
  warnings: string[];
}

export interface RunIntegrity {
  run_id: string | null;
  config_sha256: string | null;
  dataset_sha256: string | null;
  frame_sha256: string | null;
  code_version: string | null;
  feature_manifest_sha256: string | null;
  raw_event_count: number | null;
  selected_event_count: number | null;
  eligible_observation_count: number | null;
  artifact_sha256: Record<string, string>;
  created_at: string | null;
}

export interface ArtifactFile {
  name: string;
  size_bytes: number | null;
  recorded_sha256: string | null;
  is_json: boolean;
  path: string;
}

export interface RunSummary {
  run_id: string;
  status: string | null;
  code_version: string | null;
  started_at: string | null;
  completed_at: string | null;
  frame_sha256: string | null;
  error: string | null;
  artifact_directory: string | null;
  artifacts_available: boolean;
}

export interface ExperimentSummary {
  experiment_id: string;
  revision: number;
  title: string;
  hypothesis_statement: string | null;
  conclusion: string;
  conclusion_notes: string | null;
  registered_at: string | null;
  config_sha256: string | null;
  dataset_sha256: string | null;
  symbol: string | null;
  timeframe: string | null;
  event_name: string | null;
  horizons_bars: number[];
  run_count: number;
  completed_run_count: number;
  failed_run_count: number;
  latest_run_status: string | null;
  registry_name: string;
}

export interface ExperimentDetail extends ExperimentSummary {
  registry_path: string;
  hypothesis: HypothesisView | null;
  dataset: DatasetReferenceView | null;
  feature_dataset: FeatureDatasetView | null;
  event_study: EventStudyView | null;
  statistics: StatisticalSpecificationView | null;
  tags: string[];
  evidence_run_id: string | null;
  statistical_report: StatisticalReport | null;
  run_integrity: RunIntegrity | null;
  runs: RunSummary[];
  related_finding_ids: string[];
  config_schema_version: number | null;
}

export interface SourceEvidence {
  experiment_id: string | null;
  revision: number | null;
  run_id: string | null;
  config_sha256: string | null;
  dataset_sha256: string | null;
  statistical_report_sha256: string | null;
  conclusion: string | null;
}

export interface FindingSummary {
  finding_id: string;
  title: string;
  status: string;
  symbol: string | null;
  timeframe: string | null;
  event_name: string | null;
  source_experiment_id: string | null;
  source_conclusion: string | null;
  reviewed_at: string | null;
  limitation_count: number;
  non_claim_count: number;
}

export interface FindingDetail extends FindingSummary {
  market_behavior_claim: string | null;
  evidence_summary: string | null;
  economic_rationale: string | null;
  human_reviewer_notes: string | null;
  limitations: string[];
  explicit_non_claims: string[];
  applicable_event: EventDefinition | null;
  source_evidence: SourceEvidence;
  artifact_path: string;
  derived_candidate_ids: string[];
}

export interface PositionSizing {
  method: string | null;
  fraction: number | null;
}

export interface RiskRules {
  maximum_concurrent_positions: number | null;
  stop_loss_fraction: number | null;
  take_profit_fraction: number | null;
}

export interface BacktestSummary {
  trade_count: number | null;
  cumulative_return: number | null;
  mean_trade_return: number | null;
  median_trade_return: number | null;
  standard_deviation_trade_return: number | null;
  win_rate: number | null;
  maximum_drawdown: number | null;
  total_execution_cost_return: number | null;
}

export interface ChronologicalSplit {
  name: string | null;
  role: string | null;
  start: string | null;
  end: string | null;
}

export interface SplitValidationResult {
  split: ChronologicalSplit;
  primary: BacktestSummary;
  stress: BacktestSummary;
  criteria_passed: boolean | null;
  failures: string[];
}

export interface ValidationCriteria {
  minimum_trades_per_evaluation_split: number | null;
  require_positive_mean_return: boolean | null;
  maximum_drawdown_limit: number | null;
  stress_slippage_bps_per_side: number | null;
}

export interface ValidationPlan {
  plan_id: string | null;
  candidate_sha256: string | null;
  dataset_sha256: string | null;
  frozen_before_validation: boolean | null;
  research_gate_passed: boolean | null;
  criteria: ValidationCriteria;
  primary_execution_model: Record<string, unknown>;
  splits: ChronologicalSplit[];
  artifact_path: string;
}

export interface ValidationReport {
  assessment: string | null;
  research_gate_passed: boolean | null;
  plan_sha256: string | null;
  candidate_sha256: string | null;
  dataset_sha256: string | null;
  split_results: SplitValidationResult[];
  warnings: string[];
  generated_at: string | null;
  artifact_path: string;
}

export interface CandidateSummary {
  candidate_id: string;
  revision: number;
  title: string;
  symbol: string | null;
  timeframe: string | null;
  direction: string | null;
  purpose: string | null;
  research_gate_passed: boolean | null;
  source_finding_id: string | null;
  source_finding_status: string | null;
  source_evidence_sha256: string | null;
  validation_assessment: string | null;
  validated_at: string | null;
  display_status: string;
  holding_bars: number | null;
  entry_event_name: string | null;
  validated: boolean;
}

export interface CandidateDetail extends CandidateSummary {
  signal_semantics: string | null;
  execution_timing: string | null;
  entry_event: EventDefinition | null;
  position_sizing: PositionSizing;
  risk_rules: RiskRules;
  assumptions: string[];
  validation_plan: ValidationPlan | null;
  validation_report: ValidationReport | null;
  validation_manifest: Record<string, unknown> | null;
  trade_ledgers: ArtifactFile[];
  artifact_path: string;
  artifact_directory: string;
}

export interface ReportSummary {
  report_id: string;
  title: string;
  file_name: string;
  size_bytes: number;
  modified_at: string;
  path: string;
}

export interface ReportDetail extends ReportSummary {
  content: string;
}

export interface OverviewCounts {
  datasets: number;
  experiments: number;
  experiment_runs: number;
  findings: number;
  strategy_candidates: number;
  reports: number;
}

export interface StatusTally {
  label: string;
  count: number;
}

export interface SystemCheck {
  name: string;
  ok: boolean;
  detail: string;
}

export interface LatestResult {
  kind: string;
  identifier: string;
  title: string;
  status: string;
  detail: string | null;
  occurred_at: string | null;
  link: string;
}

export interface Overview {
  counts: OverviewCounts;
  experiments_by_conclusion: StatusTally[];
  findings_by_status: StatusTally[];
  candidates_by_display_status: StatusTally[];
  recent_experiments: ExperimentSummary[];
  latest_results: LatestResult[];
  system_checks: SystemCheck[];
  dataset_warning_total: number;
  notices: string[];
  generated_at: string;
}

export interface Health {
  status: string;
  version: string;
  repository_root: string;
  roots: Record<string, { path: string; exists: boolean }>;
}
