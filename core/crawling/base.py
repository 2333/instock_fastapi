#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据爬取抽象基类

提供统一的接口和数据源抽象，便于未来切换不同数据源
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type
import time
import hashlib

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """支持的数据源"""

    EAST_MONEY = "eastmoney"
    SINA = "sina"
    SSE = "sse"
    SZSE = "szse"
    TUSHARE = "tushare"


class Market(Enum):
    """市场类型"""

    A_SHARE = "A"  # A股
    HK = "HK"  # 港股
    US = "US"  # 美股
    ETF = "ETF"
    INDEX = "INDEX"


class AdjustType(Enum):
    """复权类型"""

    NO_ADJUST = ""  # 不复权
    FORWARD = "qfq"  # 前复权
    BACKWARD = "hfq"  # 后复权


@dataclass
class CrawlConfig:
    """爬虫配置"""

    timeout: float = 30.0  # 请求超时（秒）
    max_retries: int = 3  # 最大重试次数
    min_delay: float = 0.1  # 最小请求间隔（秒）
    max_concurrent: int = 5  # 最大并发数
    proxy_url: Optional[str] = None  # 代理URL
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


@dataclass
class RateLimiter:
    """速率限制器"""

    min_delay: float = 0.1
    last_request_time: float = 0.0
    request_count: int = 0
    window_start: float = 0.0
    window_size: float = 60.0
    max_requests_per_window: int = 60

    async def acquire(self) -> None:
        """获取请求许可"""
        current_time = time.time()

        # 检查窗口
        if current_time - self.window_start >= self.window_size:
            self.window_start = current_time
            self.request_count = 0

        # 最小间隔
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)

        # 窗口限流
        if self.request_count >= self.max_requests_per_window:
            wait_time = self.window_start + self.window_size - current_time
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self.window_start = time.time()
                self.request_count = 0

        self.last_request_time = time.time()
        self.request_count += 1


@dataclass
class ProxyPool:
    """简单代理池"""

    proxies: List[str] = field(default_factory=list)
    current_index: int = 0
    fail_count: Dict[str, int] = field(default_factory=dict)
    max_failures: int = 2

    def __post_init__(self) -> None:
        normalized = []
        for proxy in self.proxies:
            item = self.normalize_proxy(proxy)
            if item and item not in normalized:
                normalized.append(item)
        self.proxies = normalized

    def get_proxy(self) -> Optional[str]:
        """获取代理"""
        if not self.proxies:
            return None
        return self.proxies[self.current_index]

    def mark_failed(self, proxy: str) -> None:
        """标记代理失败"""
        if not proxy:
            return
        self.fail_count[proxy] = self.fail_count.get(proxy, 0) + 1
        if self.fail_count[proxy] >= self.max_failures and proxy in self.proxies:
            idx = self.proxies.index(proxy)
            self.proxies.pop(idx)
            self.fail_count.pop(proxy, None)
            if self.proxies:
                self.current_index %= len(self.proxies)
            else:
                self.current_index = 0
            logger.warning("代理连续失败，已移除: %s", proxy)
            return
        self.rotate()

    def rotate(self) -> None:
        """轮换代理"""
        if self.proxies:
            self.current_index = (self.current_index + 1) % len(self.proxies)

    @staticmethod
    def normalize_proxy(proxy: str) -> Optional[str]:
        if not proxy:
            return None
        item = proxy.strip()
        if not item or item.startswith("#"):
            return None
        if item.startswith(("http://", "https://", "socks5://", "socks5h://")):
            return item
        return f"http://{item}"

    @classmethod
    def from_file(cls, file_path: str, max_failures: int = 2) -> "ProxyPool":
        proxies: List[str] = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as fp:
                for line in fp:
                    p = cls.normalize_proxy(line)
                    if p:
                        proxies.append(p)
        return cls(proxies=proxies, max_failures=max_failures)


T = TypeVar("T", bound="BaseCrawler")


