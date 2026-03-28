# Windows 交互语音助手

通过语音或文本指令控制 Windows 系统的智能助手，支持应用管理、系统控制、文件操作、定时提醒、跨应用键盘自动化等功能。

## 功能特性

### 语音控制
- **唤醒词检测** — 支持配置唤醒词，唤醒后说出指令
- **语音识别** — Sherpa-onnx + SenseVoice（本地离线，无需网络），自动检测可用引擎
- **双模式输入** — 语音模式和文本模式可随时切换
- **ASR 纠错** — 自动修正语音识别错误（如"打一微信"→"打开微信"）

### 应用管理
- **打开/关闭应用** — 语音或文本指令打开/关闭任意应用
- **应用扫描** — 自动扫描本地已安装程序并注册到指令系统
- **智能匹配** — 支持中文名、英文名、别名等多种唤起方式

### 系统控制
- 音量调节
- 记事本、计算器、文件管理器等系统工具快速打开
- 支持扩展插件自定义指令

### 跨应用键盘自动化（V2 新增）
- **抖音控制** — 通过 pyautogui 模拟键盘快捷键
  - 播放/暂停（Space）、点赞（L）、评论（I）、关注（F）
  - 滚动（上滑/下滑）、全屏、静音、刷新等

### 反馈机制
- TTS 语音播报执行结果
- Windows 通知栏实时通知

## 支持的指令

| 指令示例 | 说明 |
|---------|------|
| 打开 记事本 | 打开记事本 |
| 关闭 计算器 | 关闭计算器 |
| 设置 音量 50 | 设置音量为 50% |
| 定时 5 分钟 | 设置 5 分钟定时提醒 |
| 存入文件夹 C:\test 内容 测试文本 | 保存文本到文件夹 |
| 列出应用 | 显示已注册应用列表 |
| 检查应用 VSCode | 查询应用是否已安装 |
| 抖音点赞 | 点赞/取消点赞 |
| 抖音收藏 | 收藏/取消收藏 |
| 抖音关注 | 关注/取消关注 |
| 抖音评论 | 评论 |
| 抖音全屏 | 全屏 |
| 抖音小窗 | 小窗模式 |
| 抖音暂停 | 暂停/播放 |
| 抖音快进 | 快进 |
| 抖音快退 | 快退 |
| 抖音上下滑 | 上下翻页 |
| 抖音弹幕 | 开启/关闭弹幕 |
| 抖音清屏 | 清屏 |
| 抖音自动连播 | 自动连播 |
| 抖音网页全屏 | 网页内全屏 |
| 抖音稍后再看 | 稍后再看 |
| 抖音不感兴趣 | 不感兴趣 |
| 抖音相关推荐 | 相关推荐 |
| 抖音作者主页 | 进入作者主页 |
| 抖音复制口令 | 复制分享口令 |
| 抖音音量加/减 | 音量调节 |
| 退出 | 退出程序 |

## 环境要求

- Windows 10/11
- Python 3.10+
- 麦克风（用于语音模式）

## 安装依赖

```powershell
# 基础依赖
pip install sounddevice SpeechRecognition pyyaml win10toast pyttsx3

# V2 增强依赖（推荐安装）
pip install pypinyin rapidfuzz pyautogui jieba

# V2 可选（语义匹配，需要较大模型）
pip install sentence-transformers torch

# 本地语音识别（可选，推荐）
pip install sherpa-onnx
```

### 下载语音模型（可选）

如需本地离线语音识别，需下载 sherpa-onnx 官方的 SenseVoice 模型：

1. 下载地址：https://github.com/k2-fsa/sherpa-onnx/releases
2. 寻找：`sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-*.tar.bz2`
3. 解压后得到 `model.int8.onnx` 和 `tokens.txt`
4. 将这两个文件放到 `models/sense_voice/` 目录

程序会自动检测模型是否可用：
- 有模型 → 使用 Sherpa-onnx 本地离线识别
- 无模型 → 自动切换到 Google STT（需要网络）

