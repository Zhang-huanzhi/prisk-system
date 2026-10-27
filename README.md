# Prisk-System

面向后端代码变更的最小风险分析原型。

当前版本验证一个最小闭环：读取本地 Git 仓库的 `base..head` 累积差异，识别后端代码变更位置，匹配少量接口、权限、数据事务和测试协同规则，输出 JSON 风险报告。

## 运行

在项目根目录执行：

```powershell
python main.py `
  --repo "D:\Data\Obsidian_Data\Zhz2.0\Software Engineering\EiheiZone-experience" `
  --base main `
  --head prisk-risk-demo `
  --output reports\eiheizone-demo.json
```

当前只使用 Python 标准库，不需要额外安装依赖。风险命中表示建议人工关注，不表示代码一定存在缺陷。
