import sys
import os
from pathlib import Path

# 支持作为模块调用和直接运行两种方式
if __name__ == '__main__' and __package__ is None:
    # 添加项目根目录到 sys.path，使 src 能被识别为包
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = 'src'

try:
    from .config import load_config
    from .executor import execute_intent
    from .feedback import say, notify
    from .intents import IntentParser
    from .logger import configure_logging, get_logger
    from .plugins import PluginManager
    from .recognize import SpeechRecognizer, check_speech_dependencies
    from .nlu.phonetic_corrector import PhoneticCorrector
    from .nlu.fuzzy_regex import FuzzyRegexMatcher
except ImportError:
    from config import load_config
    from executor import execute_intent
    from feedback import say, notify
    from intents import IntentParser
    from logger import configure_logging, get_logger
    from plugins import PluginManager
    from recognize import SpeechRecognizer, check_speech_dependencies
    from phonetic_corrector import PhoneticCorrector
    from fuzzy_regex import FuzzyRegexMatcher


def main():
    print("Starting main...")
    cfg = load_config()
    print("Config loaded")
    configure_logging(cfg.get('log_file'))
    logger = get_logger()
    print("Logging configured")

    parser = IntentParser(cfg.get('intents_path'))
    plugin_manager = PluginManager(cfg.get('plugin_path'))

    from .executor import load_app_map
    load_app_map(cfg.get('app_map_path'))

    # 初始化增强 NLU 组件
    corrector = None
    fuzzy_matcher = None
    if cfg.get('enable_asr_correction', True):
        try:
            from .executor import APP_MAP as _APP_MAP
            corrector = PhoneticCorrector(
                intents_path=cfg.get('intents_path'),
                app_names=list(_APP_MAP.keys())
            )
            logger.info('ASR 纠错模块初始化成功')
        except Exception as e:
            logger.warning(f'ASR 纠错模块初始化失败: {e}')

    if cfg.get('nlu_engine') == 'fuzzy_regex':
        try:
            fuzzy_matcher = FuzzyRegexMatcher(cfg.get('intents_path'))
            logger.info('FuzzyRegex 匹配器初始化成功')
        except Exception as e:
            logger.warning(f'FuzzyRegex 匹配器初始化失败: {e}')

    # 扫描本地程序目录并更新 APP_MAP
    from .executor import scan_all_program_folders
    try:
        scanned = scan_all_program_folders()
        logger.info(f'扫描到 {len(scanned)} 个本地应用程序')
    except Exception as e:
        logger.warning(f'扫描本地应用程序失败: {e}')
        scanned = []

    dep_ok, dep_msg = check_speech_dependencies()
    voice_available = dep_ok
    recognizer = None
    # 延迟初始化语音识别器，避免启动卡住
    # if voice_available:
    #     try:
    #         recognizer = SpeechRecognizer(language=cfg.get('language', 'zh-CN'))
    #         logger.info('语音识别模块初始化成功')
    #     except Exception as e:
    #         voice_available = False
    #         logger.warning(f'语音识别初始化失败: {e}')

    if not voice_available:
        logger.warning('语音识别不可用: ' + dep_msg)

    logger.info('语音助手启动完成')
    print('语音模块检测:', dep_msg)

    print('欢迎使用 Windows 交互语音助手（输入“退出”结束）')
    print('输入 1 进入语音输入模式；输入 0 继续文本输入。')
    print('Entering main loop...')
    use_voice = False

    while True:
        try:
            if use_voice:
                if not voice_available or recognizer is None:
                    logger.warning('语音识别功能不可用，自动切回文本模式')
                    say('语音识别不可用，请使用文本输入')
                    use_voice = False
                    continue

                ok, query = recognizer.listen_with_wake_word(cfg.get('wake_words', []))
                if not ok:
                    logger.warning(f'语音识别失败: {query}')
                    say(query)
                    continue
                print('识别内容：', query)
            else:
                query = input('请输入指令：').strip()

            if not query:
                continue

            if query in ('0', '1'):
                use_voice = (query == '1')
                if use_voice and voice_available and recognizer is None:
                    try:
                        recognizer = SpeechRecognizer(language=cfg.get('language', 'zh-CN'))
                        logger.info('语音识别模块初始化成功')
                    except Exception as e:
                        voice_available = False
                        logger.warning(f'语音识别初始化失败: {e}')
                        say('语音识别初始化失败，请使用文本输入')
                        use_voice = False
                        continue
                logger.info(f'输入模式切换为: {"语音" if use_voice else "文本"}')
                say('已切换为' + ('语音' if use_voice else '文本') + '模式')
                continue

            if query in ('退出', '关闭', '拜拜'):
                say('再见')
                break

            # ASR 纠错
            if corrector:
                corrected = corrector.correct(query)
                if corrected != query:
                    print(f'ASR纠错：{query} -> {corrected}')
                    logger.info(f'ASR纠错: {query} -> {corrected}')
                    query = corrected

            # 模糊匹配优先（如果启用）
            if fuzzy_matcher:
                intent_name, slots = fuzzy_matcher.match(query)
                if intent_name != 'unknown':
                    logger.info(f'FuzzyRegex解析: {query} => intent={intent_name}, slots={slots}')
                else:
                    intent_name, slots = parser.parse(query)
                    logger.info(f'解析: {query} => intent={intent_name}, slots={slots}')
            else:
                intent_name, slots = parser.parse(query)
                logger.info(f'解析: {query} => intent={intent_name}, slots={slots}')

            plugin_ok, plugin_result = plugin_manager.try_execute(intent_name, slots)
            if plugin_ok:
                text = plugin_result
                logger.info(f'插件命令执行: {text}')
                say(text)
                notify('语音助手', text)
                continue

            success, message = execute_intent(intent_name, slots)
            if not success:
                logger.warning(message)
                say('执行失败:' + message)
            else:
                logger.info(message)
                say(message)
            notify('语音助手', message)

        except KeyboardInterrupt:
            say('已退出')
            break
        except Exception as e:
            logger.error(f'运行时异常: {e}')
            say('发生错误:' + str(e))

if __name__ == '__main__':
    main()
