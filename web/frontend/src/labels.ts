/**
 * 英文 artifact 词汇 → 中文标签映射，以及展示用格式化函数。
 *
 * 语调规则：只有真正通过验证的状态才使用 positive 语调；正的收益数值一律用中性
 * 表述（"均值收益""累计收益"），不使用"盈利""收益机会"这类暗示可交易性的措辞。
 */

export type Tone = "positive" | "negative" | "caution" | "neutral" | "unknown";

export interface LabelSpec {
  text: string;
  tone: Tone;
  hint?: string;
}

const UNKNOWN: LabelSpec = { text: "未记录", tone: "unknown" };

function lookup(table: Record<string, LabelSpec>, value: string | null | undefined): LabelSpec {
  if (value === null || value === undefined || value === "") {
    return UNKNOWN;
  }
  return table[value] ?? { text: value, tone: "unknown", hint: "artifact 中的未知状态值" };
}

const EXPERIMENT_CONCLUSIONS: Record<string, LabelSpec> = {
  not_reviewed: { text: "未评审", tone: "neutral", hint: "已有运行结果，但尚无人工结论" },
  supported: { text: "假设被支持", tone: "positive", hint: "人工判定证据支持预声明方向" },
  not_supported: {
    text: "假设未被支持",
    tone: "negative",
    hint: "人工判定证据不支持预声明方向",
  },
  inconclusive: { text: "结论不确定", tone: "caution", hint: "证据不足以判定任一方向" },
  invalid: { text: "实验无效", tone: "negative", hint: "实验本身存在缺陷" },
};

const RUN_STATUSES: Record<string, LabelSpec> = {
  running: { text: "运行中", tone: "caution" },
  completed: { text: "已完成", tone: "positive" },
  failed: { text: "已失败", tone: "negative" },
};

const FINDING_STATUSES: Record<string, LabelSpec> = {
  accepted_for_research: {
    text: "已接受用于后续研究",
    tone: "positive",
    hint: "可作为策略研究的证据来源",
  },
  rejected: {
    text: "已拒绝",
    tone: "negative",
    hint: "证据不支持该 claim；记录被永久保留",
  },
};

const CANDIDATE_DISPLAY_STATUSES: Record<string, LabelSpec> = {
  PIPELINE_PROBE: {
    text: "流程探针",
    tone: "caution",
    hint: "仅用于验证流水线链路，在契约上不可能取得 qualification",
  },
  REJECTED: { text: "已拒绝", tone: "negative", hint: "来源研究发现已被拒绝" },
  PENDING_REVIEW: { text: "待验证", tone: "neutral", hint: "尚无可用的验证结论" },
  SUPPORTED: { text: "验证支持", tone: "positive", hint: "全部预声明验证标准均通过" },
  NOT_SUPPORTED: { text: "验证未支持", tone: "negative", hint: "至少一个验证标准未通过" },
};

const CANDIDATE_PURPOSES: Record<string, LabelSpec> = {
  qualification: { text: "资格验证", tone: "neutral", hint: "来源 finding 已通过研究门槛" },
  pipeline_probe: {
    text: "流程探针",
    tone: "caution",
    hint: "来源 finding 未通过研究门槛，结果不得解释为策略结论",
  },
};

const VALIDATION_ASSESSMENTS: Record<string, LabelSpec> = {
  supported: { text: "验证支持", tone: "positive" },
  not_supported: { text: "验证未支持", tone: "negative" },
  inconclusive: { text: "结论不确定", tone: "caution" },
};

const SPLIT_ROLES: Record<string, LabelSpec> = {
  research: { text: "研究期", tone: "neutral", hint: "用于形成假设的样本" },
  validation: { text: "验证期", tone: "neutral", hint: "独立样本，用于检验规则" },
  final_test: {
    text: "最终测试期",
    tone: "neutral",
    hint: "只使用一次；结果不得用于修改同一候选修订",
  },
};

const EXPECTED_DIRECTIONS: Record<string, LabelSpec> = {
  positive: { text: "正向", tone: "neutral" },
  negative: { text: "负向", tone: "neutral" },
  two_sided: { text: "双侧", tone: "neutral" },
};

const DATASET_KINDS: Record<string, LabelSpec> = {
  ohlcv: { text: "OHLCV 数据集", tone: "neutral" },
  feature: { text: "特征数据集", tone: "neutral", hint: "由 OHLCV 数据集物化而来" },
};

const SEVERITIES: Record<string, LabelSpec> = {
  error: { text: "错误", tone: "negative" },
  warning: { text: "警告", tone: "caution" },
  info: { text: "提示", tone: "neutral" },
};

export const conclusionLabel = (value: string | null | undefined): LabelSpec =>
  lookup(EXPERIMENT_CONCLUSIONS, value);
export const runStatusLabel = (value: string | null | undefined): LabelSpec =>
  lookup(RUN_STATUSES, value);
export const findingStatusLabel = (value: string | null | undefined): LabelSpec =>
  lookup(FINDING_STATUSES, value);
export const candidateStatusLabel = (value: string | null | undefined): LabelSpec =>
  lookup(CANDIDATE_DISPLAY_STATUSES, value);
