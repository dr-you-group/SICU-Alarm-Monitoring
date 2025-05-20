import sys
import os
from datetime import datetime, timedelta
from math import sin
import numpy as np
import base64
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QFrame, QScrollArea,
                             QTableWidget, QTableWidgetItem, QTextEdit, QCheckBox, QDateEdit,
                             QComboBox, QHeaderView, QSplitter, QSizePolicy, QGridLayout,
                             QCalendarWidget)
from PySide6.QtCore import Qt, QDate, QSize, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QBrush

from data_structure import patient_data, ALARM_COLORS

WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 700
PATIENT_CONTAINER_HEIGHT = 40
TIMELINE_HEIGHT = 40
PATIENT_ID_WIDTH = 300
SEARCH_BUTTON_WIDTH = 120
BOTTOM_CONTAINER_HEIGHT = 80
INFO_SECTION_HEIGHT = 40
WAVEFORM_HEIGHT = 300
HEADER_HEIGHT = 25
ID_LABEL_WIDTH = 60
ALARM_BUTTON_WIDTH = 80
SAVE_BUTTON_WIDTH = 60
COMMENT_HEIGHT = 30
BUTTON_SPACING = 2
DATE_PICKER_WIDTH = 150
ADMISSION_PICKER_WIDTH = 220

class TimelineWidget(QWidget):
    alarmSelected = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(TIMELINE_HEIGHT)
        self.alarms = []
        self.selected_alarm_index = -1
        
    def set_alarms(self, alarms):
        self.alarms = alarms
        self.selected_alarm_index = -1
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        painter.fillRect(0, 0, width, height, QColor("#2A2A2A"))
        
        painter.setPen(QPen(Qt.white, 1, Qt.DotLine))
        for i in range(1, 24):
            x = (width - 10) * (i / 24) + 5
            painter.drawLine(x, 0, x, height)
            
        for i, alarm in enumerate(self.alarms):
            time_parts = alarm["time"].split(":")
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds = int(time_parts[2]) if len(time_parts) > 2 else 0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            day_seconds = 24 * 3600
            x_pos = 5 + (width - 10) * (total_seconds / day_seconds)
            
            color = alarm["color"]
            if color in ALARM_COLORS:
                alarm_color = QColor(ALARM_COLORS[color])
            else:
                alarm_color = QColor("#808080")
                
            if i == self.selected_alarm_index:
                painter.setPen(QPen(Qt.white, 2))
                painter.setBrush(QBrush(alarm_color))
                painter.drawRect(x_pos - 6, 5, 12, height - 10)
            else:
                painter.setPen(Qt.transparent)
                painter.setBrush(QBrush(alarm_color))
                painter.drawRect(x_pos - 4, 8, 8, height - 16)
    
    def mousePressEvent(self, event):
        click_x = event.position().x()
        width = self.width()
        
        closest_alarm = -1
        closest_distance = float('inf')
        
        for i, alarm in enumerate(self.alarms):
            time_parts = alarm["time"].split(":")
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds = int(time_parts[2]) if len(time_parts) > 2 else 0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            day_seconds = 24 * 3600
            x_pos = 5 + (width - 10) * (total_seconds / day_seconds)
            
            distance = abs(click_x - x_pos)
            if distance < closest_distance and distance < 20:
                closest_alarm = i
                closest_distance = distance
        
        if closest_alarm != -1:
            self.selected_alarm_index = closest_alarm
            self.update()
            
            self.alarmSelected.emit(self.alarms[closest_alarm])
            
            print(f"알람 선택됨: {self.alarms[closest_alarm]['color']} ({self.alarms[closest_alarm]['time']})")


