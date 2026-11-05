# Frozen NetBox Runtime Sample

这组文件是从 `docs/versions/v1.0.0/` 提取到工作区后的 v1.0 NetBox 样本副本。当前教师演示 API 不默认读取本目录；以后的验证迭代可以通过 `--stage03`、`--stage04`、`--stage05` 显式指向这里。

- `stage03-change-objects.jsonl` 和 `stage04-structure-objects.jsonl` 保留 v1.0 的统一变更与结构结果；
- `stage04-structure-objects.jsonl` 体积大，继续被 gitignore，不进入仓库，也不是当前实现或默认演示的依赖；
- `stage05-rule-results.jsonl` 曾根据本目录的 stage04 文件重新生成，避免运行时直接读取冻结文档目录；
- `stage05-manifest.json` 记录该次生成的输入、数量和证据统计。

`docs/versions/v1.0.0/` 中已经入库的冻结说明和小型产物保持原位。本目录不是那些文档的替代品，也不表示新的 NetBox 实证结论。

完整上游仓库和 API 缓存不需要随运行时样本提供。