export const purposeLabel = (value: string | null | undefined): LabelSpec =>
  lookup(CANDIDATE_PURPOSES, value);
export const assessmentLabel = (value: string | null | undefined): LabelSpec =>
  lookup(VALIDATION_ASSESSMENTS, value);
export const splitRoleLabel = (value: string | null | undefined): LabelSpec =>
  lookup(SPLIT_ROLES, value);
export const directionLabel = (value: string | null | undefined): LabelSpec =>
  lookup(EXPECTED_DIRECTIONS, value);
export const datasetKindLabel = (value: string | null | undefined): LabelSpec =>
  lookup(DATASET_KINDS, value);
export const severityLabel = (value: string | null | undefined): LabelSpec =>
  lookup(SEVERITIES, value);

const SIMPLE_TERMS: Record<string, string> = {
  // 事件条件运算符
  gt: "大于",
  ge: "大于或等于",
  lt: "小于",
  le: "小于或等于",
  eq: "等于",
  ne: "不等于",
  all: "全部满足",
  any: "任一满足",
  // 事件研究设定
  simple: "简单收益率",
  log: "对数收益率",
  allow: "允许重叠",
  non_overlapping: "不重叠采样",
  iid: "IID bootstrap",
  moving_block: "Moving-block bootstrap",
  // 数据语义
  open: "K 线开盘时刻",
  close: "K 线收盘时刻",
  bid: "买价（bid）",
  ask: "卖价（ask）",
  mid: "中间价（midpoint）",
  last: "最新成交价",
  unknown: "未知",
  tick: "报价跳动次数",
  real: "实际成交量",
  continuous: "连续（7×24）",
  weekdays: "工作日",
  observed_gaps: "保留观测缺口",
  // 策略语义
  long: "做多",
  short: "做空",
  next_bar_open: "下一根 K 线开盘成交",
  fixed_fraction_notional: "固定名义比例",
  // 数据集与 artifact 分类
  ohlcv: "OHLCV 数据集",
  feature: "特征数据集",
  experiment: "实验",
  finding: "研究发现",
  candidate: "策略候选",
  // 系统检查项
  processed_data: "处理后数据目录",
  experiments: "实验目录",
  reports: "报告目录",
  write_access: "写入权限",
};

/** 把单个英文技术词转为中文；未收录的词原样返回。 */
export function term(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "未记录";
  }
  return SIMPLE_TERMS[value] ?? value;
}

const VALIDATION_FAILURES: Record<string, string> = {
  non_positive_primary_mean_return: "主执行模型的单笔均值收益非正",
  non_positive_stress_mean_return: "压力执行模型的单笔均值收益非正",
  primary_drawdown_limit_exceeded: "主执行模型的最大回撤超过预声明上限",
  stress_drawdown_limit_exceeded: "压力执行模型的最大回撤超过预声明上限",
  insufficient_trades: "交易样本数低于预声明最小值",
};

export function failureLabel(value: string): string {
  return VALIDATION_FAILURES[value] ?? value;
}

const QUALITY_CODES: Record<string, string> = {
  missing_candle: "缺失 K 线",
  duplicate_timestamp: "重复时间戳",
  unsorted_timestamp: "时间戳未排序",
  invalid_ohlc: "OHLC 关系非法",
  negative_volume: "负成交量",
  non_positive_price: "非正价格",
};

export function qualityCodeLabel(value: string): string {
  return QUALITY_CODES[value] ?? value;
}

// --------------------------------------------------------------------------
// 格式化
// --------------------------------------------------------------------------

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  timeZone: "UTC",
  hour12: false,
});

const DATE_FORMATTER = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  timeZone: "UTC",
});

/** 全部时间按 UTC 展示，与 artifact 的规范时区一致。 */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "未记录";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return `${DATE_TIME_FORMATTER.format(parsed)} UTC`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "未记录";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return DATE_FORMATTER.format(parsed);
}

export function formatInteger(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "未记录";
  }
  return value.toLocaleString("zh-CN");
}

export function formatNumber(value: number | null | undefined, digits = 6): string {
  if (value === null || value === undefined) {
    return "未记录";
  }
  return value.toFixed(digits);
}

/** 比例值转百分比字符串；保留符号以便与置信区间对照。 */
export function formatPercent(value: number | null | undefined, digits = 4): string {
  if (value === null || value === undefined) {
    return "未记录";
  }
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatInterval(
  interval: [number, number] | null | undefined,
  digits = 5,
): string {
  if (!interval) {
    return "未记录";
  }
  return `[${(interval[0] * 100).toFixed(digits)}%, ${(interval[1] * 100).toFixed(digits)}%]`;
}

export function formatBytes(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "未记录";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  const units = ["KB", "MB", "GB"];
  let size = value / 1024;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(1)} ${units[index]}`;
}

export function shortHash(value: string | null | undefined, length = 12): string {
  if (!value) {
    return "未记录";
  }
  return value.length <= length ? value : `${value.slice(0, length)}…`;
}

export function formatBoolean(
  value: boolean | null | undefined,
  trueText = "是",
  falseText = "否",
): string {
  if (value === null || value === undefined) {
    return "未记录";
  }
  return value ? trueText : falseText;
}
