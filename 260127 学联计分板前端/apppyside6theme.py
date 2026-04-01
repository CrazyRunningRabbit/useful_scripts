2# apppyside6.py
# PySide6 desktop version of the "Guess Word Scoreboard" game
# Requires: PySide6

import sys
import random
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QSpinBox,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtGui import QPixmap


WORD_BANK = {
    "赞助商主题": ["电话卡", "中国移动", "京东", "新航道", "三达集团", "蓝博士", "银联", "蓝月亮", "宴来居", "Dance Sport", "西京都"],
    "春节主题": ["饺子", "红包", "鞭炮", "春晚", "灯笼", "春联", "舞狮", "拜年", "团圆饭", "福字", "守岁", "年兽", "窗花", "年糕", "汤圆",
             "压岁钱", "中国结", "冰糖葫芦", "正月十五", "年夜饭", "辞旧迎新", "恭喜发财", "龙马精神", "张灯结彩", "万象更新"],
    "马年主题": ["马车", "马蹄", "马鞍", "马尾", "骏马", "小马宝莉", "马到成功", "一马当先", "马戏团", "斑马", "千里马", "马不停蹄",
             "老马识途", "金戈铁马", "马首是瞻", "汗马功劳", "青梅竹马", "马术", "马年吉祥", "马革裹尸", "天马行空", "龙马精神",
             "蛛丝马迹", "兵荒马乱", "塞翁失马"],
    "新加坡主题": ["鱼尾狮", "榴莲", "滨海湾", "圣淘沙", "肉骨茶", "辣椒螃蟹", "摩天轮", "星耀樟宜", "海南鸡饭", "乌节路", "娘惹文化",
             "新加坡国立大学", "南洋理工大学", "小印度", "牛车水", "夜间动物园", "环球影城", "组屋", "咖喱鱼头", "叻沙", "花园城市",
             "李光耀", "新加坡樟宜机场", "新加坡司令", "甘榜格南"],
    "留学生活主题": ["签证", "护照", "机票", "行李箱", "宿舍", "图书馆", "小组作业", "期末考试", "食堂", "租房", "Presentation", "Deadline",
               "奖学金", "Office Hour", "思乡", "汇率", "打工", "毕业论文", "迎新周", "学生证", "跨文化交际", "学术论文", "毕业典礼",
               "校友会", "文化冲击"],
    "综合创意词": ["微信", "支付宝", "网购", "外卖", "短视频", "自拍", "网红", "打卡", "emo", "躺平", "干饭人", "内卷", "凡尔赛", "破防",
             "元宇宙", "区块链", "人工智能", "无人机", "碳中和", "冬奥会", "命运共同体", "一带一路", "数字货币", "虚拟现实"],
    "春晚节目相关": ["唱歌", "跳舞", "相声", "魔术", "主持人", "彩排", "灯光", "音响", "化妆", "礼服", "走台", "候场", "音效", "追光",
               "串词", "幕布", "道具", "后台", "直播", "视听语言", "舞台调度", "情绪饱满", "声台形表", "圆满成功"],
}


APP_QSS = r"""
QWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #1a0b0b, stop:0.45 #2a1111, stop:1 #0f172a);
    color: rgba(255,255,255,230);
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC";
    font-size: 14px;
}

QFrame#Card {
    background: rgba(255,255,255,15);
    border: 1px solid rgba(255,215,0,55);
    border-radius: 16px;
}

QLabel#Title {
    color: rgb(255,215,0);
    font-size: 40px;
    font-weight: 900;
}

QLabel#Subtitle {
    color: rgba(255,255,255,210);
    font-size: 14px;
}

QLabel#Badge {
    background: rgba(255,215,0,35);
    border: 1px solid rgba(255,215,0,55);
    border-radius: 999px;
    padding: 6px 10px;
    font-weight: 700;
}

QLabel#BigWord {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 rgba(255,215,0,25), stop:1 rgba(255,0,0,25));
    border: 1px solid rgba(255,215,0,60);
    border-radius: 16px;
    padding: 14px;
    font-size: 56px;
    font-weight: 900;
    qproperty-alignment: AlignCenter;
}

QLabel#HintWord {
    background: rgba(255,255,255,15);
    border: 1px dashed rgba(255,215,0,60);
    border-radius: 16px;
    padding: 18px;
    font-size: 18px;
    font-weight: 700;
    qproperty-alignment: AlignCenter;
}


QLabel#Timer {
    background: rgba(0,0,0,45);
    border: 1px solid rgba(255,215,0,70);
    border-radius: 16px;
    padding: 10px;
    font-size: 48px;
    font-weight: 900;
    color: rgb(255,215,0);
    qproperty-alignment: AlignCenter;
}

QLabel#Score {
    background: rgba(255,255,255,18);
    border: 1px solid rgba(255,215,0,55);
    border-radius: 16px;
    padding: 10px;
    font-size: 44px;
    font-weight: 900;
    qproperty-alignment: AlignCenter;
}

QLabel#Muted {
    color: rgba(255,255,255,170);
    font-size: 13px;
}

QPushButton {
    background: rgba(255,255,255,18);
    border: 1px solid rgba(255,215,0,55);
    border-radius: 12px;
    padding: 10px 12px;
    font-weight: 700;
}

QPushButton:hover {
    background: rgba(255,215,0,20);
}

QPushButton:pressed {
    background: rgba(255,215,0,30);
}

QPushButton:disabled {
    background: rgba(255,255,255,10);
    border: 1px solid rgba(255,255,255,20);
    color: rgba(255,255,255,120);
}

QSpinBox {
    background: rgba(0,0,0,30);
    border: 1px solid rgba(255,215,0,55);
    border-radius: 10px;
    padding: 4px 8px;
    font-weight: 700;
}
"""


