import os


def say(text):
    print(f'[语音] {text}')
    return True


def notify(title, message):
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=5)
        return True
    except Exception:
        print(f'[通知] {title}: {message}')
        return False
