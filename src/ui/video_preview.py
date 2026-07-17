import os
import sys
import platform
import re
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSlider)

class VideoPreviewWidget(QWidget):
    """
    高度集成的跨平台音视频及图片混合预览通用控件。
    自动根据文件扩展名切换预览布局（图片渲染 vs 视频播放控制）。
    """
    
    # 支持的常见扩展名
    IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
    VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.ts'}

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化多媒体引擎
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5) # 默认50%音量
        
        self.current_file_path = ""
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # 整体主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(8)
        
        # 1. 图片与默认提示文本展示标签 (QLabel)
        self.preview_label = QLabel("选择文件后在此预览")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(320)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #888888;
                font-size: 13px;
                padding: 8px;
            }
        """)
        self.preview_label.setWordWrap(True)
        self.preview_label.setScaledContents(False)
        self.main_layout.addWidget(self.preview_label, 1)
        
        # 2. 视频渲染视窗 (QVideoWidget)
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(320)
        self.video_widget.setStyleSheet("background-color: #000000; border-radius: 4px;")
        self.player.setVideoOutput(self.video_widget)
        self.main_layout.addWidget(self.video_widget, 1)
        self.video_widget.hide() # 默认隐藏
        
        # 3. 播放控制栏容器 (QWidget)
        self.control_container = QWidget()
        control_layout = QHBoxLayout(self.control_container)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(6)
        
        # 播放/暂停按钮
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedWidth(35)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                color: white;
                font-size: 12px;
                min-width: 35px;
                padding: 4px;
            }
            QPushButton:hover { background-color: #505050; }
        """)
        control_layout.addWidget(self.play_btn)
        
        # 进度滑块
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 6px;
                background: #2b2b2b;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #0078d4;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #555555;
                width: 12px;
                margin-top: -3px;
                margin-bottom: -3px;
                border-radius: 6px;
            }
        """)
        control_layout.addWidget(self.slider)
        
        # 时间文字标签
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("border: none; background: transparent; color: #cccccc; font-size: 11px; padding: 0px;")
        control_layout.addWidget(self.time_label)
        
        # 静音/音量按钮
        self.volume_btn = QPushButton("🔊")
        self.volume_btn.setFixedWidth(35)
        self.volume_btn.setStyleSheet(self.play_btn.styleSheet())
        control_layout.addWidget(self.volume_btn)
        
        self.main_layout.addWidget(self.control_container)
        self.control_container.hide() # 默认隐藏

    def _connect_signals(self):
        # 绑定播放按钮
        self.play_btn.clicked.connect(self._toggle_play)
        
        # 播放状态改变时更新按钮文本 (▶ / ⏸)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        
        # 进度与总时长监听
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        
        # 拖拽滑块跳过进度
        self.slider.sliderMoved.connect(self._on_slider_moved)
        
        # 静音开关
        self.volume_btn.clicked.connect(self._toggle_mute)

    # ── 内部槽函数与逻辑实现 ──
    
    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setText("⏸")
        else:
            self.play_btn.setText("▶")

    def _format_time(self, ms):
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"

    def _on_duration_changed(self, duration):
        self.slider.setRange(0, duration)
        self._update_time_label(self.player.position(), duration)

    def _on_position_changed(self, position):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self._update_time_label(position, self.player.duration())

    def _update_time_label(self, pos, dur):
        self.time_label.setText(f"{self._format_time(pos)} / {self._format_time(dur)}")

    def _on_slider_moved(self, pos):
        self.player.setPosition(pos)

    def _toggle_mute(self):
        if self.audio_output.isMuted():
            self.audio_output.setMuted(False)
            self.volume_btn.setText("🔊")
        else:
            self.audio_output.setMuted(True)
            self.volume_btn.setText("🔇")

    # ── 外部核心公开接口 ──

    def show_file(self, fpath: str):
        """
        加载并展示指定文件的预览。
        如果是图片，渲染图片并关闭播放器；
        如果是视频，显示渲染视窗、播放控制栏并开始播放。
        """
        self.stop()
        self.current_file_path = fpath
        
        if not fpath or not os.path.exists(fpath):
            self.clear("⚠️ 文件不存在，无法加载预览")
            return

        ext = os.path.splitext(fpath)[1].lower()
        
        # 处理图片预览模式
        if ext in self.IMAGE_EXTS:
            self.video_widget.hide()
            self.control_container.hide()
            self.preview_label.show()
            
            # 计算适合的比率缩放尺寸，防止图片撑大布局
            w = max(self.preview_label.width() - 8, 260)
            h = max(self.preview_label.height() - 8, 300)
            
            pix = QPixmap(fpath)
            if not pix.isNull():
                scaled = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled)
                self.preview_label.setText("")
            else:
                self.preview_label.setPixmap(QPixmap())
                self.preview_label.setText("❌ 无法加载图片，文件可能损坏")
                
        # 处理视频预览模式
        elif ext in self.VIDEO_EXTS:
            self.preview_label.hide()
            self.video_widget.show()
            self.control_container.show()
            
            # 异步加载媒体并播放
            self.player.setSource(QUrl.fromLocalFile(fpath))
            self.player.play()
            
        # 处理不支持的文件格式
        else:
            self.video_widget.hide()
            self.control_container.hide()
            self.preview_label.show()
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"📄 不支持直接预览的文件格式：\n{os.path.basename(fpath)}")

    def stop(self):
        """停止音视频播放器，完全断开媒体流并释放底层软解码资源"""
        self.player.stop()

    def clear(self, default_text="选择文件后在此预览"):
        """恢复为初始状态"""
        self.stop()
        self.current_file_path = ""
        self.video_widget.hide()
        self.control_container.hide()
        self.preview_label.show()
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(default_text)
