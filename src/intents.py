import json
import os
import re


class IntentParser:
    def __init__(self, intents_path):
        self.intents_path = intents_path
        self.intents = self._load_intents()

    def _load_intents(self):
        if not os.path.exists(self.intents_path):
            return []
        with open(self.intents_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def parse(self, text):
        text = text.strip().lower()

        for intent in self.intents:
            for pattern in intent.get('patterns', []):
                if re.search(pattern, text):
                    slots = {}
                    for slot_name, regex in intent.get('slots', {}).items():
                        m = re.search(regex, text)
                        if m:
                            slots[slot_name] = m.group(1)
                    return intent['name'], slots

        if '打开' in text or '启动' in text:
            target = re.sub(r'.*(打开|启动)\s*', '', text)
            return 'open_app', {'app_name': target.strip()}

        if '关闭' in text or '退出' in text:
            target = re.sub(r'.*(关闭|退出)\s*', '', text)
            return 'close_app', {'app_name': target.strip()}

        if '设置' in text and '音量' in text:
            value = re.search(r'音量\s?(\d+)', text)
            return 'set_volume', {'value': int(value.group(1)) if value else 50}

        if '定时' in text or '闹钟' in text:
            minutes = re.search(r'(\d+)\s*分钟', text)
            if minutes:
                return 'set_timer', {'minutes': int(minutes.group(1))}

        if '列出应用' in text or '显示应用' in text or '应用列表' in text:
            return 'list_apps', {}

        if '检查应用' in text or '查询应用' in text or '是否安装' in text:
            m = re.search(r'(?:检查应用|查询应用|是否安装)\s*(.*)', text)
            if m:
                return 'check_app', {'app_name': m.group(1).strip()}

        if '存入文件夹' in text or '保存到文件夹' in text or '存入文件' in text:
            # 语法：存入文件夹 <路径> 内容 <文本> 或 存入文件 <路径/文件名> <文本>
            folder_match = re.search(r'(?:存入文件夹|保存到文件夹)\s*([^\s:：]+)\s*(?:内容|文本)?\s*[:：]?\s*(.*)', text)
            file_match = re.search(r'(?:存入文件|保存)\s*([^\s:：]+\/[^\s:：]+)\s*(.*)', text)
            if folder_match:
                folder = folder_match.group(1).strip()
                content = folder_match.group(2).strip() or ''
                return 'save_to_folder', {'folder': folder, 'content': content}
            if file_match:
                filepath = file_match.group(1).strip()
                content = file_match.group(2).strip() or ''
                return 'save_to_folder', {'filepath': filepath, 'content': content}

        return 'unknown', {}
