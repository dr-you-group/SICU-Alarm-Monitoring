import sys
import os
from datetime import datetime, timedelta
from math import sin
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QFrame, QScrollArea,
                             QTableWidget, QTableWidgetItem, QTextEdit, QCheckBox, QDateEdit,
                             QComboBox, QHeaderView, QSplitter, QSizePolicy, QGridLayout,
                             QCalendarWidget)
from PySide6.QtCore import Qt, QDate, QSize, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QBrush

# 상수 정의
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 700
PATIENT_CONTAINER_HEIGHT = 40
TIMELINE_HEIGHT = 40
PATIENT_ID_WIDTH = 300
SEARCH_BUTTON_WIDTH = 120
BOTTOM_CONTAINER_HEIGHT = 80  # 하단 컨테이너 높이 감소
INFO_SECTION_HEIGHT = 40
WAVEFORM_HEIGHT = 300
HEADER_HEIGHT = 25
ID_LABEL_WIDTH = 60
ALARM_BUTTON_WIDTH = 80
SAVE_BUTTON_WIDTH = 60
COMMENT_HEIGHT = 30  # 코멘트 입력 높이 감소
BUTTON_SPACING = 2  # 버튼 사이 간격 더 감소
DATE_PICKER_WIDTH = 120  # 날짜 선택 버튼 너비

# 알람 색상 정의
ALARM_COLORS = {
    "White": "#FFFFFF",
    "SilentCyan": "#00FFFF",
    "Cyan": "#00FFFF",
    "ShortYellow": "#FFFF00",
    "Yellow": "#FFFF00",
    "Red": "#FF0000",
    "None": "#808080"  # 회색으로 기본값 설정
}

# 데모용 알람 데이터
DEMO_ALARMS = {
    "2025-05-01": [
        {"time": "02:15:30", "color": "White"},
        {"time": "05:45:12", "color": "SilentCyan"},
        {"time": "14:22:05", "color": "Yellow"},
        {"time": "19:08:45", "color": "Red"}
    ],
    "2025-05-02": [
        {"time": "01:30:20", "color": "Cyan"},
        {"time": "07:12:43", "color": "ShortYellow"},
        {"time": "12:29:24", "color": "Red"},
        {"time": "18:57:10", "color": "Yellow"}
    ],
    "2025-05-03": [
        {"time": "04:10:15", "color": "White"},
        {"time": "10:25:33", "color": "Red"},
        {"time": "16:45:18", "color": "Red"},
        {"time": "22:05:49", "color": "SilentCyan"}
    ]
}

class TimelineWidget(QWidget):
    # 시그널 정의
    alarmSelected = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(TIMELINE_HEIGHT)
        self.alarms = []  # 알람 데이터 리스트
        self.selected_alarm_index = -1  # 선택된 알람 인덱스
        
    def set_alarms(self, alarms):
        self.alarms = alarms
        self.selected_alarm_index = -1
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # 타임라인 배경
        painter.fillRect(0, 0, width, height, QColor("#2A2A2A"))
        
        # 24시간 마커 그리기 (시간 레이블 없이 선만 표시)
        painter.setPen(QPen(Qt.white, 1, Qt.DotLine))
        for i in range(1, 24):
            x = (width - 10) * (i / 24) + 5
            painter.drawLine(x, 0, x, height)
            
            # 시간 레이블은 상위 레이아웃에서 처리하므로 여기서는 그리지 않음
        
        # 알람 표시
        for i, alarm in enumerate(self.alarms):
            # 시간을 x 좌표로 변환
            time_parts = alarm["time"].split(":")
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds = int(time_parts[2]) if len(time_parts) > 2 else 0
            
            # 24시간 기준으로 x 좌표 계산
            total_seconds = hours * 3600 + minutes * 60 + seconds
            day_seconds = 24 * 3600
            x_pos = 5 + (width - 10) * (total_seconds / day_seconds)
            
            # 알람 색상
            color = alarm["color"]
            if color in ALARM_COLORS:
                alarm_color = QColor(ALARM_COLORS[color])
            else:
                alarm_color = QColor("#808080")  # 기본 회색
                
            # 선택된 알람 강조
            if i == self.selected_alarm_index:
                # 테두리 추가
                painter.setPen(QPen(Qt.white, 2))
                painter.setBrush(QBrush(alarm_color))
                painter.drawRect(x_pos - 6, 5, 12, height - 10)
            else:
                # 일반 알람
                painter.setPen(Qt.transparent)
                painter.setBrush(QBrush(alarm_color))
                painter.drawRect(x_pos - 4, 8, 8, height - 16)
    
    def mousePressEvent(self, event):
        # 클릭된 위치에서 가장 가까운 알람 찾기
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
            if distance < closest_distance and distance < 20:  # 20픽셀 내에서 가장 가까운 알람 선택
                closest_alarm = i
                closest_distance = distance
        
        if closest_alarm != -1:
            self.selected_alarm_index = closest_alarm
            self.update()
            
            # 시그널을 통해 알람 선택 이벤트 발생
            self.alarmSelected.emit(self.alarms[closest_alarm])
            
            print(f"알람 선택됨: {self.alarms[closest_alarm]['color']} ({self.alarms[closest_alarm]['time']})")


