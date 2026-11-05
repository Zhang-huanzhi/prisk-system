# Prisk 本地演示数据

这些 JSONL 文件是脱敏、可提交仓库的最小开发数据，用于 domain/service 测试和当前的默认演示启动。

教师演示 API 和评分 CLI 默认读取本目录。`backend/data/frozen-netbox/` 不是启动依赖；以后的验证迭代可以把它作为显式 `--stage03`、`--stage04`、`--stage05` 输入。使用 `dataset_cli`、`structure_cli`、`rules_cli` 或 `scoring_cli` 时，通过命令行参数显式传入其他输入和输出路径。
