# Windows 交互语音助手

## 目录结构

- `config/` 配置文件。
- `data/` 意图定义数据。
- `plugins/` 扩展插件。
- `src/` 程序代码。

## 运行

1. 安装依赖：

```powershell
pip install pyyaml pyttsx3 SpeechRecognition win10toast
```

2. 运行：

```powershell
python -m src.main
```

3. 输入示例：
 - 打开 记事本
 - 关闭 计算器
 - 设置 音量 50
 - 定时 1 分钟
 - 存入文件夹 C:\\Users\\Public 内容 测试文本
 - 保存到文件 test_folder 测试文本
 - 列出应用
 - 检查应用 VSCode
 - 退出

## 扩展

- 编辑 `data/intents.json` 增加意图。
- 插件放 `plugins/`，需要包含 `intent_name` 和 `execute(slots)`。