class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(WAVEFORM_HEIGHT)
        self.signals = ["ABP", "Lead-II", "Resp", "Pleth"]
        self.waveform_data = None
        self.decoded_waveforms = {}
        
    def set_waveform_data(self, data):
        self.waveform_data = data
        self.decoded_waveforms = {}
        
        # Base64 데이터 디코딩
        if self.waveform_data:
            for signal in self.signals:
                if signal in self.waveform_data and self.waveform_data[signal]:
                    try:
                        # 문자열이 base64 인코딩된 파형 데이터인 경우 디코딩
                        self.decoded_waveforms[signal] = patient_data.decode_base64_waveform(self.waveform_data[signal])
                    except Exception as e:
                        print(f"Error decoding waveform for {signal}: {e}")
                        self.decoded_waveforms[signal] = np.array([])
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        total_height = self.height()
        signal_height = total_height / len(self.signals)
        
        for i, signal in enumerate(self.signals):
            y_base = i * signal_height + signal_height / 2
            
            painter.drawText(5, y_base + 5, signal)
            
            pen = QPen(Qt.black, 1.5)
            painter.setPen(pen)
            
            path = QPainterPath()
            path.moveTo(50, y_base)
            
            # 디코딩된 파형 데이터 있는 경우
            if signal in self.decoded_waveforms and len(self.decoded_waveforms[signal]) > 0:
                waveform = self.decoded_waveforms[signal]
                points_to_draw = min(len(waveform), width - 60)
                
                if points_to_draw > 0:
                    # 디코딩된 파형의 y값 범위 계산
                    min_val = np.min(waveform)
                    max_val = np.max(waveform)
                    value_range = max(max_val - min_val, 1e-5)  # 0으로 나누기 방지
                    
                    # 화면에 맞게 스케일링
                    scale_factor = signal_height * 0.4 / value_range
                    
                    # 파형 그리기
                    for j in range(points_to_draw):
                        x = 50 + j * ((width - 60) / points_to_draw)
                        # 값을 화면 높이에 맞게 스케일링
                        value_idx = int(j * len(waveform) / points_to_draw)
                        normalized_value = (waveform[value_idx] - min_val) * scale_factor
                        y = y_base - normalized_value
                        
                        if j == 0:
                            path.moveTo(x, y)
                        else:
                            path.lineTo(x, y)
            else:
                # 디코딩된 데이터가 없는 경우 기본 사인파
                amplitude = signal_height / 4
                for x in range(50, width - 10, 10):
                    freq = 0.02 + i * 0.005
                    y = y_base + amplitude * sin(x * freq)
                    path.lineTo(x, y)
            
            painter.drawPath(path)
            
            if i < len(self.signals) - 1:
                painter.setPen(Qt.gray)
                painter.drawLine(0, (i + 1) * signal_height, width, (i + 1) * signal_height)


