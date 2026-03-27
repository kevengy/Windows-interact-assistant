import os
import json

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

DEFAULT_CONFIG = {
    'wake_words': ['你好小猪'],
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
        yaml_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
        json_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
        if os.path.exists(yaml_path):
            path = yaml_path
        elif os.path.exists(json_path):
            path = json_path
        else:
            print("Config file not found, using default")
            return DEFAULT_CONFIG.copy()
    path = os.path.abspath(path)
    print(f"Config path: {path}")

    if not os.path.exists(path):
        print("Config file not found, using default")
        return DEFAULT_CONFIG.copy()

    try:
        with open(path, 'r', encoding='utf-8') as f:
            if path.endswith('.yaml') or path.endswith('.yml'):
                user_cfg = yaml.safe_load(f) or {}
            else:
                user_cfg = json.load(f) or {}
        print("Config loaded from file")
    except Exception as e:
        print(f"Config load error: {e}")
        user_cfg = {}

    cfg = DEFAULT_CONFIG.copy()
    cfg.update(user_cfg)
    print("Config merged")

    return cfg
