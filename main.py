import sys
import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QFrame, QScrollArea,
                             QTableWidget, QTableWidgetItem, QTextEdit, QCheckBox, QDateEdit,
                             QComboBox, QHeaderView, QSplitter, QSizePolicy, QGridLayout,
                             QCalendarWidget, QDialog, QListWidget, QListWidgetItem,
                             QDialogButtonBox, QMenu)
from PySide6.QtCore import Qt, QDate, QSize, QRect, QPoint, Signal, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QBrush, QAction

from data_structure import patient_data, ALARM_COLORS

# 분리된 컴포넌트들 import
from components.csv_manager import CSVManager
from components.waveform_manager import WaveformWidget, WaveformManager
from components.nursing_record_manager import NursingRecordManager
from components.patient_data_manager import TimelineWidget, PatientDataManager

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

class SICUMonitoring(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_date = QDate.currentDate()
        self.current_alarm_id = ""  # 현재 선택된 알람 ID
        
        # 분리된 컴포넌트 관리자들
        self.csv_manager = CSVManager("alarm_annotations.csv")
        self.waveform_manager = None  # UI 생성 후 초기화
        self.nursing_manager = None   # UI 생성 후 초기화
        self.patient_manager = None   # UI 생성 후 초기화
        
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
        
        main_layout.addWidget(self.createPatientAndAlarmInfoSection())  # 통합 섹션
        main_layout.addWidget(self.createTimelineSection())
        main_layout.addWidget(self.createContentSection())
        main_layout.addWidget(self.createBottomSection())
        
        # 컴포넌트 관리자들 초기화 (UI 생성 후)
        self.waveform_manager = WaveformManager(
            self.waveform_widget, self.waveform_info_label,
            self.numeric_table, self.numeric_info_label
        )
        self.nursing_manager = NursingRecordManager(self.nursing_table, self.record_info_label, self)
        self.patient_manager = PatientDataManager(
            self.patient_id, self.admission_combo, self.date_combo, 
            self.alarm_info_label, self.timeline_widget
        )
        
    def createPatientAndAlarmInfoSection(self):
        """환자 정보와 알람 정보를 통합한 섹션 (우측에 Numeric 데이터 테이블)"""
        info_section = QWidget()
        info_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        info_section.setFixedHeight(240)  # Numeric 데이터 섹션 높이 증가에 맞춰 조정 (160 -> 240)
        info_layout = QHBoxLayout(info_section)
        info_layout.setContentsMargins(5, 5, 5, 5)
        info_layout.setSpacing(15)
        
        # 왼쪽: 환자 정보 + 알람 정보
        left_container = QWidget()
        left_container.setMinimumWidth(600)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # 첫 번째 행: 환자 ID
        patient_row = QWidget()
        patient_layout = QHBoxLayout(patient_row)
        patient_layout.setContentsMargins(0, 0, 0, 0)
        patient_layout.setSpacing(10)
        
        id_label = QLabel("환자 ID:")
        id_label.setFixedWidth(ID_LABEL_WIDTH)
        patient_layout.addWidget(id_label)
        
        self.patient_id = QLineEdit()
        self.patient_id.setText("11604980")
        self.patient_id.setFixedWidth(PATIENT_ID_WIDTH)
        patient_layout.addWidget(self.patient_id)
        
        self.search_button = QPushButton("정보불러오기")
        self.search_button.setFixedWidth(SEARCH_BUTTON_WIDTH)
        patient_layout.addWidget(self.search_button)
        
        patient_layout.addStretch()
        left_layout.addWidget(patient_row)
        
        # 두 번째 행: 입원기간 및 날짜 선택
        admission_row = QWidget()
        admission_layout = QHBoxLayout(admission_row)
        admission_layout.setContentsMargins(0, 0, 0, 0)
        admission_layout.setSpacing(10)
        
        admission_label = QLabel("입원 기간:")
        admission_layout.addWidget(admission_label)
        
        self.admission_combo = QComboBox()
        self.admission_combo.setFixedWidth(ADMISSION_PICKER_WIDTH)
        self.admission_combo.setEnabled(False)
        admission_layout.addWidget(self.admission_combo)
        
        date_label = QLabel("날짜:")
        admission_layout.addWidget(date_label)
        
        self.date_combo = QComboBox()
        self.date_combo.setFixedWidth(DATE_PICKER_WIDTH)
        self.date_combo.setEnabled(False)
        admission_layout.addWidget(self.date_combo)
        
        admission_layout.addStretch()
        left_layout.addWidget(admission_row)
        
        # 세 번째 행: 알람 정보
        self.alarm_info_label = QLabel("환자 정보를 불러오고 입원 기간과 날짜를 선택해주세요")
        self.alarm_info_label.setStyleSheet("color: #888888; font-size: 14px;")
        left_layout.addWidget(self.alarm_info_label)
        
        # 남은 공간 채우기
        left_layout.addStretch()
        
        info_layout.addWidget(left_container)
        
        # 오른쪽: Numeric 데이터 테이블
        numeric_container = self.createNumericDataSection()
        info_layout.addWidget(numeric_container)
        
        return info_section
    
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
        
        # 간호기록 테이블 (엑셀 스타일)
        self.nursing_table = QTableWidget()
        self.nursing_table.setAlternatingRowColors(True)
        self.nursing_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.nursing_table.setStyleSheet("""
            QTableWidget {
                background-color: #2A2A2A;
                color: white;
                gridline-color: #444444;
                border: 1px solid #444444;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #444444;
            }
            QTableWidget::item:selected {
                background-color: #3A3A3A;
            }
            QHeaderView::section {
                background-color: #1A1A1A;
                color: white;
                padding: 5px;
                border: 1px solid #444444;
                font-weight: bold;
            }
        """)
        
        content_layout.addWidget(self.nursing_table)
        
        # 초기에는 테이블 숨김
        self.nursing_table.setVisible(False)
        
        return right_frame
    
    def createNumericDataSection(self):
        """Numeric 데이터 섹션 생성 - 우측 상단에 배치 (8개 파라미터 모두 표시)"""
        numeric_container = QWidget()
        numeric_container.setFixedWidth(400)  # 고정 너비
        numeric_container.setFixedHeight(220)  # 8개 행이 모두 보이도록 높이 증가 (150 -> 220)
        
        numeric_layout = QVBoxLayout(numeric_container)
        numeric_layout.setContentsMargins(5, 2, 5, 2)  # 위아래 여백 줄임
        numeric_layout.setSpacing(1)  # 간격 줄임
        
        # 헤더
        numeric_label = QLabel("Numeric Data")
        numeric_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        numeric_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 2px;")  # 폰트 크기 증가
        numeric_layout.addWidget(numeric_label)
        
        # Numeric 데이터 정보 라벨 (크기 줄임)
        self.numeric_info_label = QLabel("알람 선택 시 표시")
        self.numeric_info_label.setAlignment(Qt.AlignCenter)
        self.numeric_info_label.setStyleSheet("color: #888888; font-size: 10px; margin: 2px;")  # 폰트 크기 증가
        numeric_layout.addWidget(self.numeric_info_label)
        
        # Numeric 데이터 테이블 (8개 파라미터가 모두 보이도록)
        self.numeric_table = QTableWidget()
        self.numeric_table.setColumnCount(2)
        self.numeric_table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.numeric_table.setAlternatingRowColors(True)
        self.numeric_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # 8행으로 고정 설정 (스크롤 없이 모두 보이도록)
        self.numeric_table.setRowCount(8)
        
        # 테이블 스타일 (극도로 컴팩트하게 조정)
        self.numeric_table.setStyleSheet("""
            QTableWidget {
                background-color: #2A2A2A;
                color: white;
                gridline-color: #444444;
                border: 1px solid #444444;
            }
            QTableWidget::item {
                padding: 3px;
                border-bottom: 1px solid #444444;
                font-size: 11px;  /* 폰트 크기 증가 */
                margin: 0px;
            }
            QTableWidget::item:selected {
                background-color: #3A3A3A;
            }
            QHeaderView::section {
                background-color: #1A1A1A;
                color: white;
                padding: 3px;
                border: 1px solid #444444;
                font-weight: bold;
                font-size: 10px;  /* 헤더 폰트 크기 증가 */
                margin: 0px;
            }
        """)
        
        # 컬럼 크기 조정
        numeric_header_view = self.numeric_table.horizontalHeader()
        numeric_header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        numeric_header_view.setSectionResizeMode(1, QHeaderView.Stretch)
        # 헤더 높이 조정
        numeric_header_view.setMinimumSectionSize(15)
        numeric_header_view.setDefaultSectionSize(20)
        
        # 행 높이 조정 (8개가 모두 보이도록 적절한 크기로)
        self.numeric_table.verticalHeader().setDefaultSectionSize(18)  # 10 -> 18로 증가
        self.numeric_table.verticalHeader().setVisible(False)  # 세로 헤더 숨김
        
        # 스크롤바 비활성화
        self.numeric_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.numeric_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 테이블에 더 많은 공간 할당
        numeric_layout.addWidget(self.numeric_table, 1)
        
        # 초기에는 테이블 숨김
        self.numeric_table.setVisible(False)
        
        return numeric_container
    
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
    
    def search_patient(self):
        """환자 검색 - PatientDataManager에 위임"""
        self.patient_manager.search_patient()
    
    def admission_selected(self, index):
        """입원 기간 선택 - PatientDataManager에 위임"""
        self.patient_manager.admission_selected(index)
        # 컨텐츠 표시 업데이트
        self.update_content_visibility()
    
    def date_selected(self, date_str):
        """날짜 선택 - PatientDataManager에 위임"""
        self.patient_manager.date_selected(date_str)
        # 컨텐츠 표시 업데이트
        self.update_content_visibility()
    
    def on_alarm_selected(self, alarm):
        """알람 선택 처리"""
        color = alarm["color"]
        time = alarm["time"]
        timestamp = alarm.get("timestamp", f"{self.date_combo.currentText()} {time}")
        
        print(f"알람 선택 이벤트: {color} ({time}), 타임스탬프: {timestamp}")
        
        # 알람 ID 생성 (환자ID-날짜-시간 형태)
        date_str = self.date_combo.currentText()
        self.current_alarm_id = self.csv_manager.generate_alarm_id(
            self.patient_manager.current_patient_id, date_str, time
        )
        
        # PatientDataManager의 선택된 알람 정보 업데이트
        self.patient_manager.update_selected_alarm(color, time, timestamp)
        self.patient_manager.has_selected_alarm = True
        
        # 저장된 주석 데이터 로드
        annotation = self.csv_manager.get_annotation(self.current_alarm_id)
        
        # isAlarm 상태 업데이트
        if annotation['isAlarm'] is not None:
            status_text = "True" if annotation['isAlarm'] else "False"
            self.isalarm_status_label.setText(status_text)
            if annotation['isAlarm']:
                self.isalarm_status_label.setStyleSheet("color: red;")
            else:
                self.isalarm_status_label.setStyleSheet("")
        else:
            # 저장된 데이터가 없으면 기본값으로 설정
            self.isalarm_status_label.setText("None")
            self.isalarm_status_label.setStyleSheet("")
        
        # 코멘트 업데이트
        self.comment_text.setText(annotation['comment'])
        
        # 콘텐츠 표시 업데이트
        self.update_content_visibility()
        
        # 필터 다이얼로그 닫기
        if hasattr(self.nursing_manager, 'filter_dialog') and self.nursing_manager.filter_dialog is not None:
            self.nursing_manager.filter_dialog.close()
            self.nursing_manager.filter_dialog = None
        
        # 파형 데이터와 간호기록 로드
        self.waveform_manager.load_waveform_data(self.patient_manager.current_patient_id, timestamp)
        self.nursing_manager.load_nursing_record(self.patient_manager.current_patient_id, timestamp)
        
        print(f"알람 ID: {self.current_alarm_id}")
        if annotation['isAlarm'] is not None:
            print(f"저장된 isAlarm: {annotation['isAlarm']}, Comment: '{annotation['comment']}'")
    
    def update_content_visibility(self):
        """컨텐츠 표시 여부 업데이트"""
        has_date = self.patient_manager.has_selected_date
        has_alarm = self.patient_manager.has_selected_alarm
        
        if has_date and has_alarm:
            # 파형 섹션
            self.waveform_info_label.setVisible(False)
            self.waveform_widget.setVisible(True)
            
            # 간호기록 섹션
            self.record_info_label.setVisible(False)
            self.nursing_table.setVisible(True)
        else:
            # 파형 섹션
            self.waveform_info_label.setVisible(True)
            self.waveform_widget.setVisible(False)
            
            # Numeric 데이터 섹션 (기본 안내 메시지 표시)
            if hasattr(self, 'numeric_info_label'):
                self.numeric_info_label.setVisible(True)
            if hasattr(self, 'numeric_table'):
                self.numeric_table.setVisible(False)
            
            # 간호기록 섹션
            self.record_info_label.setVisible(True)
            self.nursing_table.setVisible(False)
    
    def save_comment(self):
        """주석 저장 - CSVManager에 위임"""
        comment = self.comment_text.text()
        is_alarm = self.isalarm_status_label.text() == "True"
        
        if self.current_alarm_id:
            # 주석 데이터 저장
            self.csv_manager.set_annotation(self.current_alarm_id, is_alarm, comment)
            # CSV 파일에 저장
            self.csv_manager.save_annotations()
            print(f"주석 저장됨 - ID: {self.current_alarm_id}, isAlarm: {is_alarm}, Comment: {comment}")
        else:
            print("저장할 알람이 선택되지 않았습니다")
    
    def set_isalarm(self, status):
        """isAlarm 상태 설정"""
        status_text = "True" if status else "False"
        self.isalarm_status_label.setText(status_text)
        
        if status:
            self.isalarm_status_label.setStyleSheet("color: red;")
        else:
            self.isalarm_status_label.setStyleSheet("")
            
        print(f"isAlarm 설정: {status_text}")
        
        # 즉시 저장
        if self.current_alarm_id:
            comment = self.comment_text.text()
            # 주석 데이터 저장
            self.csv_manager.set_annotation(self.current_alarm_id, status, comment)
            # CSV 파일에 저장
            self.csv_manager.save_annotations()
            print(f"isAlarm 즉시 저장됨 - ID: {self.current_alarm_id}, isAlarm: {status}, Comment: {comment}")
        else:
            print("저장할 알람이 선택되지 않았습니다")
    
    # 간호기록 필터 관련 메서드들을 NursingRecordManager에 위임
    @property
    def column_filters(self):
        """간호기록 관리자의 column_filters 속성에 접근"""
        return self.nursing_manager.column_filters if self.nursing_manager else {}
    
    def apply_column_filters(self):
        """컬럼 필터 적용 - NursingRecordManager에 위임"""
        if self.nursing_manager:
            self.nursing_manager.apply_column_filters()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SICUMonitoring()
    window.show()
    sys.exit(app.exec())
