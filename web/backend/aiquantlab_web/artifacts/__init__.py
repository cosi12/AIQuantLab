"""artifact 发现与宽松解析。

本层不感知 HTTP，可被测试或 CLI 直接调用。为什么使用宽松解析而不是研究引擎的
严格 pydantic 模型，见 docs/WEB_ARCHITECTURE.md 第 4.3 节。
"""

from __future__ import annotations
