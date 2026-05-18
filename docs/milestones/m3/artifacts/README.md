# Pre-M3 Artifacts

每个 wave 都必须留下可恢复的 artifact。最低要求如下：

- `Status`
- `Owner`
- `Depends`
- `Changed files`
- `Commands run`
- `Results`
- `Open risks`
- `Next step`
- `Blocked by`
- `Last updated`

## 恢复原则

- 不从聊天记录恢复，优先从 artifact 恢复
- 不从零重新分析，先读取 tracker 指向的当前 wave artifact
- 如果 artifact 与代码事实冲突，以最新代码 + 当前 wave 结论为准，并立刻回写 artifact

## 当前 wave 文件

- [W0-scope-freeze.md](./W0-scope-freeze.md)
- [W1-release-correctness.md](./W1-release-correctness.md)
- [W2-runtime-schema-alignment.md](./W2-runtime-schema-alignment.md)
- [W2b-data-completeness-alignment.md](./W2b-data-completeness-alignment.md)
- [W3-residue-cleanup.md](./W3-residue-cleanup.md)
- [W4-doc-mainline-alignment.md](./W4-doc-mainline-alignment.md)