> **注意**：项目路径不能包含中文/非ASCII字符（如 `C:\我的项目`），否则 sherpa-onnx 无法加载模型。

## 运行

```powershell
python src/main.py
```

## 使用方式

### 语音模式（默认）
程序启动后直接进入语音模式，说出 **唤醒词 + 指令**，如：
- `你好小猪打开微信`
- `小助手关闭浏览器`

### 文本模式
输入 `0` 切换到文本模式，输入 `1` 切回语音模式

### ASR 纠错说明
语音识别可能将"打开微信"误识别为"打一微信"，纠错模块会自动修正后再解析，无需重复指令。

### 抖音控制说明
确保抖音桌面版已打开并处于前台状态，语音指令将模拟键盘快捷键操作。

## 配置文件

`config/config.yaml` 可配置以下选项：

```yaml
wake_words:
  - 小助手
  - 助手
  - 你好助手
language: zh-CN
speech_engine: sherpaonnx  # 语音引擎：sherpaonnx（本地）/ google（网络）
speech_model_path: models/sense_voice  # sherpa-onnx 模型路径
tts_engine: pyttsx3
intents_path: ../data/intents.json
intent_descriptions_path: ../data/intent_descriptions.json
plugin_path: ../plugins
log_file: ../assistant.log
app_map_path: ../config/app_map.json

# V2 配置项
nlu_engine: fuzzy_regex      # 解析引擎：fuzzy_regex / hybrid
enable_asr_correction: true  # 启用 ASR 纠错
enable_douyin_control: true # 启用抖音控制
```

## 项目结构

```
Windows-interact-assistant/
├── config/
│   ├── config.yaml        # 主配置文件
│   └── app_map.json       # 应用路径映射
├── data/
│   ├── intents.json        # 意图定义
│   └── intent_descriptions.json  # 语义匹配语料（V2）
├── models/
│   └── sense_voice/        # 语音识别模型（可选，需下载）
│       ├── model_q8.onnx
│       └── tokens.txt
├── plugins/
│   └── example_plugin.py   # 插件示例
├── src/
│   ├── main.py            # 程序入口
│   ├── config.py          # 配置加载
│   ├── executor.py        # 指令执行
│   ├── intents.py         # 意图解析（Legacy）
│   ├── nlu/               # NLU 增强模块（V2）
│   │   ├── __init__.py
│   │   ├── phonetic_corrector.py  # ASR 纠错
│   │   ├── fuzzy_regex.py         # 增强正则匹配
│   │   ├── douyin_controller.py   # 抖音键盘控制
│   │   └── hybrid_engine.py       # 混合 NLU 引擎
│   ├── plugins.py          # 插件管理
│   ├── recognize.py        # 语音识别
│   ├── feedback.py         # 反馈（TTS/通知）
│   └── logger.py           # 日志
├── README.md
└── 功能规划大纲.md
```

## 扩展插件

在 `plugins/` 目录下创建 `.py` 文件，需包含：

```python
intent_name = 'my_command'

def execute(slots):
    return '执行结果'
```

插件被加载后，通过意图名称自动触发。

## 扩展意图

编辑 `data/intents.json` 添加自定义意图模式：

```json
[
    {
        "name": "my_intent",
        "patterns": ["我的指令(.+)"],
        "slots": {"keyword": "(.+)"}
    }
]
```

## 版本历史

### v1.2
- 新增本地离线语音识别（Sherpa-onnx + SenseVoice）
- 程序启动直接进入语音模式
- 自动检测可用语音引擎
- 修复中文路径导致模型加载失败的问题（需使用英文路径）

### v1.1
- 新增 NLU 增强模块（FuzzyRegex、ASR 纠错）
- 新增抖音键盘控制功能
- 新增 HybridNLUEngine 预备（sentence-transformers）
- 修复多处代码逻辑错误

### v1.0
- 基础语音助手功能
- 应用管理、系统控制、文件操作、定时提醒
- 插件体系

## License

MIT
