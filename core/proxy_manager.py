#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import random
from pathlib import Path
from typing import Dict, List, Optional

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"
PROXY_FILE = CONFIG_DIR / "proxy.txt"
API_CONFIG_FILE = CONFIG_DIR / "api_config.json"


class ProxyManager:
    _instance: Optional["ProxyManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.api_config = self._load_api_config()
        self.test_url = "http://myip.ipip.net"
        self.pool_size = 20
        self.min_size = 10
        self.data: List[str] = []
        self._init_pool()

    def _load_api_config(self) -> Optional[Dict]:
        try:
            if API_CONFIG_FILE.exists():
                with open(API_CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.error(f"API配置文件不存在: {API_CONFIG_FILE}")
                return None
        except Exception as e:
            logger.error(f"加载API配置文件失败: {e}")
            return None

    def _build_api_url(self, count: int) -> Optional[str]:
        if not self.api_config or "proxy_api" not in self.api_config:
            logger.error("API配置不存在或格式错误")
            return None

        proxy_api = self.api_config["proxy_api"]
        base_url = proxy_api.get("url_base")
        params = proxy_api.get("params", {})

        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_str}&count={count}"

    def _init_pool(self):
        proxies = self.load_proxies()
        self.data = self.test_proxies(proxies) if proxies else []
        self.save_proxies(self.data)
        self.ensure_pool()

    def fetch_and_save_proxies(self, count: int, append: bool = False):
        api_url = self._build_api_url(count)
        if not api_url:
            logger.error("无法构建API URL，请检查配置文件")
            return

        try:
            resp = requests.get(api_url, timeout=10)
            if resp.status_code == 200:
                proxies = resp.text.strip().split()
                if append:
                    current = set(self.load_proxies())
                    proxies = [p for p in proxies if p not in current]
                    all_proxies = list(current) + proxies
                    self.save_proxies(all_proxies)
                else:
                    self.save_proxies(proxies)
            else:
                logger.error(f"代理API响应异常: {resp.status_code}")
        except Exception as e:
            logger.error(f"获取代理失败: {e}")

    def load_proxies(self) -> List[str]:
        if not PROXY_FILE.exists():
            return []
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    def save_proxies(self, proxies: List[str]):
        PROXY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROXY_FILE, "w", encoding="utf-8") as f:
            for proxy in proxies:
                f.write(proxy + "\n")

    def test_proxies(self, proxies: List[str]) -> List[str]:
        valid = []

        def test_one(proxy_str: str):
            try:
                user_pass, host_port = proxy_str.split("@")
                user, password = user_pass.split(":")
                ip, port = host_port.split(":")
                proxy = {
                    "http": f"http://{user}:{password}@{ip}:{port}",
                    "https": f"http://{user}:{password}@{ip}:{port}",
                }
                resp = requests.get(self.test_url, proxies=proxy, timeout=5)
                if resp.status_code == 200:
                    return proxy_str
                else:
                    logger.info(f"代理不可用: {proxy_str} 响应码: {resp.status_code}")
            except Exception as e:
                logger.debug(f"代理不可用: {proxy_str} 错误: {e}")
            return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_proxy = {executor.submit(test_one, p): p for p in proxies}
            for future in as_completed(future_to_proxy):
                result = future.result()
                if result:
                    valid.append(result)

        if not valid and proxies:
            logger.warning("代理测试全部失败，保留原始代理")
            return proxies

        return valid

    def ensure_pool(self):
        if not self.data or len(self.data) < self.min_size:
            need_count = self.pool_size - len(self.data) if self.data else self.pool_size
            logger.info(f"代理池数量不足{self.min_size}，补充{need_count}条代理")
            self.fetch_and_save_proxies(need_count, append=True)
            self.data = self.test_proxies(self.load_proxies())
            self.save_proxies(self.data)
            if not self.data:
                logger.warning("代理池为空，将在运行时测试代理")

    def refresh_pool(self):
        """强制刷新代理池"""
        logger.info("强制刷新代理池")
        self.fetch_and_save_proxies(self.pool_size, append=False)
        self.data = self.test_proxies(self.load_proxies())
        self.save_proxies(self.data)
        logger.info(f"刷新后可用代理: {len(self.data)}")

    def get_proxy(self) -> Optional[Dict[str, str]]:
        self.ensure_pool()
        if not self.data:
            return None
        proxy_str = random.choice(self.data)
        try:
            user_pass, host_port = proxy_str.split("@")
            user, password = user_pass.split(":")
            ip, port = host_port.split(":")
            return {
                "http": f"http://{user}:{password}@{ip}:{port}",
                "https": f"http://{user}:{password}@{ip}:{port}",
            }
        except Exception as e:
            logger.error(f"解析代理失败: {e}")
            return None

    def report_bad_proxy(self, proxy: str):
        if isinstance(proxy, dict):
            try:
                proxy_str = proxy["http"].replace("http://", "")
            except Exception:
                logger.warning(f"report_bad_proxy参数异常: {proxy}")
                return
        else:
            proxy_str = proxy

        if proxy_str in self.data:
            self.data.remove(proxy_str)
            logger.info(f"移除异常代理: {proxy_str}")
            self.save_proxies(self.data)
            if len(self.data) < self.min_size:
                self.ensure_pool()


proxy_manager = ProxyManager()


def get_proxy_manager() -> ProxyManager:
    return proxy_manager
