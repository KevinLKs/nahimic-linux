"""Nahimic desktop control panel."""
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import os
from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import QTimer, Qt, QLockFile
from PySide6.QtGui import QIcon, QFont
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QCheckBox, QSlider, QTabWidget, QFrame)
from backend import Backend, DATA, PROFILES

STYLE = """
QWidget { background: #111b2d; color: #e6edf8; font-family: 'Noto Sans CJK SC'; font-size: 14px; }
QLabel#brand { color: #6dd8dc; font-size: 15px; font-weight: 700; letter-spacing: 3px; }
QLabel#title { font-size: 30px; font-weight: 700; }
QLabel#muted, QLabel#foot { color: #92a6c3; }
QLabel#value { color: #6dd8dc; font-family: 'DejaVu Sans Mono'; font-size: 22px; }
QFrame#card { background: #182740; border: 1px solid #2a3d59; border-radius: 10px; }
QFrame#card QLabel, QFrame#card QCheckBox, QFrame#card QWidget { background: transparent; }
QPushButton { background: #20324e; border: 1px solid #354b69; padding: 11px 18px; border-radius: 7px; }
QPushButton:hover { border-color: #6dd8dc; }
QPushButton:checked { background: #28566a; color: #a4f6f4; border-color: #6dd8dc; }
QPushButton:disabled, QCheckBox:disabled { color: #607089; }
QPushButton:focus { border: 2px solid #b6f5f5; }
QTabWidget::pane { border: 0; }
QTabBar::tab { background: #111b2d; color: #92a6c3; padding: 12px 22px; border-bottom: 2px solid #2a3d59; }
QTabBar::tab:selected { color: #6dd8dc; border-bottom-color: #6dd8dc; }
QSlider::groove:horizontal { background: #354b69; height: 5px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #6dd8dc; border-radius: 2px; }
QSlider::handle:horizontal { background: #e6edf8; width: 16px; margin: -6px 0; border-radius: 8px; }
QSlider::groove:vertical { background: #354b69; width: 5px; border-radius: 2px; }
QSlider::handle:vertical { background: #6dd8dc; height: 15px; margin: 0 -5px; border-radius: 6px; }
QCheckBox { spacing: 9px; padding: 5px 0; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #607089; border-radius: 4px; }
QCheckBox::indicator:checked { background: #6dd8dc; border-color: #6dd8dc; image: none; }
"""


class ControlSlider(QSlider):
    def keyReleaseEvent(self, event):
        super().keyReleaseEvent(event)
        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                           Qt.Key_PageUp, Qt.Key_PageDown, Qt.Key_Home, Qt.Key_End):
            self.sliderReleased.emit()


