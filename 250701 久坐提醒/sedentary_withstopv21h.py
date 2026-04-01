import time
import tkinter as tk
from tkinter import messagebox
import threading
import sys


def startup_popup():
    """程序启动时弹出一次提示"""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    messagebox.showinfo("提示", "您已点击兔子久坐提醒器，请勿重复点击，30分钟后会出现第一次提示。如需要立即结束进程请在terminal中ctrl+c或者找到任务管理器相应进程，也可以在30min后一次弹窗提醒中点击结束选项，久坐会导致心脑血管疾病，下背部疼痛，腰椎间盘突出和痔疮，兔兔温馨提示您请勿久坐。")
    root.destroy()


def show_popup():
    """循环提醒的弹窗"""
    def close_app():
        root.destroy()
        sys.exit(0)  # 彻底结束程序

    root = tk.Tk()
    root.title("提醒")
    root.attributes("-topmost", True)  # 窗口置顶
    root.geometry("300x120")

    label = tk.Label(root, text="该起来活动一下啦！", font=("微软雅黑", 12))
    label.pack(pady=15)

    ok_btn = tk.Button(root, text="好的", command=root.destroy, width=10)
    ok_btn.pack(side="left", padx=20, pady=10)

    quit_btn = tk.Button(root, text="退出程序", command=close_app, width=10, fg="red")
    quit_btn.pack(side="right", padx=20, pady=10)

    root.mainloop()


def reminder_loop():
    while True:
        time.sleep(3600)  # 30分钟是1800秒，建议这个时间
        show_popup()


if __name__ == "__main__":
    # 先运行一次启动提示
    startup_popup()

    # 开启提醒循环
    threading.Thread(target=reminder_loop, daemon=True).start()

    # 主线程挂起
    while True:
        time.sleep(1)

