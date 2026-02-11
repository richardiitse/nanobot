"""智谱联网搜索工具.

使用智谱官方 Web Search API: https://open.bigmodel.cn/api/paas/v4/web_search
"""

import os
from typing import Any

import httpx

from nanobot.agent.tools.base import Tool


class ZhipuWebSearchTool(Tool):
    """使用智谱 Web Search API 进行网络搜索."""

    name = "web_search"
    description = "搜索网络信息，返回网页标题、URL、摘要等。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询字符串（建议不超过70字符）"
            },
            "count": {
                "type": "integer",
                "description": "最大结果数 (1-50)",
                "minimum": 1,
                "maximum": 50,
                "default": 10
            }
        },
        "required": ["query"]
    }

    # 搜索引擎选项
    SEARCH_ENGINES = {
        "search_std": "标准搜索",
        "search_pro": "增强搜索",
        "search_pro_sogou": "搜狗搜索",
        "search_pro_quark": "夸克搜索",
    }

    # 时间过滤选项
    RECENCY_FILTERS = {
        "oneDay": "一天内",
        "oneWeek": "一周内",
        "oneMonth": "一个月内",
        "oneYear": "一年内",
        "noLimit": "不限",
    }

    def __init__(
        self,
        api_key: str | None = None,
        search_engine: str = "search_std",
        recency_filter: str = "noLimit",
        content_size: str = "medium"
    ):
        """初始化智谱搜索工具.

        Args:
            api_key: 智谱 API Key
            search_engine: 搜索引擎类型 (search_std, search_pro, search_pro_sogou, search_pro_quark)
            recency_filter: 时间过滤 (oneDay, oneWeek, oneMonth, oneYear, noLimit)
            content_size: 内容大小 (medium, high)
        """
        self.api_key = api_key or os.environ.get("ZHIPU_API_KEY", "")
        self.search_engine = search_engine
        self.recency_filter = recency_filter
        self.content_size = content_size
        self.api_base = "https://open.bigmodel.cn/api/paas/v4/web_search"

    async def execute(self, query: str, count: int = 10, **kwargs: Any) -> str:
        """执行网络搜索.

        Args:
            query: 搜索查询字符串
            count: 返回结果数量 (1-50)

        Returns:
            格式化的搜索结果字符串
        """
        if not self.api_key:
            return "错误: 未配置 ZHIPU_API_KEY"

        # 限制查询长度
        query = query[:70]
        n = min(max(count, 1), 50)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_base,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "search_query": query,
                        "search_engine": self.search_engine,
                        "search_intent": False,
                        "count": n,
                        "search_recency_filter": self.recency_filter,
                        "content_size": self.content_size
                    }
                )
                response.raise_for_status()

            data = response.json()

            # 解析搜索结果
            if "search_result" in data and data["search_result"]:
                return self._format_results(data["search_result"], query)

            return f"未找到结果: {query}"

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                return "错误: API Key 无效或已过期"
            elif status == 429:
                return "错误: 请求过于频繁，请稍后重试"
            else:
                return f"HTTP 错误 ({status}): {e.response.text[:200]}"
        except httpx.TimeoutException:
            return "错误: 请求超时，请稍后重试"
        except Exception as e:
            return f"错误: {str(e)}"

    def _format_results(self, results: list, query: str) -> str:
        """格式化搜索结果.

        Args:
            results: 搜索结果列表
            query: 搜索查询字符串

        Returns:
            格式化的结果字符串
        """
        lines = [f"搜索结果: {query}\n"]
        lines.append("=" * 60)

        for i, r in enumerate(results, 1):
            title = r.get("title", "无标题")
            link = r.get("link", "")
            content = r.get("content", "")
            media = r.get("media", "")
            icon = r.get("icon", "")

            lines.append(f"\n{i}. {title}")

            if media:
                lines.append(f"   来源: {media}")
            if link:
                lines.append(f"   链接: {link}")
            if content:
                # 截取摘要，避免过长
                snippet = content[:200] + "..." if len(content) > 200 else content
                lines.append(f"   摘要: {snippet}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
