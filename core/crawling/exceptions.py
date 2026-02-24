#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义异常模块
"""

from typing import Optional


class DataFetchError(Exception):
    """数据获取错误"""

    def __init__(self, message: str, source: Optional[str] = None, code: Optional[str] = None):
        self.message = message
        self.source = source
        self.code = code
        super().__init__(self.message)


class DataParseError(Exception):
    """数据解析错误"""

    def __init__(self, message: str, raw_data: Optional[str] = None):
        self.message = message
        self.raw_data = raw_data
        super().__init__(self.message)


class RateLimitError(Exception):
    """请求频率限制错误"""

    def __init__(self, message: str = "请求过于频繁，请稍后重试"):
        self.message = message
        super().__init__(self.message)


class ProxyError(Exception):
    """代理错误"""

    def __init__(self, message: str, proxy: Optional[str] = None):
        self.message = message
        self.proxy = proxy
        super().__init__(self.message)


class AuthenticationError(Exception):
    """认证错误"""

    def __init__(self, message: str = "认证失败，请检查API密钥"):
        self.message = message
        super().__init__(self.message)


class DataNotFoundError(Exception):
    """数据不存在"""

    def __init__(self, message: str = "请求的数据不存在"):
        self.message = message
        super().__init__(self.message)


class DatabaseError(Exception):
    """数据库错误"""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class BacktestError(Exception):
    """回测错误"""

    def __init__(self, message: str, strategy_id: Optional[str] = None):
        self.message = message
        self.strategy_id = strategy_id
        super().__init__(self.message)


class PatternRecognitionError(Exception):
    """形态识别错误"""

    def __init__(self, message: str, pattern_type: Optional[str] = None):
        self.message = message
        self.pattern_type = pattern_type
        super().__init__(self.message)