class Panel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.backend = Backend()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pending = None
        self.jobs = deque()
        self.settings_loaded = False
        self.loaded_pid = None
        self.setWindowTitle("Nahimic 音效")
        self.setWindowIcon(QIcon(str(Path(__file__).with_name("nahimic.svg"))))
        self.resize(940, 730)
        self.setMinimumSize(820, 680)
        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central); layout.setContentsMargins(32, 25, 32, 22); layout.setSpacing(20)
        brand = QLabel("NAHIMIC  /  AUDIO CONTROL"); brand.setObjectName("brand"); layout.addWidget(brand)
        top = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("让声音更有层次"); title.setObjectName("title"); titles.addWidget(title)
        subtitle = QLabel("内置扬声器 · MECHREVO · SN6140"); subtitle.setObjectName("muted"); titles.addWidget(subtitle)
        top.addLayout(titles); top.addStretch()
        self.power = QPushButton("正在连接…"); self.power.setCheckable(True); self.power.setMinimumWidth(160)
        self.power.clicked.connect(lambda checked: self.submit(lambda: self.backend.enabled(checked), "state"))
        top.addWidget(self.power); layout.addLayout(top)
        self.controls = QWidget(); controls_layout = QVBoxLayout(self.controls); controls_layout.setContentsMargins(0,0,0,0); controls_layout.setSpacing(18)
        layout.addWidget(self.controls)
        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("扬声器音量"))
        self.volume = ControlSlider(Qt.Horizontal); self.volume.setRange(0,100)
        self.volume.sliderReleased.connect(lambda: self.submit(lambda v=self.volume.value(): self.backend.volume(v), "state"))
        self.volume_value = QLabel("—"); self.volume_value.setFixedWidth(50)
        self.volume.valueChanged.connect(lambda value: self.volume_value.setText(f"{value}%"))
        self.mute = QCheckBox("静音"); self.mute.clicked.connect(lambda checked: self.submit(lambda: self.backend.mute(checked), "state"))
        volume_row.addWidget(self.volume,1); volume_row.addWidget(self.volume_value); volume_row.addWidget(self.mute)
        controls_layout.addLayout(volume_row)
        modes = QHBoxLayout(); self.modes = {}
        for name,(label,_) in PROFILES.items():
            button = QPushButton(label); button.setCheckable(True); button.setMinimumHeight(48)
            button.clicked.connect(lambda checked=False,n=name: self.submit(lambda: self.backend.profile(n), "settings"))
            modes.addWidget(button); self.modes[name] = button
        controls_layout.addLayout(modes)
        tabs = QTabWidget(); controls_layout.addWidget(tabs)
        effects = QWidget(); effects_layout = QVBoxLayout(effects); effects_layout.setContentsMargins(0,18,0,0); effects_layout.setSpacing(18)
        tabs.addTab(effects,"音效")
        cards = QHBoxLayout(); cards.setSpacing(16); effects_layout.addLayout(cards)
        self.values = {}; self.switches = {}
        for title, hint, state, gain in (
            ("低音", "增加低频的厚度", "kSet_BassBoostState", "kSet_BassBoostGainDB"),
            ("人声", "让对白与歌声更清晰", "kSet_VoiceBoostState", "kSet_VoiceBoostGainDB"),
            ("高音", "突出明亮的细节", "kSet_TrebleBoostState", "kSet_TrebleBoostGainDB")):
            card = QFrame(); card.setObjectName("card"); column = QVBoxLayout(card); column.setContentsMargins(20,20,20,22); column.setSpacing(18)
            enabled = QCheckBox(title); enabled.clicked.connect(lambda checked,n=state: self.submit(lambda: self.backend.set_setting(n,int(checked)),"settings"))
            self.switches[state] = enabled; column.addWidget(enabled)
            label = QLabel("— dB"); label.setObjectName("value"); column.addWidget(label)
            slider = ControlSlider(Qt.Horizontal)
            slider.valueChanged.connect(lambda v,l=label:l.setText(f"{v:+d} dB"))
            slider.sliderReleased.connect(lambda n=gain,s=slider:self.submit(lambda v=s.value():self.backend.set_setting(n,v),"settings"))
            self.values[gain] = slider; column.addWidget(slider)
            note = QLabel(hint); note.setObjectName("muted"); column.addWidget(note)
            cards.addWidget(card,1)
        extra = QHBoxLayout()
        for name,title in (("kSet_SpkVirtualSurroundState","扬声器虚拟环绕"),("kSet_CompressorState","动态压缩")):
            button=QCheckBox(title);button.clicked.connect(lambda checked,n=name:self.submit(lambda:self.backend.set_setting(n,int(checked)),"settings"))
            self.switches[name]=button;extra.addWidget(button)
        effects_layout.addLayout(extra)
        effects_layout.addStretch()
        eq=QWidget(); eq_layout=QVBoxLayout(eq);eq_layout.setContentsMargins(4,18,4,6);tabs.addTab(eq,"均衡器")
        switch=QCheckBox("启用均衡器");switch.clicked.connect(lambda checked:self.submit(lambda:self.backend.set_setting("kSet_EQState",int(checked)),"settings"))
        self.switches['kSet_EQState']=switch;eq_layout.addWidget(switch)
        bands=QHBoxLayout();eq_layout.addLayout(bands)
        for band,label in (("31Hz","31"),("62Hz","62"),("125Hz","125"),("250Hz","250"),("500Hz","500"),("1kHz","1k"),("2kHz","2k"),("4kHz","4k"),("8kHz","8k"),("16kHz","16k")):
            name="kSet_EQ"+band+"GainDB";column=QVBoxLayout();column.setAlignment(Qt.AlignHCenter)
            value=QLabel("0 dB");value.setAlignment(Qt.AlignCenter);column.addWidget(value)
            slider=ControlSlider(Qt.Vertical);slider.setMinimumHeight(145)
            slider.valueChanged.connect(lambda v,l=value:l.setText(f"{v:+d} dB"))
            slider.sliderReleased.connect(lambda n=name,s=slider:self.submit(lambda v=s.value():self.backend.set_setting(n,v),"settings"))
            column.addWidget(slider,1,Qt.AlignHCenter);frequency=QLabel(label+" Hz");frequency.setAlignment(Qt.AlignCenter);column.addWidget(frequency);bands.addLayout(column,1);self.values[name]=slider
        settings=QWidget();sl=QVBoxLayout(settings);sl.setContentsMargins(4,22,4,6);tabs.addTab(settings,"设置")
        self.auto=QCheckBox("登录后自动运行音效");self.auto.clicked.connect(lambda checked:self.submit(lambda:self.backend.autostart(checked),"state"));sl.addWidget(self.auto)
        note=QLabel("关闭窗口后，音效会继续运行。\n音效开关、模式和参数会自动保存。\n\n当前适配：本机内置扬声器");note.setObjectName("muted");sl.addWidget(note);sl.addStretch()
        layout.addStretch()
        self.status=QLabel("正在连接音效服务…");self.status.setWordWrap(True);layout.addWidget(self.status)
        foot=QLabel("NAHIMIC LINUX  ·  0.1.0");foot.setObjectName("foot");layout.addWidget(foot)
        self.controls.setEnabled(False);self.power.setEnabled(False)
        self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(100)
        self.status_timer=QTimer(self);self.status_timer.timeout.connect(self.refresh);self.status_timer.start(2000)
        self.refresh()

    def submit(self, function, kind):
        if self.pending:
            if kind != 'status': self.jobs.append((function,kind))
            return
        self.pending=(self.pool.submit(function),kind)
        if kind != 'status':
            self.controls.setEnabled(False);self.power.setEnabled(False)
            self.status.setText("正在应用…")

    def refresh(self):
        if not self.pending:
            if self.jobs:self.submit(*self.jobs.popleft())
            else:self.submit(self.backend.status,'status')

    def poll(self):
        if not self.pending or not self.pending[0].done():return
        future,kind=self.pending;self.pending=None
        try:
            result=future.result()
            if kind=='settings':
                self.apply_settings(result);self.refresh()
            elif kind=='state':self.refresh()
            else:
                ready=result['ready']
                if ready and result['instance'] != self.loaded_pid:
                    self.loaded_pid=result['instance'];self.settings_loaded=False
                self.power.setEnabled(ready)
                self.controls.setEnabled(ready and self.settings_loaded)
                self.auto.setChecked(result['autostart'])
                if ready:
                    self.power.setChecked(result['enabled']);self.power.setText("音效已开启" if result['enabled'] else "原声 · 音效已关闭")
                    if not self.volume.isSliderDown():self.volume.setValue(result['volume'])
                    self.mute.setChecked(result['muted'])
                    self.status.setText("正在使用原厂音效" if result['active'] else "正在播放原声" if not result['enabled'] else "音效已开启，请选择 Nahimic Speakers 输出")
                    if not self.settings_loaded:self.submit(self.backend.settings,'settings')
                else:
                    self.settings_loaded=False;self.power.setText("等待音效服务")
                    self.status.setText("正在准备音效，请稍候…" if result['service'] in ('active','activating') else "音效服务未运行，请关闭并重新打开软件。")
        except Exception as error:
            self.status.setText("操作未完成："+str(error))
            self.controls.setEnabled(self.settings_loaded);self.power.setEnabled(self.settings_loaded)
        if not self.pending and self.jobs:self.submit(*self.jobs.popleft())

    def apply_settings(self,state):
        for name,button in self.modes.items():button.setChecked(name==state['profile'])
        for name,slider in self.values.items():
            item=state['settings'][name];slider.setRange(round(item['min']),round(item['max']));slider.setValue(round(item['value']))
        for name,switch in self.switches.items():switch.setChecked(bool(state['settings'][name]['value']))
        self.settings_loaded=True


def main():
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
    runtime=Path(os.environ['XDG_RUNTIME_DIR']);lock=QLockFile(str(runtime/'nahimic-panel.lock'))
    socket_name=str(runtime/'nahimic-panel.socket')
    if not lock.tryLock(0):
        socket=QLocalSocket();socket.connectToServer(socket_name)
        if not socket.waitForConnected(1000):raise RuntimeError("音效窗口已运行，但无法联系窗口")
        socket.write(b'show');socket.waitForBytesWritten(1000)
        return
    QLocalServer.removeServer(socket_name);server=QLocalServer()
    if not server.listen(socket_name):raise RuntimeError(server.errorString())
    subprocess.run(['systemctl','--user','start','nahimic.service'],check=True,timeout=15)
    panel=Panel()
    def activate():
        connection=server.nextPendingConnection();connection.close();connection.deleteLater()
        panel.settings_loaded=False
        panel.showNormal();panel.raise_();panel.activateWindow()
    server.newConnection.connect(activate)
    panel.show();app.exec();panel.pool.shutdown(wait=True,cancel_futures=True)


if __name__=='__main__':main()