class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(WAVEFORM_HEIGHT)
        self.signals = ["ABP", "Lead-II", "Resp", "Pleth"]
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        # 완전히 균등한 4개의 그래프를 그리기 위한 높이 계산
        total_height = self.height()
        signal_height = total_height / len(self.signals)
        
        # 각 신호별 파형 그리기
        for i, signal in enumerate(self.signals):
            # 각 신호의 기준 y 위치 계산 (중앙에 위치)
            y_base = i * signal_height + signal_height / 2
            
            # 신호 레이블 그리기 (왼쪽 정렬)
            painter.drawText(5, y_base + 5, signal)
            
            # 파형 그리기
            pen = QPen(Qt.black, 1.5)
            painter.setPen(pen)
            
            path = QPainterPath()
            path.moveTo(50, y_base)
            
            # 간단한 사인파 생성
            amplitude = signal_height / 4  # 각 신호 영역 높이의 1/4을 진폭으로 사용
            for x in range(50, width - 10, 10):
                # 각 신호마다 다른 주파수 사용
                freq = 0.02 + i * 0.005
                y = y_base + amplitude * sin(x * freq)
                path.lineTo(x, y)
            
            painter.drawPath(path)
            
            # 구분선 그리기
            if i < len(self.signals) - 1:
                painter.setPen(Qt.gray)
                painter.drawLine(0, (i + 1) * signal_height, width, (i + 1) * signal_height)


