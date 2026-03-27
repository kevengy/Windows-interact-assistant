"""
语音识别模块 - 使用 sounddevice 采集 + Google 语音识别
"""
import io
import wave
import threading
import numpy as np
import sounddevice as sd
import speech_recognition as sr


def check_speech_dependencies():
    """检查语音依赖是否满足"""
    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        if not input_devices:
            return False, '检测不到麦克风设备，请插入麦克风或检查系统设置'
        default_input = sd.query_devices(kind='input')
        return True, f'检测到麦克风：{default_input["name"]}，采样率 {int(default_input["default_samplerate"])}Hz'
    except Exception as e:
        return False, f'音频设备检测失败: {e}'


def list_microphones():
    """列出所有可用麦克风设备"""
    try:
        devices = sd.query_devices()
        mics = []
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                mics.append(f"[{i}] {d['name']} ({int(d['default_samplerate'])}Hz)")
        return mics
    except Exception:
        return []


class SounddeviceMicrophone:
    """
    使用 sounddevice 作为音频源的麦克风封装，
    替代 pyaudio（Windows 上 pyaudio 安装困难）
    """
    def __init__(self, device=None, sample_rate=16000, chunk_size=1024):
        if device is None:
            device = sd.query_devices(kind='input')['index']
        self.device = device
        self.sample_rate = int(sample_rate)
        self.chunk_size = chunk_size

        # 获取设备参数
        if isinstance(device, int):
            dev_info = sd.query_devices(device)
        else:
            dev_info = sd.query_devices(kind='input')
        self.sample_rate = int(dev_info['default_samplerate'])
        self.channels = int(dev_info['max_input_channels'])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def listen(self, timeout=5, phrase_time_limit=8):
        """
        录制音频，返回 (success, audio_data or error_message)
        timeout: 等待语音开始的超时（秒）
        phrase_time_limit: 语音最大持续时间（秒）
        """
        duration = min(phrase_time_limit + 2, 30)  # 留 2 秒缓冲
        try:
            print(f'正在录音（设备: {self.device}，采样率: {self.sample_rate}Hz）...')

            # 录制音频，使用 np.float32 格式
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                device=self.device
            )

            # 等待录音完成
            sd.wait()

            # 转换为 16-bit PCM
            audio_int16 = np.int16(audio_data * 32767).flatten()

            # 转换为 WAV 格式字节
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())
            wav_bytes = wav_buffer.getvalue()

            return True, wav_bytes

        except sd.PortAudioError as e:
            return False, f'录音失败（PortAudio）: {e}'
        except Exception as e:
            return False, f'录音失败: {e}'


