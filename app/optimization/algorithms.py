import asyncio
import random
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, RBF, ConstantKernel
from scipy.stats import norm

logger = logging.getLogger(__name__)


@dataclass
class Trial:
    """优化试验记录"""
    parameters: Dict[str, Any]
    score: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None
    backtest_result_id: Optional[int] = None
    status: str = "running"
    error: Optional[str] = None


class BaseOptimizer(ABC):
    """优化器基类"""

    def __init__(self, param_space: Dict[str, Dict[str, Any]], objective: str = "sharpe_ratio"):
        self.param_space = param_space
        self.objective = objective
        self.trials: List[Trial] = []
        self.best_trial: Optional[Trial] = None

    @abstractmethod
    async def suggest(self, n: int = 1) -> List[Dict[str, Any]]:
        """生成下一组参数建议"""
        pass

    def record_trial(self, parameters: Dict[str, Any], score: Optional[float], **kwargs):
        """记录试验结果"""
        trial = Trial(parameters=parameters, score=score, **kwargs)
        self.trials.append(trial)

        if score is not None and (self.best_trial is None or score > self.best_trial.score):
            self.best_trial = trial

    @abstractmethod
    def is_done(self) -> bool:
        """检查是否达到终止条件"""
        pass

    def get_best_parameters(self) -> Optional[Dict[str, Any]]:
        """获取最优参数"""
        return self.best_trial.parameters if self.best_trial else None

    def get_best_score(self) -> Optional[float]:
        """获取最优得分"""
        return self.best_trial.score if self.best_trial else None


class RandomSearchOptimizer(BaseOptimizer):
    """随机搜索优化器"""

    def __init__(self, param_space: Dict[str, Dict[str, Any]], objective: str = "sharpe_ratio", n_trials: int = 100):
        super().__init__(param_space, objective)
        self.n_trials = n_trials
        self.tried: List[Tuple] = []

    def _sample_parameters(self) -> Dict[str, Any]:
        """从参数空间随机采样"""
        params = {}
        for name, spec in self.param_space.items():
            ptype = spec["type"]
            low = spec["low"]
            high = spec["high"]

            if ptype == "int":
                params[name] = random.randint(int(low), int(high))
            elif ptype == "float":
                step = spec.get("step")
                if step:
                    steps = int((high - low) / step) + 1
                    params[name] = low + random.randint(0, steps - 1) * step
                else:
                    params[name] = random.uniform(low, high)
            else:
                raise ValueError(f"Unknown param type: {ptype}")

        return params

    async def suggest(self, n: int = 1) -> List[Dict[str, Any]]:
        """生成随机参数（不重复）"""
        suggestions = []
        for _ in range(n):
            for attempt in range(100):  # 尝试避免重复
                params = self._sample_parameters()
                key = tuple(sorted(params.items()))
                if key not in self.tried:
                    self.tried.append(key)
                    suggestions.append(params)
                    break
            else:
                # 实在无法不重复时，接受重复
                suggestions.append(self._sample_parameters())

        return suggestions

    def is_done(self) -> bool:
        return len(self.trials) >= self.n_trials


class BayesianOptimizer(BaseOptimizer):
    """贝叶斯优化器（高斯过程 + EI）"""

    def __init__(
        self,
        param_space: Dict[str, Dict[str, Any]],
        objective: str = "sharpe_ratio",
        n_initial: int = 5,
        kernel=None,
    ):
        super().__init__(param_space, objective)
        self.n_initial = n_initial
        self.X: List[List[float]] = []  # 参数向量（归一化后）
        self.y: List[float] = []  # 得分
        self.param_names = list(param_space.keys())
        self.bounds = np.array([[spec["low"], spec["high"]] for spec in param_space.values()])

        # GP 内核：Matern 适合超参数优化
        if kernel is None:
            kernel = Matern(length_scale=1.0, length_scale_bounds=(1e-2, 1e3), nu=2.5)
        self.gp = GaussianProcessRegressor(kernel=kernel, alpha=1e-6, normalize_y=True, n_restarts_optimizer=5)

    def _normalize(self, params: Dict[str, Any]) -> List[float]:
        """将参数归一化到 [0,1]"""
        vec = []
        for i, name in enumerate(self.param_names):
            low, high = self.bounds[i]
            val = params[name]
            normalized = (val - low) / (high - low) if high > low else 0.5
            vec.append(normalized)
        return vec

    def _denormalize(self, vec: List[float]) -> Dict[str, Any]:
        """从归一化向量还原参数"""
        params = {}
        for i, name in enumerate(self.param_names):
            low, high = self.bounds[i]
            # 反归一化并取整（如果原类型是 int）
            spec = self.param_space[name]
            ptype = spec["type"]
            raw = low + vec[i] * (high - low)

            if ptype == "int":
                params[name] = int(round(raw))
            else:
                step = spec.get("step")
                if step:
                    params[name] = round(raw / step) * step
                else:
                    params[name] = float(raw)

        return params

    async def suggest(self, n: int = 1) -> List[Dict[str, Any]]:
        """使用 EI 采集函数建议下一组参数"""
        if len(self.X) < self.n_initial:
            # 初始阶段：拉丁超立方采样（简化：随机）
            suggestions = []
            for _ in range(n):
                params = {}
                for name, spec in self.param_space.items():
                    low, high = spec["low"], spec["high"]
                    if spec["type"] == "int":
                        params[name] = random.randint(int(low), int(high))
                    else:
                        params[name] = random.uniform(low, high)
                suggestions.append(params)
            return suggestions

        # 拟合 GP
        X_array = np.array(self.X)
        y_array = np.array(self.y)
        self.gp.fit(X_array, y_array)

        # 期望改进（Expected Improvement）
        def expected_improvement(x: np.ndarray) -> float:
            x = x.reshape(1, -1)
            mu, sigma = self.gp.predict(x, return_std=True)
            mu = mu[0]
            sigma = sigma[0]

            if sigma == 0:
                return 0.0

            y_best = max(self.y)
            z = (mu - y_best) / sigma
            ei = (mu - y_best) * norm.cdf(z) + sigma * norm.pdf(z)
            return float(ei)

        # 多起点优化 EI
        best_ei = -1
        best_vec = None
        for _ in range(100):
            x0 = np.random.uniform(0, 1, len(self.param_names))
            # 简化：直接评估随机点，不使用梯度优化
            ei = expected_improvement(x0)
            if ei > best_ei:
                best_ei = ei
                best_vec = x0

        if best_vec is None:
            # 回退到随机
            return [self._denormalize(np.random.uniform(0, 1, len(self.param_names)).tolist()) for _ in range(n)]

        return [self._denormalize(best_vec.tolist())]

    def record_trial(self, parameters: Dict[str, Any], score: Optional[float], **kwargs):
        """记录试验并更新 GP"""
        super().record_trial(parameters, score, **kwargs)
        self.X.append(self._normalize(parameters))
        if score is not None:
            self.y.append(score)
        else:
            # 失败 trial 不加入 GP 训练
            self.X.pop()

    def is_done(self) -> bool:
        return len(self.trials) >= self.n_initial + 100  # 初始 + 100 轮优化


def create_optimizer(method: str, param_space: Dict[str, Dict[str, Any]], **kwargs) -> BaseOptimizer:
    """工厂函数：创建优化器"""
    if method == "random":
        return RandomSearchOptimizer(param_space, **kwargs)
    elif method == "bayesian":
        return BayesianOptimizer(param_space, **kwargs)
    else:
        raise ValueError(f"Unknown optimization method: {method}")
