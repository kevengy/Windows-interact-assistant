"""
混合 NLU 引擎
结合 FuzzyRegex（快速路径）和 EmbeddingMatcher（语义路径）
作为 IntentParser 的高级替代品
"""
import os
import json
from typing import Tuple, Dict, Optional

from .fuzzy_regex import FuzzyRegexMatcher


class HybridNLUEngine:
    """
    混合意图解析引擎

    解析流程：
    1. FuzzyRegex 快速路径（正则匹配，高精度）
    2. EmbeddingMatcher 语义路径（句子嵌入，高召回）——可选
    3. 父类 IntentParser 回退（兼容 legacy）
    """

    def __init__(
        self,
        intents_path: str,
        intent_descriptions_path: str = None,
        embedding_threshold: float = 0.65,
        use_embedding: bool = False
    ):
        """
        Args:
            intents_path: intents.json 路径
            intent_descriptions_path: intent_descriptions.json 路径（embedding 用）
            embedding_threshold: 嵌入匹配置信度阈值
            use_embedding: 是否启用 embedding 匹配（需要 sentence-transformers）
        """
        self.intents_path = intents_path
        self.intent_descriptions_path = intent_descriptions_path
        self.embedding_threshold = embedding_threshold
        self.use_embedding = use_embedding

        # 快速路径：模糊正则匹配器
        self.fuzzy_regex = FuzzyRegexMatcher(intents_path)

        # 语义路径：句子嵌入匹配器（延迟加载）
        self.embedding_matcher = None
        self._intent_descriptions = []

        if use_embedding:
            self._init_embedding_matcher()

        self._load_intent_descriptions()

    def _init_embedding_matcher(self):
        """初始化 embedding 匹配器（可选，需 sentence-transformers）"""
        try:
            from .embedding_matcher import EmbeddingMatcher
            self.embedding_matcher = EmbeddingMatcher(
                model_name='paraphrase-multilingual-MiniLM-L12-v2'
            )
            # 预加载所有 intent 描述的向量
            for desc in self._intent_descriptions:
                self.embedding_matcher.add_intent(
                    name=desc['name'],
                    description=desc['description'],
                    slots=desc.get('slots', {})
                )
        except ImportError:
            self.embedding_matcher = None
        except Exception:
            self.embedding_matcher = None

    def _load_intent_descriptions(self):
        """加载意图描述语料"""
        if not self.intent_descriptions_path:
            return
        try:
            with open(self.intent_descriptions_path, 'r', encoding='utf-8') as f:
                self._intent_descriptions = json.load(f)
        except Exception:
            self._intent_descriptions = []

    def parse(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        解析文本意图

        Args:
            text: 输入文本

        Returns:
            (intent_name, slots_dict)
        """
        text = text.strip().lower()
        if not text:
            return 'unknown', {}

        # 1. FuzzyRegex 快速路径
        intent, slots = self.fuzzy_regex.match(text)
        if intent != 'unknown':
            return intent, slots

        # 2. EmbeddingMatcher 语义路径
        if self.embedding_matcher and self.use_embedding:
            intent, confidence = self.embedding_matcher.classify(text)
            if intent != 'unknown' and confidence >= self.embedding_threshold:
                # 从 intent_descriptions 获取 slots 定义
                slots = self._get_slots_for_intent(intent, text)
                return intent, slots

        # 3. 回退到原始 IntentParser（legacy 兼容）
        # 注意：此处返回 unknown，因为 HybridNLUEngine 替代了 IntentParser
        # 实际使用时建议直接用 FuzzyRegexMatcher 作为主要解析器
        return 'unknown', {}

    def _get_slots_for_intent(self, intent_name: str, text: str) -> Dict[str, str]:
        """根据意图类型从文本中提取槽位"""
        # 通用的槽位提取逻辑
        slots = {}

        if intent_name == 'open_app':
            import re
            m = re.search(r'(?:打开|启动)\s*(.*)', text)
            if m:
                slots['app_name'] = m.group(1).strip()

        elif intent_name == 'close_app':
            import re
            m = re.search(r'(?:关闭|退出)\s*(.*)', text)
            if m:
                slots['app_name'] = m.group(1).strip()

        elif intent_name == 'douyin_control':
            import re
            m = re.search(
                r'(?:抖音|douyin)\s*(播放|暂停|点赞|评论|滚动|关注|分享|上滑|下滑|全屏|静音|刷新|首页)',
                text
            )
            if m:
                slots['action'] = m.group(1)

        elif intent_name == 'set_volume':
            import re
            m = re.search(r'音量\s?(\d+)', text)
            if m:
                slots['value'] = m.group(1)

        elif intent_name == 'set_timer':
            import re
            m = re.search(r'(\d+)\s*分钟', text)
            if m:
                slots['minutes'] = m.group(1)

        return slots

    def add_intent(self, name: str, description: str, slots: Dict = None):
        """动态添加新意图到 embedding 索引"""
        if self.embedding_matcher:
            self.embedding_matcher.add_intent(name, description, slots or {})
        self._intent_descriptions.append({
            'name': name,
            'description': description,
            'slots': slots or {}
        })
