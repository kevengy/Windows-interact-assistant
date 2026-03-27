"""
增强的正则意图匹配器
在原有 IntentParser 基础上增加模糊匹配能力
"""
import re
import os
import json
from difflib import SequenceMatcher


class FuzzyRegexMatcher:
    """支持模糊匹配的意图解析器"""

    def __init__(self, intents_path=None):
        """
        初始化模糊匹配器

        Args:
            intents_path: intents.json 文件路径
        """
        self.intents_path = intents_path
        self.intents = []
        if intents_path and os.path.exists(intents_path):
            self._load_intents(intents_path)

        # 硬编码的回退规则（从原 IntentParser 迁移）
        self._fallback_rules = [
            {
                'keywords': ['打开', '启动'],
                'intent': 'open_app',
                'slot_name': 'app_name',
                'slot_pattern': r'.*(?:打开|启动)\s*(.*)'
            },
            {
                'keywords': ['关闭', '退出'],
                'intent': 'close_app',
                'slot_name': 'app_name',
                'slot_pattern': r'.*(?:关闭|退出)\s*(.*)'
            },
            {
                'keywords': ['设置', '音量'],
                'intent': 'set_volume',
                'slot_name': 'value',
                'slot_pattern': r'音量\s?(\d+)'
            },
            {
                'keywords': ['定时', '闹钟'],
                'intent': 'set_timer',
                'slot_name': 'minutes',
                'slot_pattern': r'(\d+)\s*分钟'
            },
            {
                'keywords': ['列出应用', '显示应用', '应用列表'],
                'intent': 'list_apps',
                'slot_name': None,
                'slot_pattern': None
            },
            {
                'keywords': ['检查应用', '查询应用', '是否安装'],
                'intent': 'check_app',
                'slot_name': 'app_name',
                'slot_pattern': r'(?:检查应用|查询应用|是否安装)\s*(.*)'
            },
            {
                'keywords': ['存入文件夹', '保存到文件夹', '存入文件'],
                'intent': 'save_to_folder',
                'slot_name': None,
                'slot_pattern': None
            },
            # 抖音控制回退规则（无前缀）
            {
                'keywords': [
                    '继续播放', '继续', '下一个', '上一个',
                    '点赞', '收藏', '关注', '取消关注', '评论', '分享',
                    '暂停', '播放', '全屏', '网页全屏', '小窗', '自动连播',
                    '清屏', '弹幕', '不感兴趣', '相关推荐', '作者主页', '复制口令',
                    '上滑', '下滑', '快进', '快退', '音量加', '音量减', '稍后再看',
                    '静音', '刷新', '首页'
                ],
                'intent': 'douyin_control',
                'slot_name': 'action',
                'slot_pattern': None
            },
        ]

    def _load_intents(self, intents_path):
        """从 JSON 文件加载意图定义"""
        try:
            with open(intents_path, 'r', encoding='utf-8') as f:
                self.intents = json.load(f)
        except Exception:
            self.intents = []

    def match(self, text):
        """
        尝试匹配意图

        Args:
            text: 输入文本

        Returns:
            (intent_name, slots_dict) 或 ('unknown', {})
        """
        text = text.strip().lower()

        # 1. 尝试 JSON 中的正则 patterns
        for intent in self.intents:
            for pattern in intent.get('patterns', []):
                if re.search(pattern, text):
                    slots = {}
                    for slot_name, regex in intent.get('slots', {}).items():
                        m = re.search(regex, text)
                        if m:
                            slots[slot_name] = m.group(1)
                    return intent['name'], slots

        # 2. 尝试硬编码回退规则
        # 预先收集抖音动作关键词（用于冲突检测）
        douyin_keywords = [
            '继续播放', '继续', '下一个', '上一个',
            '点赞', '收藏', '关注', '取消关注', '评论', '分享',
            '暂停', '播放', '全屏', '网页全屏', '小窗', '自动连播',
            '清屏', '弹幕', '不感兴趣', '相关推荐', '作者主页', '复制口令',
            '上滑', '下滑', '快进', '快退', '音量加', '音量减', '稍后再看',
            '静音', '刷新', '首页'
        ]
        has_douyin_action = any(kw in text for kw in douyin_keywords)

        for rule in self._fallback_rules:
            if any(kw in text for kw in rule['keywords']):
                slots = {}
                # 抖音控制特殊处理：从关键词直接提取动作
                if rule['intent'] == 'douyin_control':
                    action = self._extract_douyin_action(text, rule['keywords'])
                    if action:
                        slots['action'] = action
                        return 'douyin_control', slots
                    continue  # 没匹配到关键词，继续下一个规则
                # 如果当前是 open_app/close_app，且文本中也包含抖音动作词
                # 优先使用抖音控制（如"打开评论"、"关闭弹幕"）
                if rule['intent'] in ('open_app', 'close_app') and has_douyin_action:
                    action = self._extract_douyin_action(text, douyin_keywords)
                    if action:
                        return 'douyin_control', {'action': action}
                if rule['slot_pattern']:
                    m = re.search(rule['slot_pattern'], text)
                    if m:
                        slots[rule['slot_name']] = m.group(1).strip()
                        # 尝试模糊提取应用名
                        if rule['intent'] in ('open_app', 'close_app'):
                            slots['app_name'] = self._fuzzy_extract_app_name(
                                m.group(1).strip()
                            )
                return rule['intent'], slots

        return 'unknown', {}

    def _fuzzy_extract_app_name(self, raw_name):
        """
        模糊提取应用名称
        移除常见前缀/后缀词
        """
        if not raw_name:
            return raw_name

        # 移除常见干扰词
        stop_words = ['程序', '软件', '应用', '打开', '启动', '关闭', '退出',
                       '请', '帮我', '我想', '能不能', '可以', '那个', '这个']
        result = raw_name
        for word in stop_words:
            result = result.replace(word, '')

        result = result.strip(' .，。、!！?？')
        return result if result else raw_name

    def _calculate_similarity(self, s1, s2):
        """计算两个字符串的相似度"""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def _extract_douyin_action(self, text, keywords):
        """从文本中提取匹配的抖音动作词"""
        text_lower = text.lower()
        for kw in keywords:
            if kw.lower() in text_lower:
                return kw
        return None

    def add_intent(self, intent_dict):
        """动态添加新意图"""
        self.intents.append(intent_dict)
