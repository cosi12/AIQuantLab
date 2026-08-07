"""AIQuantLab Web 后端：对 artifact 层的只读 HTTP 视图。

本 package 不写入任何文件，也不调用研究引擎的实验、回测或验证执行路径。
架构约束见 docs/WEB_ARCHITECTURE.md。
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
