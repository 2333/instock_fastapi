# Rebaseline Artifact 约定

> 目的: 让 `M0 rebaseline` 可以在任意时间点中断、恢复、换人接手，而不丢失上下文

---

## 使用方式

- 每个任务默认对应一个记录文件:
  - `docs/rebaseline_artifacts/RB0-01.md`
  - `docs/rebaseline_artifacts/RB1-01.md`
  - `docs/rebaseline_artifacts/RB2-01.md`
  - ...
- 文件不存在时，由当前执行者创建。
- 若任务只做了少量工作，也要至少写明:
  - 当前结论
  - 已检查范围
  - 剩余动作
  - 阻塞点

---

## 最小模板

```md
# RBx-xx

> 更新时间: 2026-04-06 00:00 CST
> 执行者: Agent X
> 状态: in_progress / review / blocked / done

## 任务目标

一句话说明当前任务要解决什么。

## 已完成

- 已检查的文件/模块
- 已做出的判断
- 已完成的代码或文档变更

## 关键结论

- keep/remove/hold 判定
- 风险说明
- 与其他任务的依赖关系

## 剩余动作

1. 下一步最小动作
2. 若继续并行，需要谁先完成什么

## 证据

- 测试命令
- 构建结果
- 相关文件路径
- commit / diff 范围
```

---

## 更新规则

- 开始任务时: 在 tracker 里把状态改成 `in_progress`
- 暂停任务前: 更新 artifact 文件中的“关键结论”和“剩余动作”
- 完成任务后: 在 tracker 里改为 `review` 或 `done`
- 若发现新风险: 先写 artifact，再决定是否新增任务

---

## 不要把上下文只留在对话里

以下信息必须落盘，不能只停留在临时对话上下文:

- 哪些文件属于 `M0 keep`
- 哪些文件属于 `remove`
- 哪些文件暂时 `hold`
- 为什么这么判定
- 当前卡在哪一步
- 下一位接手者该从哪里开始
