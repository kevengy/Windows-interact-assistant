import os
import json

DEFAULT_CONFIG = {
    'wake_words': ['hi', 'keven'],
    'language': 'zh-CN',
    'tts_engine': 'pyttsx3',
    'intents_path': os.path.join(os.path.dirname(__file__), '..', 'data', 'intents.json'),
    'plugin_path': os.path.join(os.path.dirname(__file__), '..', 'plugins'),
    'log_file': os.path.join(os.path.dirname(__file__), '..', 'assistant.log'),
    'app_map_path': os.path.join(os.path.dirname(__file__), '..', 'config', 'app_map.json'),
}


def load_config(path=None):
    print("Loading config...")
    if not path:
        path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
    path = os.path.abspath(path)
    print(f"Config path: {path}")

    if not os.path.exists(path):
        print("Config file not found, using default")
        return DEFAULT_CONFIG

    try:
        with open(path, 'r', encoding='utf-8') as f:
            user_cfg = json.load(f) or {}
        print("Config loaded from file")
    except Exception as e:
        print(f"Config load error: {e}")
        user_cfg = {}

    cfg = DEFAULT_CONFIG.copy()
    cfg.update(user_cfg)
    print("Config merged")

    return cfg