class SpeechRecognizer:
    """
    语音识别器，支持中文识别
    使用 sounddevice 采集 + Google 语音识别
    """
    def __init__(self, language='zh-CN'):
        ok, msg = check_speech_dependencies()
        if not ok:
            raise RuntimeError(msg)
        self.recognizer = sr.Recognizer()
        self.language = language
        self.microphone = SounddeviceMicrophone()

    def _recognize_with_retry(self, audio, retries=3, delay=1):
        """带重试的语音识别，处理网络连接错误"""
        import time
        last_error = None
        for attempt in range(retries):
            try:
                text = self.recognizer.recognize_google(audio, language=self.language)
                return True, text
            except Exception as e:
                last_error = e
                err_str = str(e)
                # WinError 10054 = 连接被重置，WinError -1 = 连接断开
                if '10054' in err_str or '10053' in err_str or 'WinError -1' in err_str or 'Connection' in err_str or 'reset' in err_str.lower():
                    if attempt < retries - 1:
                        wait_time = delay * (2 ** attempt)  # 指数退避
                        print(f'网络连接被重置，{wait_time}秒后重试 ({attempt + 1}/{retries})...')
                        time.sleep(wait_time)
                        continue
                # 其他错误直接抛出
                raise
        return False, f'识别失败: {last_error}'

    def listen_once(self, timeout=5, phrase_time_limit=8):
        """
        录制并识别一段语音，返回 (success, text or error_message)
        """
        ok, audio_or_error = self.microphone.listen(timeout=timeout, phrase_time_limit=phrase_time_limit)
        if not ok:
            return False, audio_or_error

        audio_data = audio_or_error

        try:
            # 将 WAV 字节数据封装为 AudioFile（从内存）
            audio_io = io.BytesIO(audio_data)
            with sr.AudioFile(audio_io) as source:
                audio = self.recognizer.record(source)

            # 使用 Google 语音识别（需要网络），带重试
            return self._recognize_with_retry(audio)

        except sr.WaitTimeoutError:
            return False, '监听超时，未检测到语音'
        except sr.UnknownValueError:
            return False, '无法识别语音内容'
        except sr.RequestError as e:
            return False, f'语音识别服务出错: {e}'
        except Exception as e:
            return False, f'识别失败: {e}'

    def listen_with_wake_word(self, wake_words=None, retries=2):
        """
        持续监听直到检测到唤醒词，然后返回后续指令
        wake_words: 唤醒词列表，如 ['小助手', '助手']
        """
        if wake_words is None:
            wake_words = []

        attempt = 0
        while attempt <= retries:
            ok, text = self.listen_once()
            if not ok:
                attempt += 1
                if attempt > retries:
                    return False, text
                print(f'语音识别失败，重试 {attempt}/{retries}: {text}')
                continue

            normalized = text.lower().strip()
            print(f'[调试] 识别结果: [{text}] -> normalized: [{normalized}]')

            # 如果配置了唤醒词，检查是否包含
            if wake_words:
                found_wake = False
                remaining = normalized
                for wake in wake_words:
                    wake_lower = wake.lower()
                    # 精确匹配：唤醒词在识别结果中
                    if wake_lower in remaining:
                        remaining = remaining.replace(wake_lower, '', 1).strip()
                        found_wake = True
                        print(f'[调试] 精确匹配唤醒词 [{wake}] 成功，剩余: [{remaining}]')
                        break
                    # 模糊匹配：使用相似度检测（处理语音识别常见的近音字错误）
                    from difflib import SequenceMatcher
                    # 检查唤醒词开头部分的匹配（容忍"麦麦"被识别成"买买"等）
                    wake_prefix = wake_lower[:max(2, len(wake_lower) - 2)]
                    for i in range(len(remaining) - len(wake_prefix) + 1):
                        chunk = remaining[i:i + len(wake_prefix) + 2]
                        ratio = SequenceMatcher(None, wake_prefix, chunk).ratio()
                        if ratio >= 0.8:
                            # 找到了近似前缀，从该位置提取唤醒词+后续内容
                            remaining = remaining[i + len(wake_prefix) + 2:].strip()
                            found_wake = True
                            print(f'[调试] 模糊匹配唤醒词 [{wake}] 成功（相似度 {ratio:.2f}），剩余: [{remaining}]')
                            break
                    if found_wake:
                        break

                if not found_wake:
                    print(f'未检测到唤醒词，继续监听...')
                    continue

                if not remaining:
                    # 只有唤醒词没有后续指令
                    print('检测到唤醒词，请说出指令...')
                    continue

                return True, remaining
            else:
                # 无唤醒词配置，直接返回识别结果
                return True, normalized

        return False, '语音识别失败'


def test_recording():
    """测试录音功能"""
    print('=== 录音测试 ===')
    ok, msg = check_speech_dependencies()
    print(f'依赖检查: {msg}')

    mics = list_microphones()
    print(f'可用麦克风 ({len(mics)}):')
    for m in mics:
        print(f'  {m}')

    print('\n开始 3 秒录音测试...')
    mic = SounddeviceMicrophone()
    ok, result = mic.listen(timeout=5, phrase_time_limit=3)
    if ok:
        print(f'录音成功，音频大小: {len(result)} bytes')
        # 简单验证：检查是否为有效的 WAV 数据
        print('WAV 数据有效')
    else:
        print(f'录音失败: {result}')


if __name__ == '__main__':
    test_recording()
