import os
import sys


def say(text):
    print(f'[语音] {text}')
    return True


def notify(title, message):
    """发送系统通知，失败时回退到 stderr"""
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=5)
        return True
    except ImportError:
        pass
    except Exception:
        pass

    # 回退：写入 stderr，确保在无控制台时也能被捕获
    if sys.stderr is not None:
        print(f'[通知] {title}: {message}', file=sys.stderr)
    return False