class SICUMonitoring(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_date = QDate.currentDate()
        self.selected_alarm_color = "None"
        self.has_selected_date = False
        self.has_selected_alarm = False
        self.current_patient_id = ""
        self.current_admission_id = ""
        self.admission_periods = []  # 입원 기간 데이터를 저장
        self.initUI()
        self.connectSignals()
        
    def initUI(self):
        self.setWindowTitle("SICU - Monitoring")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.setStyleSheet("background-color: #333333; color: white;")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        main_layout.addWidget(self.createPatientInfoSection())
        main_layout.addWidget(self.createAlarmInfoSection())
        main_layout.addWidget(self.createTimelineSection())
        main_layout.addWidget(self.createContentSection())
        main_layout.addWidget(self.createBottomSection())
        
    def createPatientInfoSection(self):
        patient_container = QWidget()
        patient_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        patient_container.setFixedHeight(PATIENT_CONTAINER_HEIGHT)
        
        patient_layout = QGridLayout(patient_container)
        patient_layout.setContentsMargins(0, 0, 0, 0)
        patient_layout.setHorizontalSpacing(5)
        
        id_label = QLabel("환자 ID:")
        id_label.setFixedWidth(ID_LABEL_WIDTH)
        patient_layout.addWidget(id_label, 0, 0)
        
        self.patient_id = QLineEdit()
        self.patient_id.setText("1160 4980")
        self.patient_id.setFixedWidth(PATIENT_ID_WIDTH)
        patient_layout.addWidget(self.patient_id, 0, 1)
        
        self.search_button = QPushButton("정보불러오기")
        self.search_button.setFixedWidth(SEARCH_BUTTON_WIDTH)
        patient_layout.addWidget(self.search_button, 0, 2)
        
        # 빈 공간 설정
        patient_layout.setColumnStretch(3, 1)
        
        return patient_container
        
    def createAlarmInfoSection(self):
        info_section = QWidget()
        info_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        info_section.setFixedHeight(INFO_SECTION_HEIGHT)
        info_layout = QHBoxLayout(info_section)
        info_layout.setContentsMargins(5, 0, 5, 0)
        
        # 입원 기간 선택 콤보박스 추가
        admission_label = QLabel("입원 기간:")
        info_layout.addWidget(admission_label)
        
        self.admission_combo = QComboBox()
        self.admission_combo.setFixedWidth(ADMISSION_PICKER_WIDTH)
        self.admission_combo.setEnabled(False)  # 초기에는 비활성화
        info_layout.addWidget(self.admission_combo)
        
        # 날짜 선택 콤보박스
        date_label = QLabel("날짜:")
        info_layout.addWidget(date_label)
        
        self.date_combo = QComboBox()
        self.date_combo.setFixedWidth(DATE_PICKER_WIDTH)
        self.date_combo.setEnabled(False)  # 초기에는 비활성화
        info_layout.addWidget(self.date_combo)
        
        self.alarm_info_label = QLabel("환자 정보를 불러오고 입원 기간과 날짜를 선택해주세요")
        self.alarm_info_label.setStyleSheet("color: #888888; font-size: 14px;")
        
        info_layout.addWidget(self.alarm_info_label)
        info_layout.addStretch()
        
        return info_section
    
    def updateAlarmInfoStyle(self):
        if self.selected_alarm_color in ALARM_COLORS:
            color = ALARM_COLORS[self.selected_alarm_color]
            self.alarm_info_label.setStyleSheet(f"color: {color};")
    
    def createTimelineSection(self):
        timeline_container = QWidget()
        timeline_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        timeline_container.setFixedHeight(TIMELINE_HEIGHT + 20)
        
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(5, 0, 5, 0)
        timeline_layout.setSpacing(0)
        
        time_markers_layout = QHBoxLayout()
        time_markers_layout.setContentsMargins(5, 0, 5, 0)
        
        hours = [0, 4, 8, 12, 16, 20]
        for i, hour in enumerate(hours):
            if i > 0:
                time_markers_layout.addStretch(1)
            time_label = QLabel(f"{hour}h")
            time_markers_layout.addWidget(time_label)
        
        time_markers_layout.addStretch(1)
        self.time_label = QLabel("24h")
        time_markers_layout.addWidget(self.time_label)
        
        self.day_label = QLabel(self.current_date.toString("dd/MM/yy"))
        self.day_label.setVisible(False)
        
        timeline_layout.addLayout(time_markers_layout)
        
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.alarmSelected.connect(self.on_alarm_selected)
        
        timeline_layout.addWidget(self.timeline_widget)
        
        return timeline_container
    
    def createContentSection(self):
        content_container = QWidget()
        content_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_container.setMinimumHeight(400)
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        
        left_frame = self.createLeftFrame()
        right_frame = self.createRightFrame()
        
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        
        splitter.setSizes([300, 200])
        
        content_layout.addWidget(splitter)
        
        return content_container
    
    def createLeftFrame(self):
        left_frame = QFrame()
        left_frame.setFrameShape(QFrame.Box)
        left_frame.setFrameShadow(QFrame.Plain)
        left_frame.setLineWidth(1)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(0)
        
        header_widget = QWidget()
        header_widget.setFixedHeight(HEADER_HEIGHT)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 0, 5, 0)
        
        waveform_label = QLabel("Waveform Signal")
        waveform_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_layout.addWidget(waveform_label)
        
        header_line = QFrame()
        header_line.setFrameShape(QFrame.HLine)
        header_line.setFrameShadow(QFrame.Sunken)
        
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        self.waveform_info_label = QLabel("입원 기간, 날짜, 알람을 모두 선택하세요")
        self.waveform_info_label.setAlignment(Qt.AlignCenter)
        self.waveform_info_label.setStyleSheet("color: #888888; font-size: 14px;")
        
        self.waveform_widget = WaveformWidget()
        
        left_layout.addWidget(header_widget)
        left_layout.addWidget(header_line)
        left_layout.addWidget(content_container, 1)
        
        content_layout.addWidget(self.waveform_info_label)
        content_layout.addWidget(self.waveform_widget)
        
        self.waveform_widget.setVisible(False)
        
        return left_frame
    
    def createRightFrame(self):
        right_frame = QFrame()
        right_frame.setFrameShape(QFrame.Box)
        right_frame.setFrameShadow(QFrame.Plain)
        right_frame.setLineWidth(1)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(0)
        
        header_widget = QWidget()
        header_widget.setFixedHeight(HEADER_HEIGHT)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 0, 5, 0)
        
        nursing_label = QLabel("Nursing Record")
        nursing_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_layout.addWidget(nursing_label)
        header_layout.addStretch()
        
        right_layout.addWidget(header_widget)
        
        header_line = QFrame()
        header_line.setFrameShape(QFrame.HLine)
        header_line.setFrameShadow(QFrame.Sunken)
        right_layout.addWidget(header_line)
        
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(content_container, 1)
        
        self.record_info_label = QLabel("입원 기간, 날짜, 알람을 모두 선택하세요")
        self.record_info_label.setAlignment(Qt.AlignCenter)
        self.record_info_label.setStyleSheet("color: #888888; font-size: 14px;")
        content_layout.addWidget(self.record_info_label)
        
        self.records_scroll_area = QScrollArea()
        self.records_scroll_area.setWidgetResizable(True)
        self.records_scroll_area.setFrameShape(QFrame.NoFrame)
        
        self.records_container = QWidget()
        self.records_layout = QVBoxLayout(self.records_container)
        self.records_layout.setSpacing(10)
        self.records_layout.setAlignment(Qt.AlignTop)
        
        self.records_scroll_area.setWidget(self.records_container)
        content_layout.addWidget(self.records_scroll_area)
        
        self.records_scroll_area.setVisible(False)
        
        return right_frame
    
    def createBottomSection(self):
        bottom_container = QWidget()
        bottom_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom_container.setFixedHeight(BOTTOM_CONTAINER_HEIGHT)
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)
        
        bottom_line = QFrame()
        bottom_line.setFrameShape(QFrame.HLine)
        bottom_line.setFrameShadow(QFrame.Sunken)
        bottom_layout.addWidget(bottom_line)
        
        main_widget = QWidget()
        bottom_layout.addWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 5, 10, 5)
        
        alarm_section = QWidget()
        alarm_section.setFixedWidth(200)
        alarm_layout = QVBoxLayout(alarm_section)
        alarm_layout.setContentsMargins(0, 0, 0, 0)
        alarm_layout.setSpacing(3)
        
        alarm_header = QHBoxLayout()
        alarm_header.setContentsMargins(0, 0, 0, 0)
        alarm_label = QLabel("isAlarm:")
        alarm_header.addWidget(alarm_label)
        
        self.isalarm_status_label = QLabel("None")
        alarm_header.addWidget(self.isalarm_status_label)
        alarm_header.addStretch()
        
        alarm_layout.addLayout(alarm_header)
        
        alarm_buttons = QHBoxLayout()
        alarm_buttons.setContentsMargins(0, 0, 0, 0)
        alarm_buttons.setSpacing(BUTTON_SPACING)
        
        self.true_button = QPushButton("True")
        self.true_button.setFixedWidth(ALARM_BUTTON_WIDTH)
        
        self.false_button = QPushButton("False")
        self.false_button.setFixedWidth(ALARM_BUTTON_WIDTH)
        
        alarm_buttons.addWidget(self.true_button)
        alarm_buttons.addWidget(self.false_button)
        alarm_buttons.addStretch()
        
        alarm_layout.addLayout(alarm_buttons)
        main_layout.addWidget(alarm_section)
        
        vline = QFrame()
        vline.setFrameShape(QFrame.VLine)
        vline.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(vline)
        
        comment_section = QWidget()
        comment_layout = QVBoxLayout(comment_section)
        comment_layout.setContentsMargins(0, 0, 0, 0)
        comment_layout.setSpacing(3)
        
        comment_header = QHBoxLayout()
        comment_header.setContentsMargins(0, 0, 0, 0)
        
        comment_label = QLabel("Comment:")
        comment_header.addWidget(comment_label)
        comment_header.addStretch()
        
        self.submit_button = QPushButton("저장")
        self.submit_button.setFixedWidth(SAVE_BUTTON_WIDTH)
        comment_header.addWidget(self.submit_button)
        
        comment_layout.addLayout(comment_header)
        
        self.comment_text = QLineEdit()
        self.comment_text.setFixedHeight(COMMENT_HEIGHT)
        comment_layout.addWidget(self.comment_text)
        
        main_layout.addWidget(comment_section)
        
        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 0)
        main_layout.setStretch(2, 1)
        
        return bottom_container
    
    def connectSignals(self):
        self.search_button.clicked.connect(self.search_patient)
        self.submit_button.clicked.connect(self.save_comment)
        self.admission_combo.currentIndexChanged.connect(self.admission_selected)
        self.date_combo.currentTextChanged.connect(self.date_selected)
        self.true_button.clicked.connect(lambda: self.set_isalarm(True))
        self.false_button.clicked.connect(lambda: self.set_isalarm(False))
    
    def admission_selected(self, index):
        if index < 0:  # 선택된 항목이 없을 경우
            return
        
        # 선택된 입원 기간 ID 가져오기
        self.current_admission_id = self.admission_combo.itemData(index)
        admission_text = self.admission_combo.currentText()
        
        print(f"입원 기간 선택: {admission_text} (ID: {self.current_admission_id})")
        
        # 선택된 입원 기간의 날짜들 가져오기
        available_dates = patient_data.get_available_dates(self.current_patient_id, self.current_admission_id)
        
        # 날짜 콤보박스 초기화
        self.date_combo.clear()
        
        if available_dates:
            # 날짜 콤보박스에 날짜 추가 (아무것도 선택되지 않은 상태)
            self.date_combo.addItems(available_dates)
            self.date_combo.setCurrentIndex(-1)  # 선택 항목 없음
            
            # 날짜 콤보박스 활성화
            self.date_combo.setEnabled(True)
            
            # 알람 정보 초기화
            self.alarm_info_label.setText("날짜를 선택해주세요")
        else:
            # 사용 가능한 날짜가 없는 경우
            self.date_combo.setEnabled(False)
            self.alarm_info_label.setText("선택된 입원 기간에 알람 데이터가 없습니다")
        
        # 날짜 선택 상태 초기화
        self.has_selected_date = False
        self.has_selected_alarm = False
        
        # 타임라인 초기화
        self.timeline_widget.set_alarms([])
        
        # 컨텐츠 표시 업데이트
        self.update_content_visibility()
    
    def date_selected(self, date_str):
        if not date_str:
            return
            
        self.has_selected_date = True
        
        # 날짜 선택 시 알람 선택 상태 초기화
        self.has_selected_alarm = False
        
        # 선택한 날짜에 대한 알람 데이터 로드
        self.load_alarm_data_for_date(date_str)
        
        # 컨텐츠 표시 업데이트
        self.update_content_visibility()
    
    def load_alarm_data_for_date(self, date_str):
        print(f"날짜 {date_str}의 알람 데이터 로드")
        
        # 데이터 구조에서 알람 정보 가져오기
        alarms = patient_data.get_alarms_for_date(self.current_patient_id, self.current_admission_id, date_str)
        
        # 타임라인 위젯에 알람 데이터 설정
        self.timeline_widget.set_alarms(alarms)
        
        # 날짜 선택 시 기본 알람 정보는 "None"으로 설정
        self.update_selected_alarm("None", "")
    
    def on_alarm_selected(self, alarm):
        color = alarm["color"]
        time = alarm["time"]
        timestamp = alarm.get("timestamp", f"{self.date_combo.currentText()} {time}")
        
        print(f"알람 선택 이벤트: {color} ({time}), 타임스탬프: {timestamp}")
        
        # 선택된 알람 정보 업데이트
        self.update_selected_alarm(color, time, timestamp)
        
        # 알람 선택 플래그 설정
        self.has_selected_alarm = True
        
        # 콘텐츠 표시 업데이트
        self.update_content_visibility()
        
        # 파형 데이터와 간호기록 로드
        self.load_waveform_data(timestamp)
        self.load_nursing_record(timestamp)
    
    def update_content_visibility(self):
        if self.has_selected_date and self.has_selected_alarm:
            self.waveform_info_label.setVisible(False)
            self.waveform_widget.setVisible(True)
            
            self.record_info_label.setVisible(False)
            self.records_scroll_area.setVisible(True)
        else:
            self.waveform_info_label.setVisible(True)
            self.waveform_widget.setVisible(False)
            
            self.record_info_label.setVisible(True)
            self.records_scroll_area.setVisible(False)
    
    def load_waveform_data(self, timestamp):
        print(f"파형 데이터 로드: {timestamp}")
        
        # 데이터 구조에서 파형 데이터 가져오기
        waveform_data = patient_data.get_waveform_data(self.current_patient_id, timestamp)
        
        # 파형 위젯에 데이터 설정
        self.waveform_widget.set_waveform_data(waveform_data)
    
    def load_nursing_record(self, timestamp):
        print(f"간호기록 로드: {timestamp}")
        
        # 기존 간호기록 지우기
        self.clear_nursing_records()
        
        # 데이터 구조에서 선택된 알람 시간 기준 ±30분 범위의 간호기록 가져오기
        records = patient_data.get_nursing_records_for_alarm(self.current_patient_id, timestamp)
        
        # 간호기록 위젯 생성 및 추가
        self.add_nursing_records(records)
    
    def clear_nursing_records(self):
        while self.records_layout.count():
            item = self.records_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def add_nursing_records(self, records):
        for record in records:
            record_widget = self.create_record_widget(record)
            self.records_layout.addWidget(record_widget)
    
    def create_record_widget(self, record):
        record_frame = QFrame()
        record_frame.setFrameShape(QFrame.StyledPanel)
        record_frame.setStyleSheet("background-color: #2A2A2A; border-radius: 5px;")
        
        record_layout = QVBoxLayout(record_frame)
        record_layout.setContentsMargins(10, 10, 10, 10)
        
        fields = [
            "간호중재(코드명)",
            "간호활동(코드명)",
            "간호속성코드(코드명)",
            "속성",
            "Duty(코드명)",
            "시행일시"
        ]
        
        time_label = QLabel(f"시행일시: {record['시행일시']}")
        time_label.setStyleSheet("font-weight: bold; color: #CCCCCC;")
        record_layout.addWidget(time_label)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #444444;")
        record_layout.addWidget(separator)
        
        for field in fields:
            if field != '시행일시':
                item_layout = QHBoxLayout()
                item_layout.setContentsMargins(0, 5, 0, 5)
                
                key_label = QLabel(f"{field}:")
                key_label.setFixedWidth(150)
                key_label.setStyleSheet("color: #AAAAAA;")
                
                value_label = QLabel(record.get(field, ""))
                value_label.setWordWrap(True)
                value_label.setStyleSheet("color: white;")
                
                item_layout.addWidget(key_label)
                item_layout.addWidget(value_label, 1)
                
                record_layout.addLayout(item_layout)
        
        return record_frame
    
    def search_patient(self):
        patient_id = self.patient_id.text()
        print(f"환자 검색: {patient_id}")
        
        # 환자 ID 저장
        self.current_patient_id = patient_id
        
        # 환자 정보 가져오기
        patient_info = patient_data.get_patient_info(patient_id)
        
        if patient_info:
            # 모든 콤보박스 및 안내 텍스트 초기화
            self.clear_ui_selections()
            
            # 입원 기간 콤보박스 초기화
            self.admission_combo.clear()
            
            # 입원 기간 가져오기
            admission_periods = patient_data.get_admission_periods(patient_id)
            
            # 입원 기간 콤보박스에 항목 추가 (아무것도 선택되지 않은 상태)
            for period in admission_periods:
                period_text = f"{period['start']} ~ {period['end']}"
                self.admission_combo.addItem(period_text, period['id'])
            
            # 아무 항목도 선택되지 않은 상태로 설정
            self.admission_combo.setCurrentIndex(-1)
            
            # 입원 기간 콤보박스 활성화
            self.admission_combo.setEnabled(True)
            
            # 알람 정보 텍스트 업데이트
            self.alarm_info_label.setText("입원 기간을 선택해주세요")
            self.alarm_info_label.setStyleSheet("color: #888888; font-size: 14px;")
            
            # 날짜 콤보박스 비활성화 (입원 기간 선택 전)
            self.date_combo.clear()
            self.date_combo.setEnabled(False)
        else:
            # 환자 정보가 없는 경우
            self.clear_ui_selections()
            self.alarm_info_label.setText("환자 정보를 찾을 수 없습니다")
    
    def clear_ui_selections(self):
        """UI 선택 항목 및 상태 초기화"""
        # 입원 기간 콤보박스 비활성화 및 초기화
        self.admission_combo.clear()
        self.admission_combo.setEnabled(False)
        
        # 날짜 콤보박스 비활성화 및 초기화
        self.date_combo.clear()
        self.date_combo.setEnabled(False)
        
        # 선택 상태 플래그 초기화
        self.has_selected_date = False
        self.has_selected_alarm = False
        self.current_admission_id = ""
        
        # 타임라인 초기화
        self.timeline_widget.set_alarms([])
        
        # 콘텐츠 표시 업데이트
        self.update_content_visibility()
    
    def update_selected_alarm(self, color, time_str, timestamp=None):
        self.selected_alarm_color = color
        
        if color == "None":
            if self.date_combo.currentText():
                self.alarm_info_label.setText(f"선택 알람: None ({self.date_combo.currentText()})")
            else:
                self.alarm_info_label.setText("날짜를 선택해주세요")
        else:
            if timestamp:
                self.alarm_info_label.setText(f"선택 알람: {color} ({timestamp})")
            else:
                date_str = self.date_combo.currentText()
                self.alarm_info_label.setText(f"선택 알람: {color} ({date_str} {time_str})")
        
        self.updateAlarmInfoStyle()
        
        print(f"선택 알람 정보 업데이트: {color}")
    
    def save_comment(self):
        comment = self.comment_text.text()
        print(f"코멘트 저장: {comment}")
    
    def set_isalarm(self, status):
        status_text = "True" if status else "False"
        self.isalarm_status_label.setText(status_text)
        
        if status:
            self.isalarm_status_label.setStyleSheet("color: red;")
        else:
            self.isalarm_status_label.setStyleSheet("")
            
        print(f"isAlarm 설정: {status_text}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SICUMonitoring()
    window.show()
    sys.exit(app.exec())
