"""
ASR 语音识别纠错模块
基于拼音相似度和 Levenshtein 距离修正常见的语音识别错误
例如："打一微信" -> "打开微信"
"""
import os
import re
from difflib import SequenceMatcher

try:
    from pypinyin import lazy_pinyin, Style
    PYPINYIN_AVAILABLE = True
except ImportError:
    PYPINYIN_AVAILABLE = False

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


class PhoneticCorrector:
    """基于拼音的语音识别纠错器"""

    def __init__(self, intents_path=None, app_names=None):
        """
        初始化纠错器

        Args:
            intents_path: intents.json 文件路径
            app_names: 应用名称列表（从 APP_MAP 提取）
        """
        self.commands = []  # 原始命令文本列表
        self.command_pinyin = []  # 对应拼音列表

        # 基础命令语料（常见ASR错误模式）
        self._common_asr_errors = {
            '打一': '打开',
            '打币': '打开',
            '打歪': '打开',
            '打一微': '打开微信',
            '关掉微': '关闭微信',
            '关掉一': '关闭',
            '启一': '启动',
            '启币': '启动',
            '暂停一': '暂停',
            '播放一': '播放',
        }

        # 从 intents.json 加载命令
        if intents_path and os.path.exists(intents_path):
            self._load_intents(intents_path)

        # 添加应用名称到语料
        if app_names:
            for name in app_names:
                self._add_command(name)

    def _load_intents(self, intents_path):
        """从 intents.json 加载所有 pattern 作为命令语料"""
        import json
        try:
            with open(intents_path, 'r', encoding='utf-8') as f:
                intents = json.load(f)
            for intent in intents:
                for pattern in intent.get('patterns', []):
                    # 提取 pattern 中的实际文本（去掉正则符号）
                    cmd = self._extract_text_from_pattern(pattern)
                    if cmd:
                        self._add_command(cmd)
        except Exception:
            pass

    def _extract_text_from_pattern(self, pattern):
        """从正则 pattern 中提取可读文本"""
        # 简单处理：去掉常见正则符号
        text = pattern
        text = text.replace('.*', '').replace('(.+)', '').replace('(', '').replace(')', '')
        text = text.replace('|', ' ').replace('[', '').replace(']', '')
        text = text.strip()
        return text if text else None

    def _add_command(self, cmd):
        """添加命令到语料库"""
        if not cmd or cmd in self.commands:
            return
        self.commands.append(cmd)
        self.command_pinyin.append(self._to_pinyin(cmd))

    def _to_pinyin(self, text):
        """将中文文本转换为拼音（无声调）"""
        if not PYPINYIN_AVAILABLE:
            return text.lower()
        try:
            # 提取不带声调的拼音
            pinyin = lazy_pinyin(text, style=Style.NORMAL)
            return ''.join(pinyin)
        except Exception:
            return text.lower()

    def _calc_similarity(self, s1, s2):
        """计算两个字符串的相似度"""
        if RAPIDFUZZ_AVAILABLE:
            return fuzz.ratio(s1, s2) / 100.0
        else:
            return SequenceMatcher(None, s1, s2).ratio()

    def correct(self, text):
        """
        对输入文本进行纠错

        Args:
            text: 原始识别文本

        Returns:
            纠错后的文本
        """
        if not text:
            return text

        original = text
        text = text.strip().lower()

        # 1. 检查常见ASR错误映射（快速路径）
        for error, correct in self._common_asr_errors.items():
            if error in text:
                text = text.replace(error, correct)
                if text != original.lower():
                    return text

        # 2. 尝试拼音相似度匹配
        text_pinyin = self._to_pinyin(text)

        best_match = None
        best_score = 0
        threshold = 0.75  # 相似度阈值

        for i, cmd_pinyin in enumerate(self.command_pinyin):
            # 使用快速 fuzz 过滤
            score = self._calc_similarity(text_pinyin, cmd_pinyin)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = self.commands[i]

        if best_match and best_match != text:
            return best_match

        return original

    def add_commands(self, commands):
        """动态添加命令到语料库"""
        for cmd in commands:
            self._add_command(cmd)


def build_corrector_from_app_map(app_map):
    """从 APP_MAP 构建纠错器"""
    app_names = list(app_map.keys()) if app_map else []
    corrector = PhoneticCorrector(app_names=app_names)
    return corrector
