try:
    import threading
    sr = None
    def _import_sr():
        global sr
        try:
            import speech_recognition as sr_module
            sr = sr_module
        except Exception:
            pass
    thread = threading.Thread(target=_import_sr, daemon=True)
    thread.start()
    thread.join(timeout=3)  # 3秒超时
    if sr is None:
        raise ImportError("speech_recognition import timeout")
except ImportError:
    sr = None


def has_pyaudio():
    try:
        import pyaudio
        return True
    except ImportError:
        return False


def list_microphone_names():
    if sr is None:
        return []
    try:
        import threading
        result = []
        def _list():
            try:
                result.extend(sr.Microphone.list_microphone_names())
            except Exception:
                pass
        thread = threading.Thread(target=_list, daemon=True)
        thread.start()
        thread.join(timeout=2)  # 2秒超时
        return result
    except Exception:
        return []


def check_speech_dependencies():
    if sr is None:
        return False, 'speech_recognition 模块未安装，请运行 pip install SpeechRecognition'
    if not has_pyaudio():
        return False, 'pyaudio 模块未安装，请运行 pip install pyaudio（Windows 可能需要安装预编译 wheel）'
    try:
        mics = list_microphone_names()
        if not mics:
            return False, '检测不到麦克风设备，请插入麦克风或检查系统设置'
        return True, f'检测到麦克风：{mics[0]}，可用麦克风数量 {len(mics)}'
    except Exception as e:
        return False, f'麦克风检测失败: {e}'


class SpeechRecognizer:
    def __init__(self, language='zh-CN'):
        ok, msg = check_speech_dependencies()
        if not ok:
            raise RuntimeError(msg)
        self.recognizer = sr.Recognizer()
        self.language = language

    def listen_once(self, timeout=5, phrase_time_limit=8):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print('请讲话...')
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            return False, '监听超时'
        except Exception as e:
            return False, f'录音失败: {e}'

        try:
            text = self.recognizer.recognize_google(audio, language=self.language)
            return True, text
        except sr.WaitTimeoutError:
            return False, '监听超时'
        except sr.UnknownValueError:
            return False, '无法识别语音'
        except sr.RequestError as e:
            return False, f'语音识别服务出错: {e}'
        except Exception as e:
            return False, f'识别失败: {e}'

    def listen_with_wake_word(self, wake_words=None, retries=2):
        if wake_words is None:
            wake_words = []

        attempt = 0
        while attempt <= retries:
            ok, text = self.listen_once()
            if not ok:
                attempt += 1
                if attempt > retries:
                    return False, text
                print(f'语音识别失败，重试 {attempt}/{retries} -> {text}')
                continue

            normalized = text.lower().strip()
            for wake in wake_words:
                if wake in normalized:
                    normalized = normalized.replace(wake, '').strip()
                    break

            if not normalized:
                attempt += 1
                if attempt > retries:
                    return False, '未检测到有效指令内容，请重试'
                print(f'未检测到指令内容，重试 {attempt}/{retries}')
                continue

            return True, normalized

        return False, '语音识别失败'