def mmss(seconds: int) -> str:
    if seconds < 0:
        seconds = 0
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


class Card(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("Card")
        self.setFrameShape(QFrame.NoFrame)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("猜词大作战 · 记分牌")
        self.setMinimumSize(1200, 720)

        self.active = False
        self.round_idx = 1
        self.score_a = 0
        self.score_b = 0

        self.remaining = 0
        self.assist_active = False
        self.assist_remaining = 0

        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(200)
        self.tick_timer.timeout.connect(self.on_tick)

        self.assist_timer = QTimer(self)
        self.assist_timer.setInterval(200)
        self.assist_timer.timeout.connect(self.on_assist_tick)

        self.build_ui()
        self.reset_round_state()

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title_row = QHBoxLayout()

        logo_label = QLabel()
        pixmap = QPixmap("logo.png")
        logo_label.setPixmap(pixmap.scaled(
            64, 64,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))
        logo_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        title = QLabel("猜词大作战 · 记分牌")
        title.setObjectName("Title")

        title_row.addWidget(logo_label)
        title_row.addSpacing(12)
        title_row.addWidget(title)
        title_row.addStretch(1)

        outer.addLayout(title_row)

        title.setObjectName("Title")
        subtitle = QLabel("每次邀请 2 组嘉宾上台，每组 2 人（一人比划，一人猜）。出词后自动倒计时，结束自动归零。")
        subtitle.setObjectName("Subtitle")

        
        outer.addWidget(subtitle)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        outer.addLayout(top_row)

        self.card_left = Card()
        self.card_mid = Card()
        self.card_right = Card()
        self.card_left.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.card_mid.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.card_right.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        top_row.addWidget(self.card_left, 4)
        top_row.addWidget(self.card_mid, 5)
        top_row.addWidget(self.card_right, 4)

        self.build_left_card()
        self.build_mid_card()
        self.build_right_card()

        bottom = Card()
        outer.addWidget(bottom)

        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(14, 14, 14, 14)
        bottom_layout.setSpacing(10)

        badge = QLabel("主题出词")
        badge.setObjectName("Badge")
        bottom_layout.addWidget(badge)

        hint = QLabel("点击主题随机出词，立刻开始倒计时。倒计时期间主题与计分锁定，结束自动清空并恢复可点击。")
        hint.setObjectName("Muted")
        bottom_layout.addWidget(hint)

        self.theme_buttons = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        bottom_layout.addLayout(grid)

        themes = list(WORD_BANK.keys())
        cols = 7
        for i, name in enumerate(themes):
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked=False, t=name: self.start_round(t))
            self.theme_buttons[name] = btn
            r = i // cols
            c = i % cols
            grid.addWidget(btn, r, c)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)
        bottom_layout.addLayout(controls_row)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(10, 600)
        self.duration_spin.setValue(90)
        self.duration_spin.setSuffix(" 秒")
        dur_label = QLabel("本轮倒计时：")
        dur_label.setObjectName("Muted")

        self.fullscreen_btn = QPushButton("全屏")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)

        controls_row.addWidget(dur_label)
        controls_row.addWidget(self.duration_spin)
        controls_row.addStretch(1)
        controls_row.addWidget(self.fullscreen_btn)

    def build_left_card(self):
        layout = QVBoxLayout(self.card_left)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        badge = QLabel("游戏说明")
        badge.setObjectName("Badge")
        layout.addWidget(badge)

        rule = QLabel(
            "参与形式：每次 2 组上台，每组 2 人\n"
            "游戏流程：每组限时，不能说出词语中的字\n"
            "计分方式：猜对 1 词得 1 分\n"
            "胜负判定：两轮后累计得分最高组获胜\n"
            "互动设计：卡壳可邀请观众协助比划 10 秒"
        )
        rule.setWordWrap(True)
        layout.addWidget(rule)

        badge2 = QLabel("轮次与控制")
        badge2.setObjectName("Badge")
        layout.addWidget(badge2)

        row = QHBoxLayout()
        row.setSpacing(8)
        layout.addLayout(row)

        self.prev_round_btn = QPushButton("上一轮")
        self.next_round_btn = QPushButton("下一轮")
        self.reset_score_btn = QPushButton("重置分数")

        self.prev_round_btn.clicked.connect(self.prev_round)
        self.next_round_btn.clicked.connect(self.next_round)
        self.reset_score_btn.clicked.connect(self.reset_scores)

        row.addWidget(self.prev_round_btn)
        row.addWidget(self.next_round_btn)
        row.addWidget(self.reset_score_btn)

        self.round_label = QLabel("")
        self.round_label.setObjectName("Muted")
        layout.addWidget(self.round_label)
        layout.addStretch(1)

    def build_mid_card(self):
        layout = QVBoxLayout(self.card_mid)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        badge_word = QLabel("当前词语")
        badge_word.setObjectName("Badge")
        layout.addWidget(badge_word)

        self.word_label = QLabel("")
        self.word_label.setObjectName("BigWord")
        self.word_label.setTextInteractionFlags(Qt.NoTextInteraction)
        layout.addWidget(self.word_label)

        badge_timer = QLabel("倒计时")
        badge_timer.setObjectName("Badge")
        layout.addWidget(badge_timer)

        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("Timer")
        layout.addWidget(self.timer_label)

        badge_assist = QLabel("观众协助")
        badge_assist.setObjectName("Badge")
        layout.addWidget(badge_assist)

        assist_row = QHBoxLayout()
        assist_row.setSpacing(10)
        layout.addLayout(assist_row)

        self.assist_btn = QPushButton("开启协助 10 秒")
        self.end_btn = QPushButton("结束本轮")

        self.assist_btn.clicked.connect(self.start_assist)
        self.end_btn.clicked.connect(self.end_round)

        assist_row.addWidget(self.assist_btn)
        assist_row.addWidget(self.end_btn)

        self.assist_info = QLabel("")
        self.assist_info.setWordWrap(True)
        self.assist_info.setObjectName("Muted")
        layout.addWidget(self.assist_info)

        layout.addStretch(1)

    def build_right_card(self):
        layout = QVBoxLayout(self.card_right)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        badge = QLabel("计分区")
        badge.setObjectName("Badge")
        layout.addWidget(badge)

        score_row = QHBoxLayout()
        score_row.setSpacing(10)
        layout.addLayout(score_row)

        a_box = Card()
        b_box = Card()
        score_row.addWidget(a_box, 1)
        score_row.addWidget(b_box, 1)

        a_layout = QVBoxLayout(a_box)
        a_layout.setContentsMargins(12, 12, 12, 12)
        a_layout.setSpacing(8)

        b_layout = QVBoxLayout(b_box)
        b_layout.setContentsMargins(12, 12, 12, 12)
        b_layout.setSpacing(8)

        a_name = QLabel("A 组")
        a_name.setObjectName("Muted")
        b_name = QLabel("B 组")
        b_name.setObjectName("Muted")

        self.score_a_label = QLabel("0")
        self.score_a_label.setObjectName("Score")
        self.score_b_label = QLabel("0")
        self.score_b_label.setObjectName("Score")

        a_layout.addWidget(a_name)
        a_layout.addWidget(self.score_a_label)

        b_layout.addWidget(b_name)
        b_layout.addWidget(self.score_b_label)

        a_btn_row = QHBoxLayout()
        a_btn_row.setSpacing(8)
        b_btn_row = QHBoxLayout()
        b_btn_row.setSpacing(8)

        self.a_plus = QPushButton("A +1")
        self.a_minus = QPushButton("A -1")
        self.b_plus = QPushButton("B +1")
        self.b_minus = QPushButton("B -1")

        self.a_plus.clicked.connect(lambda: self.add_score("A", 1))
        self.a_minus.clicked.connect(lambda: self.add_score("A", -1))
        self.b_plus.clicked.connect(lambda: self.add_score("B", 1))
        self.b_minus.clicked.connect(lambda: self.add_score("B", -1))

        a_btn_row.addWidget(self.a_plus)
        a_btn_row.addWidget(self.a_minus)
        b_btn_row.addWidget(self.b_plus)
        b_btn_row.addWidget(self.b_minus)

        a_layout.addLayout(a_btn_row)
        b_layout.addLayout(b_btn_row)

        self.result_hint = QLabel("")
        self.result_hint.setWordWrap(True)
        self.result_hint.setObjectName("Muted")
        layout.addWidget(self.result_hint)

        layout.addStretch(1)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("全屏")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("退出全屏")

    def prev_round(self):
        if self.active:
            return
        self.round_idx = max(1, self.round_idx - 1)
        self.update_round_label()
        self.update_result_hint()

    def next_round(self):
        if self.active:
            return
        self.round_idx = min(2, self.round_idx + 1)
        self.update_round_label()
        self.update_result_hint()

    def reset_scores(self):
        if self.active:
            return
        self.score_a = 0
        self.score_b = 0
        self.round_idx = 1
        self.update_scores_ui()
        self.update_round_label()
        self.update_result_hint()

    def update_round_label(self):
        self.round_label.setText(f"当前轮次：第 {self.round_idx} 轮（可做预选赛与决赛）")

    def update_scores_ui(self):
        self.score_a_label.setText(str(self.score_a))
        self.score_b_label.setText(str(self.score_b))

    def update_result_hint(self):
        if self.active:
            self.result_hint.setText("")
            return

        if self.round_idx != 2:
            self.result_hint.setText("")
            return

        if self.score_a > self.score_b:
            self.result_hint.setText("两轮结束：A 组领先 🎉")
        elif self.score_b > self.score_a:
            self.result_hint.setText("两轮结束：B 组领先 🎉")
        else:
            self.result_hint.setText("两轮结束：目前平分，可加赛一轮")

    def set_controls_enabled(self, enabled: bool):
        for btn in self.theme_buttons.values():
            btn.setEnabled(enabled)

        self.prev_round_btn.setEnabled(enabled)
        self.next_round_btn.setEnabled(enabled)
        self.reset_score_btn.setEnabled(enabled)

        self.a_plus.setEnabled(enabled)
        self.a_minus.setEnabled(enabled)
        self.b_plus.setEnabled(enabled)
        self.b_minus.setEnabled(enabled)

        self.duration_spin.setEnabled(enabled)

    def reset_round_state(self):
        self.active = False
        self.assist_active = False
        self.assist_remaining = 0
        self.remaining = 0

        self.word_label.setObjectName("HintWord")
        self.word_label.setStyleSheet("")  # 强制刷新样式
        self.word_label.setText("请点击下方任一主题开始")

        self.timer_label.setText(mmss(self.duration_spin.value()))
        self.assist_info.setText("")
        self.assist_btn.setEnabled(False)
        self.end_btn.setEnabled(False)

        self.set_controls_enabled(True)
        self.update_round_label()
        self.update_scores_ui()
        self.update_result_hint()

        if self.tick_timer.isActive():
            self.tick_timer.stop()
        if self.assist_timer.isActive():
            self.assist_timer.stop()

    def start_round(self, theme_name: str):
        if self.active:
            return

        if theme_name not in WORD_BANK or not WORD_BANK[theme_name]:
            QMessageBox.warning(self, "词库为空", "该主题词库为空，请先添加词语。")
            return

        self.active = True
        self.assist_active = False
        self.assist_remaining = 0

        self.remaining = int(self.duration_spin.value())
        word = random.choice(WORD_BANK[theme_name])

        self.word_label.setText(word)
        self.timer_label.setText(mmss(self.remaining))

        self.assist_info.setText("")
        self.assist_btn.setEnabled(True)
        self.end_btn.setEnabled(True)

        self.set_controls_enabled(False)
        self.update_result_hint()

        self.tick_timer.start()

    def end_round(self):
        if not self.active:
            return
        self.reset_round_state()

    def on_tick(self):
        if not self.active:
            return

        self.remaining -= 1
        if self.remaining <= 0:
            self.timer_label.setText("00:00")
            self.reset_round_state()
            return

        self.timer_label.setText(mmss(self.remaining))

    def start_assist(self):
        if not self.active:
            return
        self.assist_active = True
        self.assist_remaining = 10
        self.assist_info.setText(f"观众协助剩余 {self.assist_remaining} 秒：可举手给动作提示，但仍不能说出词语中的字。")
        self.assist_timer.start()

    def on_assist_tick(self):
        if not self.assist_active:
            if self.assist_timer.isActive():
                self.assist_timer.stop()
            return

        self.assist_remaining -= 1
        if self.assist_remaining <= 0:
            self.assist_active = False
            self.assist_info.setText("")
            if self.assist_timer.isActive():
                self.assist_timer.stop()
            return

        self.assist_info.setText(f"观众协助剩余 {self.assist_remaining} 秒：可举手给动作提示，但仍不能说出词语中的字。")

    def add_score(self, team: str, delta: int):
        if self.active:
            return

        if team == "A":
            self.score_a = max(0, self.score_a + delta)
        else:
            self.score_b = max(0, self.score_b + delta)

        self.update_scores_ui()
        self.update_result_hint()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
