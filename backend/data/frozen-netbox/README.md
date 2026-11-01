# Frozen NetBox Runtime Sample

这组文件是从 `docs/versions/v1.0.0/` 提取到工作区后的运行时样本副本，供教师演示 API 使用。

- `stage03-change-objects.jsonl` 和 `stage04-structure-objects.jsonl` 保留 v1.0 的统一变更与结构结果；
- `stage05-rule-results.jsonl` 根据本目录的 stage04 文件重新生成，避免运行时直接读取冻结文档目录；
- `stage05-manifest.json` 记录本次生成的输入、数量和证据统计。

完整上游仓库和 API 缓存不需要随运行时样本提供。
