"""artifact 读取层的领域异常。

artifacts 层不感知 HTTP；由 app.py 统一把这些异常映射为状态码。
"""

from __future__ import annotations


class ArtifactError(Exception):
    """artifact 访问失败的基类。"""


class ArtifactNotFoundError(ArtifactError):
    """请求的 artifact 不存在。"""


class ArtifactPathError(ArtifactError):
    """请求路径越出允许的 artifact 根目录。"""


class ArtifactParseError(ArtifactError):
    """artifact 存在但无法解析为预期结构。"""