class BaseCrawler(ABC):
    """数据爬取抽象基类"""

    def __init__(
        self,
        config: Optional[CrawlConfig] = None,
        rate_limiter: Optional[RateLimiter] = None,
        proxy_pool: Optional[ProxyPool] = None,
    ):
        self.config = config or CrawlConfig()
        self.rate_limiter = rate_limiter or RateLimiter(min_delay=self.config.min_delay)
        self.proxy_pool = proxy_pool
        self._client: Optional[httpx.AsyncClient] = None
        self._proxy_clients: Dict[str, httpx.AsyncClient] = {}

    @property
    @abstractmethod
    def data_source(self) -> DataSource:
        """返回数据源类型"""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """返回数据源名称"""
        pass

    async def _get_client(self, proxy_url: Optional[str] = None) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if proxy_url:
            cached = self._proxy_clients.get(proxy_url)
            if cached is not None and not cached.is_closed:
                return cached
            headers = {
                "User-Agent": self.config.user_agent,
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": self.get_referer(),
            }
            timeout = httpx.Timeout(self.config.timeout)
            client = httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
                proxy=proxy_url,
            )
            self._proxy_clients[proxy_url] = client
            return client

        if self._client is None or self._client.is_closed:
            headers = {
                "User-Agent": self.config.user_agent,
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": self.get_referer(),
            }

            timeout = httpx.Timeout(self.config.timeout)

            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
            )
        return self._client

    def get_referer(self) -> str:
        """获取Referer"""
        return "http://www.eastmoney.com/"

    async def _get_url(self, path: str) -> str:
        """构建完整URL"""
        return f"{self.get_base_url()}{path}"

    @abstractmethod
    def get_base_url(self) -> str:
        """获取基础URL"""
        pass

    @abstractmethod
    async def fetch(
        self,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """获取数据（子类实现）"""
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    )
    async def _request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
        data: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """发送HTTP请求（带重试和限流）"""
        await self.rate_limiter.acquire()

        proxy = self.proxy_pool.get_proxy() if self.proxy_pool else None
        client = await self._get_client(proxy_url=proxy)

        try:
            if method.upper() == "GET":
                response = await client.get(url, params=params, headers=headers)
            else:
                response = await client.post(url, data=data, headers=headers)

            response.raise_for_status()
            return self._parse_response(response)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误: {e.response.status_code} - {url}")
            if e.response.status_code == 429:  # Rate Limited
                await asyncio.sleep(5)
            if self.proxy_pool and proxy and e.response.status_code in {403, 429, 502, 503, 504}:
                self.proxy_pool.mark_failed(proxy)
            raise
        except httpx.RequestError as e:
            logger.error(f"请求错误: {e}")
            if self.proxy_pool and proxy:
                self.proxy_pool.mark_failed(proxy)
            raise

    def _parse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """解析响应"""
        try:
            return response.json()
        except Exception:
            return {"text": response.text, "status_code": response.status_code}

    async def fetch_all(
        self,
        urls: List[str],
        params_list: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """并发获取多个URL"""
        if params_list is None:
            params_list = [None] * len(urls)

        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def fetch_one(url: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
            async with semaphore:
                return await self._request(url, params)

        tasks = [fetch_one(url, params) for url, params in zip(urls, params_list)]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def cache_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()

    async def close(self) -> None:
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        for key, client in list(self._proxy_clients.items()):
            if not client.is_closed:
                await client.aclose()
            self._proxy_clients.pop(key, None)

    async def __aenter__(self) -> "BaseCrawler":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


class DataProvider(Generic[T]):
    """数据提供者工厂"""

    _providers: Dict[DataSource, Type[T]] = {}

    @classmethod
    def register(cls, source: DataSource) -> callable:
        """注册数据提供者"""

        def decorator(provider_class: Type[T]) -> Type[T]:
            cls._providers[source] = provider_class
            return provider_class

        return decorator

    @classmethod
    def get_provider(cls, source: DataSource) -> Optional[Type[T]]:
        """获取数据提供者类"""
        return cls._providers.get(source)

    @classmethod
    def create(cls, source: DataSource, **kwargs) -> Optional[T]:
        """创建数据提供者实例"""
        provider_class = cls.get_provider(source)
        if provider_class:
            return provider_class(**kwargs)
        return None


# 便捷函数
async def create_crawler(
    source: DataSource = DataSource.EAST_MONEY,
    **kwargs,
) -> Optional[BaseCrawler]:
    """创建爬虫实例"""
    return DataProvider.create(source, **kwargs)