class SICUMonitoring(QMainWindow):
    def __init__(self):
        super().__init__()
        # 현재 날짜 초기화 (화면에 표시되지 않은 기본값)
        self.current_date = QDate.currentDate()
        self.selected_alarm_color = "None"
        self.has_selected_date = False  # 날짜 선택 여부 플래그
        self.has_selected_alarm = False  # 알람 선택 여부 플래그
        self.initUI()
        self.connectSignals()
        
    def initUI(self):
        self.setWindowTitle("SICU - Monitoring")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.setStyleSheet("background-color: #333333; color: white;")
        
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 환자 정보 섹션
        main_layout.addWidget(self.createPatientInfoSection())
        
        # 선택 알람 & 시간 정보 섹션 (상단으로 이동)
        main_layout.addWidget(self.createAlarmInfoSection())
        
        # 타임라인 섹션
        main_layout.addWidget(self.createTimelineSection())
        
        # 메인 콘텐츠 (파형 & 간호기록)
        main_layout.addWidget(self.createContentSection())
        
        # 하단 섹션 (isAlarm & 코멘트)
        main_layout.addWidget(self.createBottomSection())
        
        # 캘린더 위젯 (초기에는 숨김)
        self.calendar = QCalendarWidget(self)
        self.calendar.setWindowFlags(Qt.Popup)
        self.calendar.setGridVisible(True)
        self.calendar.hide()
        
        # 초기 날짜 버튼 텍스트 설정 ("날짜 선택" 표시)
        self.date_button.setText("날짜 선택")
        
    def createPatientInfoSection(self):
        # 환자 정보 섹션 - 고정 높이 컨테이너
        patient_container = QWidget()
        patient_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        patient_container.setFixedHeight(PATIENT_CONTAINER_HEIGHT)
        
        # 그리드 레이아웃으로 변경하여 요소들 간의 간격 유지
        patient_layout = QGridLayout(patient_container)
        patient_layout.setContentsMargins(0, 0, 0, 0)
        patient_layout.setHorizontalSpacing(5)  # 수평 간격 설정
        
        # 환자 ID 레이블과 입력 필드를 그리드에 배치
        id_label = QLabel("환자 ID:")
        id_label.setFixedWidth(ID_LABEL_WIDTH)  # 레이블 고정 너비
        patient_layout.addWidget(id_label, 0, 0)
        
        self.patient_id = QLineEdit()
        self.patient_id.setText("1160 4980")
        self.patient_id.setFixedWidth(PATIENT_ID_WIDTH)
        patient_layout.addWidget(self.patient_id, 0, 1)
        
        # 정보 불러오기 버튼 (간격 추가)
        self.search_button = QPushButton("정보불러오기")
        self.search_button.setFixedWidth(SEARCH_BUTTON_WIDTH)
        patient_layout.addWidget(self.search_button, 0, 2)
        
        # 입원 기간 레이블과 표시를 그리드에 배치 (간격 추가)
        # 3번 열에 공백 추가하여 간격 확대
        empty_widget = QWidget()
        patient_layout.addWidget(empty_widget, 0, 3)
        patient_layout.setColumnMinimumWidth(3, 30)  # 30픽셀 최소 너비 지정
        
        date_label = QLabel("입원 기간:")
        date_label.setFixedWidth(ID_LABEL_WIDTH + 10)  # 레이블 너비 약간 증가
        patient_layout.addWidget(date_label, 0, 4)
        
        self.date_label = QLabel("24/04/01 — 25/08/09")
        patient_layout.addWidget(self.date_label, 0, 5)
        
        # 빈 공간을 채우는 스트레치 설정
        patient_layout.setColumnStretch(6, 1)  # 마지막 열이 남은 공간을 채우도록
        
        return patient_container
        
    def createAlarmInfoSection(self):
        # 선택 알람 및, 선택 시간 정보 섹션 (상단에 고정)
        info_section = QWidget()
        info_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        info_section.setFixedHeight(INFO_SECTION_HEIGHT)
        info_layout = QHBoxLayout(info_section)
        info_layout.setContentsMargins(5, 0, 5, 0)
        
        # 날짜 선택 버튼 (캘린더 표시용)
        self.date_button = QPushButton("날짜 선택")  # 초기 텍스트는 "날짜 선택"
        self.date_button.setFixedWidth(DATE_PICKER_WIDTH)
        info_layout.addWidget(self.date_button)
        
        # 선택 알람 통합 레이블 (초기에는 비운 내용)
        self.alarm_info_label = QLabel("환자 정보를 불러오고 날짜를 선택해주세요")
        self.alarm_info_label.setStyleSheet("color: #888888; font-size: 14px;")
        
        info_layout.addWidget(self.alarm_info_label)
        info_layout.addStretch()
        
        return info_section
    
    def updateAlarmInfoStyle(self):
        # 선택된 알람 색상으로 레이블 색상 변경
        if self.selected_alarm_color in ALARM_COLORS:
            color = ALARM_COLORS[self.selected_alarm_color]
            self.alarm_info_label.setStyleSheet(f"color: {color};")
    
    def createTimelineSection(self):
        # 타임라인 섹션
        timeline_container = QWidget()
        timeline_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        timeline_container.setFixedHeight(TIMELINE_HEIGHT + 20)  # 좀 더 높게 설정
        
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(5, 0, 5, 0)
        timeline_layout.setSpacing(0)
        
        # 4시간 간격으로 시간 표시하는 레이아웃
        time_markers_layout = QHBoxLayout()
        time_markers_layout.setContentsMargins(5, 0, 5, 0)
        
        # 0h부터 시작하여 4시간 간격으로 시간 마커 추가
        hours = [0, 4, 8, 12, 16, 20]
        for i, hour in enumerate(hours):
            if i > 0:
                time_markers_layout.addStretch(1)
            time_label = QLabel(f"{hour}h")
            time_markers_layout.addWidget(time_label)
        
        # 오른쪽에 24h 표시
        time_markers_layout.addStretch(1)
        self.time_label = QLabel("24h")
        time_markers_layout.addWidget(self.time_label)
        
        # 날짜 레이블 추가 (화면에 표시하지는 않지만 원본 코드의 참조를 유지하기 위해 생성)
        self.day_label = QLabel(self.current_date.toString("dd/MM/yy"))
        self.day_label.setVisible(False)  # 화면에 표시하지 않음
        
        timeline_layout.addLayout(time_markers_layout)
        
        # 타임라인 위젯
        self.timeline_widget = TimelineWidget()
        
        # 알람 선택 시그널 연결
        self.timeline_widget.alarmSelected.connect(self.on_alarm_selected)
        
        timeline_layout.addWidget(self.timeline_widget)
        
        return timeline_container
    
    def createContentSection(self):
        # 메인 콘텐츠 컨테이너
        content_container = QWidget()
        content_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_container.setMinimumHeight(400)
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 메인 스플리터 (3개 패널)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        
        # 좌측 프레임 (파형)
        left_frame = self.createLeftFrame()
        
        # 중앙 프레임 (의료 지표)
        middle_frame = self.createMiddleFrame()
        
        # 우측 프레임 (간호기록)
        right_frame = self.createRightFrame()
        
        # 스플리터에 프레임 추가
        splitter.addWidget(left_frame)
        splitter.addWidget(middle_frame)
        splitter.addWidget(right_frame)
        
        # 크기 비율 설정 - 타임라인과 정확히 일치
        # 0h~12h: 50%, 12h~18h: 25%, 18h~24h: 25%
        
        # 레이아웃에 추가 후 정확한 비율 설정
        content_layout.addWidget(splitter)
        
        # 비율 조정을 위한 명시적 설정
        splitter.setStretchFactor(0, 12)  # 12시간
        splitter.setStretchFactor(1, 6)   # 6시간
        splitter.setStretchFactor(2, 6)   # 6시간
        
        return content_container
    
    def createMiddleFrame(self):
        # 중앙 프레임 (의료 지표 영역)
        middle_frame = QFrame()
        middle_frame.setFrameShape(QFrame.Box)
        middle_frame.setFrameShadow(QFrame.Plain)
        middle_frame.setLineWidth(1)
        middle_layout = QVBoxLayout(middle_frame)
        middle_layout.setContentsMargins(5, 5, 5, 5)
        middle_layout.setSpacing(0)  # 컴포넌트 간 간격 제거
        
        # 헤더 섹션 (Medical Indicators 레이블)
        header_widget = QWidget()
        header_widget.setFixedHeight(HEADER_HEIGHT)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        indicators_label = QLabel("Numueric Data")
        indicators_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_layout.addWidget(indicators_label)
        header_layout.addStretch()
        
        # 헤더와 내용 위젯 사이 구분선
        header_line = QFrame()
        header_line.setFrameShape(QFrame.HLine)
        header_line.setFrameShadow(QFrame.Sunken)
        
        # 날짜와 알람이 선택되지 않았을 때 표시할 안내 레이블
        self.medical_info_label = QLabel("날짜와 알람을 선택하세요")
        self.medical_info_label.setAlignment(Qt.AlignCenter)
        self.medical_info_label.setStyleSheet("color: #888888; font-size: 14px;")
        
        # 의료 지표 테이블
        self.medical_table = QTableWidget(13, 2)
        self.medical_table.setHorizontalHeaderLabels(["항목", "내용"])
        self.medical_table.setStyleSheet("QTableWidget::item { border-bottom: 1px solid #444; }")
        
        medical_items = {
            "ST": "",
            "QTc": "",
            "Tskin": "",
            "ABPs": "",
            "ABPd": "",
            "ABPm": "",
            "NBPPs": "",
            "NBPd": "",
            "Perf": "",
            "SpO2": "",
            "PPV": "",
            "Percent irregular": "",
            "Percent poor signal": ""
        }
        
        for i, (k, v) in enumerate(medical_items.items()):
            item_widget = QTableWidgetItem(k)
            self.medical_table.setItem(i, 0, item_widget)
            content_widget = QTableWidgetItem(v)
            self.medical_table.setItem(i, 1, content_widget)
            
            # 읽기 전용으로 설정
            item_widget.setFlags(item_widget.flags() & ~Qt.ItemIsEditable)
            content_widget.setFlags(content_widget.flags() & ~Qt.ItemIsEditable)
        
        # 첫 번째 열은 고정 너비, 두 번째 열은 늘어남
        self.medical_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.medical_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.medical_table.setColumnWidth(0, 150)  # "항목" 열 고정 너비
        
        self.medical_table.verticalHeader().setVisible(False)
        self.medical_table.setAlternatingRowColors(True)
        self.medical_table.setStyleSheet("alternate-background-color: #2A2A2A;")
        
        # 레이아웃에 헤더, 구분선, 안내 레이블, 테이블 추가
        middle_layout.addWidget(header_widget)
        middle_layout.addWidget(header_line)
        middle_layout.addWidget(self.medical_info_label)
        middle_layout.addWidget(self.medical_table)
        
        # 초기에는 테이블 숨김
        self.medical_table.setVisible(False)
        
        return middle_frame
    
    def createLeftFrame(self):
        # 좌측 프레임 (파형 표시 영역)
        left_frame = QFrame()
        left_frame.setFrameShape(QFrame.Box)
        left_frame.setFrameShadow(QFrame.Plain)
        left_frame.setLineWidth(1)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(0)  # 컴포넌트 간 간격 제거
        
        # 헤더 섹션 (Waveform Signal 레이블)
        header_widget = QWidget()
        header_widget.setFixedHeight(HEADER_HEIGHT)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        waveform_label = QLabel("Waveform Signal")
        waveform_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_layout.addWidget(waveform_label)
        
        # 헤더와 파형 위젯 사이 구분선
        header_line = QFrame()
        header_line.setFrameShape(QFrame.HLine)
        header_line.setFrameShadow(QFrame.Sunken)
        
        # 파형 위젯 추가
        self.waveform_widget = WaveformWidget()
        
        # 날짜와 알람이 선택되지 않았을 때 표시할 안내 레이블
        self.waveform_info_label = QLabel("날짜와 알람을 선택하세요")
        self.waveform_info_label.setAlignment(Qt.AlignCenter)
        self.waveform_info_label.setStyleSheet("color: #888888; font-size: 14px;")
        
        # 레이아웃에 헤더, 구분선, 파형 위젯 추가
        left_layout.addWidget(header_widget)
        left_layout.addWidget(header_line)
        left_layout.addWidget(self.waveform_info_label)
        left_layout.addWidget(self.waveform_widget)
        
        # 초기에는 시그널 화면을 숨김
        self.waveform_widget.setVisible(False)
        
        return left_frame
    
    def createRightFrame(self):
        # 우측 프레임 (간호기록 영역)
        right_frame = QFrame()
        right_frame.setFrameShape(QFrame.Box)
        right_frame.setFrameShadow(QFrame.Plain)
        right_frame.setLineWidth(1)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        # 간호기록 헤더
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Nursing Record"))
        
        header_layout.addStretch()
        
        prev_button = QPushButton("◀")
        prev_button.setFixedSize(30, 25)
        header_layout.addWidget(prev_button)
        
        next_button = QPushButton("▶")
        next_button.setFixedSize(30, 25)
        header_layout.addWidget(next_button)
        
        right_layout.addLayout(header_layout)
        
        # 날짜와 알람이 선택되지 않았을 때 표시할 안내 레이블
        self.record_info_label = QLabel("날짜와 알람을 선택하세요")
        self.record_info_label.setAlignment(Qt.AlignCenter)
        self.record_info_label.setStyleSheet("color: #888888; font-size: 14px;")
        right_layout.addWidget(self.record_info_label)
        
        # 간호기록 테이블: 들
        self.record_table = QTableWidget(26, 2)
        self.record_table.setHorizontalHeaderLabels(["항목", "내용"])
        self.record_table.setStyleSheet("QTableWidget::item { border-bottom: 1px solid #444; }")
        
        items = {
            "간호중재(코드명)": "",
            "간호활동(코드명)": "",
            "간호속성코드(코드명)": "",
            "속성": "",
            "Duty(코드명)": "",
            "시행일시": "",
        }
        
        for i, (k, v) in enumerate(items.items()):
            print('nursing record: ', k, v)
            item_widget = QTableWidgetItem(k)
            self.record_table.setItem(i, 0, item_widget)
            content_widget = QTableWidgetItem(v)
            self.record_table.setItem(i, 1, content_widget)
            
            # 읽기 전용으로 설정
            item_widget.setFlags(item_widget.flags() & ~Qt.ItemIsEditable)
            content_widget.setFlags(content_widget.flags() & ~Qt.ItemIsEditable)
            
        
        # 첫 번째 열은 고정 너비, 두 번째 열은 늘어남
        self.record_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.record_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.record_table.setColumnWidth(0, 150)  # "항목" 열 고정 너비
        
        self.record_table.verticalHeader().setVisible(False)
        self.record_table.setAlternatingRowColors(True)
        self.record_table.setStyleSheet("alternate-background-color: #2A2A2A;")
        
        right_layout.addWidget(self.record_table)
        
        # 초기에는 테이블 숨김
        self.record_table.setVisible(False)
        
        # 이전/다음 버튼 변수 저장
        self.prev_button = prev_button
        self.next_button = next_button
        
        return right_frame
    
    def createBottomSection(self):
        # 하단 컨테이너 - 높이 감소
        bottom_container = QWidget()
        bottom_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom_container.setFixedHeight(BOTTOM_CONTAINER_HEIGHT)
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)  # 간격 감소
        
        # 구분선
        bottom_line = QFrame()
        bottom_line.setFrameShape(QFrame.HLine)
        bottom_line.setFrameShadow(QFrame.Sunken)
        bottom_layout.addWidget(bottom_line)
        
        # 메인 컨테이너 생성
        main_widget = QWidget()
        bottom_layout.addWidget(main_widget)
        
        # 메인 수평 레이아웃 생성
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 5, 10, 5)
        
        # 왼쪽: isAlarm 섹션
        alarm_section = QWidget()
        alarm_section.setFixedWidth(200)  # 너비 고정
        alarm_layout = QVBoxLayout(alarm_section)
        alarm_layout.setContentsMargins(0, 0, 0, 0)
        alarm_layout.setSpacing(3)  # 더 적은 간격
        
        # isAlarm 헤더
        alarm_header = QHBoxLayout()
        alarm_header.setContentsMargins(0, 0, 0, 0)
        alarm_label = QLabel("isAlarm:")
        alarm_header.addWidget(alarm_label)
        
        self.isalarm_status_label = QLabel("None")
        alarm_header.addWidget(self.isalarm_status_label)
        alarm_header.addStretch()
        
        alarm_layout.addLayout(alarm_header)
        
        # isAlarm 버튼들
        alarm_buttons = QHBoxLayout()
        alarm_buttons.setContentsMargins(0, 0, 0, 0)
        alarm_buttons.setSpacing(BUTTON_SPACING)  # 버튼 간격 축소
        
        self.true_button = QPushButton("True")
        self.true_button.setFixedWidth(ALARM_BUTTON_WIDTH)
        
        self.false_button = QPushButton("False")
        self.false_button.setFixedWidth(ALARM_BUTTON_WIDTH)
        
        alarm_buttons.addWidget(self.true_button)
        alarm_buttons.addWidget(self.false_button)
        alarm_buttons.addStretch()
        
        alarm_layout.addLayout(alarm_buttons)
        main_layout.addWidget(alarm_section)
        
        # 중앙: 수직 구분선
        vline = QFrame()
        vline.setFrameShape(QFrame.VLine)
        vline.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(vline)
        
        # 오른쪽: 코멘트 섹션
        comment_section = QWidget()
        comment_layout = QVBoxLayout(comment_section)
        comment_layout.setContentsMargins(0, 0, 0, 0)
        comment_layout.setSpacing(3)  # 더 적은 간격
        
        # 코멘트 헤더
        comment_header = QHBoxLayout()
        comment_header.setContentsMargins(0, 0, 0, 0)
        
        comment_label = QLabel("Comment:")
        comment_header.addWidget(comment_label)
        comment_header.addStretch()
        
        self.submit_button = QPushButton("저장")
        self.submit_button.setFixedWidth(SAVE_BUTTON_WIDTH)
        comment_header.addWidget(self.submit_button)
        
        comment_layout.addLayout(comment_header)
        
        # 코멘트 입력 필드
        self.comment_text = QLineEdit()
        self.comment_text.setFixedHeight(COMMENT_HEIGHT)
        comment_layout.addWidget(self.comment_text)
        
        main_layout.addWidget(comment_section)
        
        # 코멘트 섹션이 확장되도록 설정
        main_layout.setStretch(0, 0)  # isAlarm 섹션 (고정 크기)
        main_layout.setStretch(1, 0)  # 구분선 (고정 크기)
        main_layout.setStretch(2, 1)  # 코멘트 섹션 (확장)
        
        return bottom_container
    
    def connectSignals(self):
        # 시그널 연결
        self.search_button.clicked.connect(self.search_patient)
        self.submit_button.clicked.connect(self.save_comment)
        self.date_button.clicked.connect(self.show_calendar)
        self.calendar.clicked.connect(self.date_selected)
        self.prev_button.clicked.connect(self.prev_record)
        self.next_button.clicked.connect(self.next_record)
        self.true_button.clicked.connect(lambda: self.set_isalarm(True))
        self.false_button.clicked.connect(lambda: self.set_isalarm(False))
    
    def show_calendar(self):
        # 날짜 버튼 위치와 크기를 기준으로 캘린더 팝업 표시
        pos = self.date_button.mapToGlobal(self.date_button.rect().bottomLeft())
        self.calendar.move(pos)
        self.calendar.show()
    
    def date_selected(self, date):
        # 캘린더에서 날짜 선택 시 호출됨
        self.set_date(date)
        self.calendar.hide()
        self.has_selected_date = True  # 날짜 선택 플래그 설정
        
        # 날짜 선택 시 알람 선택 상태 초기화
        self.has_selected_alarm = False
        
        # 컨텐츠 표시 업데이트 (날짜만 선택되고 알람은 선택안됨)
        self.update_content_visibility()
    
    def set_date(self, date):
        # 날짜 설정 및 관련 UI 업데이트
        self.current_date = date
        self.date_button.setText(date.toString("yyyy-MM-dd"))
        self.day_label.setText(date.toString("dd/MM/yy"))  # 표시 형식 변경
        
        # 선택된 날짜에 해당하는 알람 데이터 로드
        self.load_alarm_data_for_date(date)
        
        # 날짜 변경 시 선택된 알람 상태 초기화
        self.has_selected_alarm = False
        self.update_content_visibility()
    
    def load_alarm_data_for_date(self, date):
        # 선택된 날짜에 대한 알람 데이터 로드
        date_str = date.toString("yyyy-MM-dd")
        print(f"날짜 {date_str}의 알람 데이터 로드")
        
        # 데모 데이터에서 알람 정보 가져오기
        alarms = []
        if date_str in DEMO_ALARMS:
            alarms = DEMO_ALARMS[date_str]
        
        # 타임라인 위젯에 알람 데이터 설정
        self.timeline_widget.set_alarms(alarms)
        
        # 날짜 선택 시 기본 알람 정보는 "None"으로 설정 (시간 없이)
        self.update_selected_alarm("None", "")
    
    def on_alarm_selected(self, alarm):
        # 타임라인에서 알람 선택 시 호출됨
        color = alarm["color"]
        time = alarm["time"]
        
        print(f"알람 선택 이벤트: {color} ({time})")
        
        # 선택된 알람 정보 업데이트
        self.update_selected_alarm(color, time)
        
        # 알람 선택 플래그 설정
        self.has_selected_alarm = True
        
        # 날짜와 알람 선택 상태에 따라 콘텐츠 표시 업데이트
        self.update_content_visibility()
        
        # 데이터 로드
        self.load_waveform_data()
        self.load_medical_indicators()
        self.load_nursing_record()
    
    def update_content_visibility(self):
        # 날짜와 알람 선택 상태에 따라 콘텐츠 표시 여부 업데이트
        if self.has_selected_date and self.has_selected_alarm:
            # 날짜와 알람이 모두 선택된 경우, 그래프, 의료지표, 간호기록 표시
            self.waveform_info_label.setVisible(False)
            self.waveform_widget.setVisible(True)
            
            self.medical_info_label.setVisible(False)
            self.medical_table.setVisible(True)
            
            self.record_info_label.setVisible(False)
            self.record_table.setVisible(True)
        else:
            # 날짜나 알람이 선택되지 않은 경우, 안내 메시지 표시
            self.waveform_info_label.setVisible(True)
            self.waveform_widget.setVisible(False)
            
            self.medical_info_label.setVisible(True)
            self.medical_table.setVisible(False)
            
            self.record_info_label.setVisible(True)
            self.record_table.setVisible(False)
    
    def load_waveform_data(self):
        # 선택된 알람에 따라 파형 데이터 로드 (예시 용도)
        print(f"파형 데이터 로드: {self.selected_alarm_color}")
        # 실제 구현에서는 알람과 연관된 파형 데이터 로드
    
    def load_nursing_record(self):
        # 선택된 알람에 따라 간호기록 로드 (예시 용도)
        print(f"간호기록 로드: {self.selected_alarm_color}")
        # 실제 구현에서는 알람과 연관된 간호기록 로드
    
    def load_medical_indicators(self):
        # 선택된 알람에 따라 의료 지표 로드 (예시 용도)
        print(f"의료 지표 로드: {self.selected_alarm_color}")
        # 실제 구현에서는 알람과 연관된 의료 지표 로드
    
    def search_patient(self):
        # 환자 ID로 데이터 검색
        patient_id = self.patient_id.text()
        print(f"환자 검색: {patient_id}")
        
        # 여기서 실제 환자 데이터 로드
        # 예시: 데이터에서 선택된 알람 정보 가져오기
        # 실제 구현에서는 DB 또는 파일에서 데이터 로드
        
        # 새로운 환자 로드 시 날짜 선택 버튼 초기화
        self.date_button.setText("날짜 선택")  # "날짜 선택"으로 다시 변경
        
        # 타임라인 초기화 (비운 알람 리스트로 설정)
        self.timeline_widget.set_alarms([])
        
        # 기본 선택된 알람 정보 초기화 (비운 상태)
        self.alarm_info_label.setText("날짜를 선택해주세요")
        self.alarm_info_label.setStyleSheet("color: #888888; font-size: 14px;")
        
        # 선택 상태 플래그 초기화
        self.has_selected_date = False
        self.has_selected_alarm = False
        
        # 콘텐츠 표시 업데이트
        self.update_content_visibility()
    
    def update_selected_alarm(self, color, time_str):
        # 선택 알람 정보 업데이트
        self.selected_alarm_color = color
        
        # 알람이 선택되지 않은 경우 (색상이 "None")
        if color == "None":
            # 시간 없이 날짜만 표시
            date_str = self.current_date.toString("yyyy-MM-dd")
            self.alarm_info_label.setText(f"선택 알람: None ({date_str})")
        else:
            # 알람이 선택된 경우 날짜와 시간 모두 표시
            date_str = self.current_date.toString("yyyy-MM-dd")
            timestamp = f"{date_str} {time_str}"
            self.alarm_info_label.setText(f"선택 알람: {color} ({timestamp})")
        
        # 스타일 업데이트
        self.updateAlarmInfoStyle()
        
        print(f"선택 알람 정보 업데이트: {color}")
    
    def save_comment(self):
        # 코멘트 저장
        comment = self.comment_text.text()
        print(f"코멘트 저장: {comment}")
        # 여기서 코멘트 저장 로직 구현
    
    def set_isalarm(self, status):
        # isAlarm 값을 True/False로 설정
        status_text = "True" if status else "False"
        self.isalarm_status_label.setText(status_text)
        
        # 상태에 따라 텍스트 색상 변경
        if status:
            self.isalarm_status_label.setStyleSheet("color: red;")
        else:
            self.isalarm_status_label.setStyleSheet("")  # 기본 색상으로 복원
            
        print(f"isAlarm 설정: {status_text}")
    
    def prev_record(self):
        # 이전 기록으로 이동
        print("이전 기록")
        # 이전 기록 탐색 로직 구현
    
    def next_record(self):
        # 다음 기록으로 이동
        print("다음 기록")
        # 다음 기록 탐색 로직 구현


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SICUMonitoring()
    window.show()
    sys.exit(app.exec())
