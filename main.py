import sys
import os
import csv
from datetime import datetime, timedelta
from math import sin
import numpy as np
import base64
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QFrame, QScrollArea,
                             QTableWidget, QTableWidgetItem, QTextEdit, QCheckBox, QDateEdit,
                             QComboBox, QHeaderView, QSplitter, QSizePolicy, QGridLayout,
                             QCalendarWidget, QDialog, QListWidget, QListWidgetItem,
                             QDialogButtonBox, QMenu)
from PySide6.QtCore import Qt, QDate, QSize, QRect, QPoint, Signal, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QBrush, QAction

from data_structure import patient_data, ALARM_COLORS

# 엑셀 스타일 컬럼 필터 다이얼로그 클래스
class ExcelColumnFilterDialog(QDialog):
    def __init__(self, column_name, unique_values, selected_values, parent=None):
        super().__init__(parent)
        self.column_name = column_name
        self.unique_values = sorted(unique_values)  # 알파벳순 정렬
        # selected_values에 따라 초기 선택 상태 설정
        if isinstance(selected_values, set):
            self.selected_values = selected_values.copy()
        else:
            # selected_values가 None이거나 다른 타입인 경우 모든 값 선택
            self.selected_values = set(self.unique_values)
        self.parent_window = parent
        
        self.setWindowTitle(f"{column_name}")
        self.setModal(False)  # 비모달로 설정
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)  # 팝업 스타일
        self.resize(250, 350)
        
        self.setupUI()
        
    def setupUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 검색창
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색")
        self.search_input.textChanged.connect(self.filter_list)
        layout.addWidget(self.search_input)
        
        # 값 목록
        self.value_list = QListWidget()
        self.populate_list()
        layout.addWidget(self.value_list)
        
        # 다크 테마 스타일
        self.setStyleSheet("""
            QDialog {
                background-color: #333333;
                color: white;
                border: 2px solid #555555;
            }
            QListWidget {
                background-color: #2A2A2A;
                color: white;
                border: 1px solid #444444;
            }
            QListWidget::item {
                padding: 3px;
                border-bottom: 1px solid #444444;
            }
            QListWidget::item:selected {
                background-color: #3A3A3A;
            }
            QLineEdit {
                background-color: #2A2A2A;
                color: white;
                border: 1px solid #444444;
                padding: 5px;
            }
        """)
    
    def populate_list(self):
        """값 목록을 채우기 - 엑셀 스타일"""
        self.value_list.clear()
        
        # 먼저 "(모두 선택)" 항목 추가
        select_all_item = QListWidgetItem()
        select_all_checkbox = QCheckBox("(모두 선택)")
        
        # 모든 값이 선택되었는지 확인
        all_selected = len(self.selected_values) == len(self.unique_values)
        select_all_checkbox.setChecked(all_selected)
        select_all_checkbox.toggled.connect(self.toggle_all_items)
        
        self.value_list.addItem(select_all_item)
        self.value_list.setItemWidget(select_all_item, select_all_checkbox)
        
        # 개별 값들 추가
        for value in self.unique_values:
            item = QListWidgetItem()
            checkbox = QCheckBox(str(value))
            checkbox.setChecked(value in self.selected_values)
            checkbox.toggled.connect(lambda checked, v=value: self.value_changed(v, checked))
            
            self.value_list.addItem(item)
            self.value_list.setItemWidget(item, checkbox)
    
    def filter_list(self):
        """검색어에 따라 목록 필터링"""
        search_text = self.search_input.text().lower()
        
        for i in range(1, self.value_list.count()):  # "(모두 선택)" 제외
            item = self.value_list.item(i)
            widget = self.value_list.itemWidget(item)
            if widget:
                text = widget.text().lower()
                item.setHidden(search_text not in text)
    
    def toggle_all_items(self, checked):
        """모두 선택/해제 처리"""
        # 보이는 항목들만 체크/언체크
        for i in range(1, self.value_list.count()):  # "(모두 선택)" 제외
            item = self.value_list.item(i)
            if not item.isHidden():
                widget = self.value_list.itemWidget(item)
                if widget:
                    widget.blockSignals(True)  # 신호 차단
                    widget.setChecked(checked)
                    widget.blockSignals(False)  # 신호 재개
        
        # 선택된 값들 업데이트
        self.update_selected_values()
        # 즉시 필터 적용
        self.apply_filter()
    
    def value_changed(self, value, checked):
        """개별 값 변경 처리"""
        self.update_selected_values()
        self.update_select_all_state()
        # 즉시 필터 적용
        self.apply_filter()
    
    def update_selected_values(self):
        """선택된 값들 업데이트"""
        self.selected_values = set()
        
        for i in range(1, self.value_list.count()):  # "(모두 선택)" 제외
            item = self.value_list.item(i)
            widget = self.value_list.itemWidget(item)
            if widget and widget.isChecked():
                # 실제 값 찾기
                value_text = widget.text()
                for orig_value in self.unique_values:
                    if str(orig_value) == value_text:
                        self.selected_values.add(orig_value)
                        break
    
    def update_select_all_state(self):
        """전체 선택 체크박스 상태 업데이트"""
        visible_count = 0
        checked_count = 0
        
        for i in range(1, self.value_list.count()):  # "(모두 선택)" 제외
            item = self.value_list.item(i)
            if not item.isHidden():
                visible_count += 1
                widget = self.value_list.itemWidget(item)
                if widget and widget.isChecked():
                    checked_count += 1
        
        # "(모두 선택)" 체크박스 업데이트
        select_all_item = self.value_list.item(0)
        select_all_widget = self.value_list.itemWidget(select_all_item)
        if select_all_widget:
            select_all_widget.blockSignals(True)
            if visible_count == 0:
                select_all_widget.setChecked(False)
            elif checked_count == visible_count:
                select_all_widget.setChecked(True)
            else:
                select_all_widget.setChecked(False)
            select_all_widget.blockSignals(False)
    
    def apply_filter(self):
        """부모 윈도우에 필터 적용"""
        if self.parent_window:
            # 필터 상태 업데이트
            if len(self.selected_values) == len(self.unique_values):
                # 모든 값이 선택된 경우 필터 없음 (특별한 값으로 표시)
                self.parent_window.column_filters[self.column_name] = "ALL_SELECTED"
            elif len(self.selected_values) == 0:
                # 아무것도 선택되지 않은 경우 빈 세트 (아무것도 표시 안 함)
                self.parent_window.column_filters[self.column_name] = set()
            else:
                # 일부만 선택된 경우
                self.parent_window.column_filters[self.column_name] = self.selected_values.copy()
            
            # 필터 적용
            self.parent_window.apply_column_filters()
    
    def get_selected_values(self):
        """선택된 값들 반환"""
        return self.selected_values.copy()
    
    def focusOutEvent(self, event):
        """포커스를 잃었을 때 다이얼로그 닫기"""
        # 짧은 지연 후 닫기 (사용자가 다시 클릭할 수 있도록)
        QTimer.singleShot(100, self.close)
        super().focusOutEvent(event)

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
            
            # 디코딩된 파형 데이터가 있는 경우에만 그리기
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
                    
                    painter.drawPath(path)
            else:
                # 데이터가 없으면 아무것도 그리지 않음 (기본 사인파 제거)
                pass
            
            # 구분선 그리기
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
        self.current_alarm_id = ""  # 현재 선택된 알람 ID
        self.admission_periods = []  # 입원 기간 데이터를 저장
        self.csv_file_path = "alarm_annotations.csv"  # CSV 파일 경로
        self.annotation_data = {}  # 주석 데이터 캐시
        
        # 컬럼 필터 상태 관리
        self.column_filters = {}  # 각 컬럼에 대한 필터 상태
        self.original_data = []  # 원본 데이터 저장
        self.filter_dialog = None  # 현재 열리 다이얼로그 추적
        self.column_widths = {}  # 컬럼 너비 저장
        
        self.load_annotations()  # 저장된 주석 데이터 로드
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
        self.patient_id.setText("11604980")  # 기본 환자 ID 설정
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
        
        # 알람 ID 생성 (환자ID-날짜-시간 형태)
        date_str = self.date_combo.currentText()
        self.current_alarm_id = self.generate_alarm_id(self.current_patient_id, date_str, time)
        
        # 선택된 알람 정보 업데이트
        self.update_selected_alarm(color, time, timestamp)
        
        # 알람 선택 플래그 설정
        self.has_selected_alarm = True
        
        # 저장된 주석 데이터 로드
        annotation = self.get_annotation(self.current_alarm_id)
        
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
        if self.filter_dialog is not None:
            self.filter_dialog.close()
            self.filter_dialog = None
        
        # 파형 데이터와 간호기록 로드
        self.load_waveform_data(timestamp)
        self.load_nursing_record(timestamp)
        
        print(f"알람 ID: {self.current_alarm_id}")
        if annotation['isAlarm'] is not None:
            print(f"저장된 isAlarm: {annotation['isAlarm']}, Comment: '{annotation['comment']}'")
    
    def update_content_visibility(self):
        if self.has_selected_date and self.has_selected_alarm:
            self.waveform_info_label.setVisible(False)
            self.waveform_widget.setVisible(True)
            
            self.record_info_label.setVisible(False)
            self.nursing_table.setVisible(True)
        else:
            self.waveform_info_label.setVisible(True)
            self.waveform_widget.setVisible(False)
            
            self.record_info_label.setVisible(True)
            self.nursing_table.setVisible(False)
    
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
        
        # 간호기록 테이블에 데이터 추가
        self.setup_nursing_table(records)
    
    def clear_nursing_records(self):
        """간호기록 테이블 초기화"""
        self.nursing_table.setRowCount(0)
        self.nursing_table.setColumnCount(0)
    
    def setup_nursing_table(self, records):
        """간호기록 테이블 설정 및 데이터 추가 (엑셀 스타일)"""
        if not records:
            return
        
        # 기존 컬럼 너비 저장 (만약 테이블이 이미 있는 경우)
        if self.nursing_table.columnCount() > 0:
            for i in range(self.nursing_table.columnCount()):
                header_item = self.nursing_table.horizontalHeaderItem(i)
                if header_item:
                    column_name = header_item.text()
                    self.column_widths[column_name] = self.nursing_table.columnWidth(i)
        
        # 컬럼 설정 (시행일시를 맨 뒤로 이동)
        columns = [
            "간호중재(코드명)",
            "간호활동(코드명)",
            "간호속성코드(코드명)",
            "속성",
            "Duty(코드명)",
            "시행일시"  # 맨 뒤로 이동
        ]
        
        self.nursing_table.setColumnCount(len(columns))
        self.nursing_table.setHorizontalHeaderLabels(columns)
        self.nursing_table.setRowCount(len(records))
        
        # 데이터 추가
        for row_idx, record in enumerate(records):
            # 데이터 컨럼들 (시행일시를 맨 뒤로)
            data_columns = [
                "간호중재(코드명)",
                "간호활동(코드명)",
                "간호속성코드(코드명)",
                "속성",
                "Duty(코드명)",
                "시행일시"
            ]
            
            for col_idx, column in enumerate(data_columns):
                item = QTableWidgetItem(str(record.get(column, "")))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용
                self.nursing_table.setItem(row_idx, col_idx, item)
        
        # 컬럼 크기 조정 (마우스로 조절 가능)
        header = self.nursing_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)  # 모든 컬럼 마우스로 조절 가능
        header.setStretchLastSection(True)  # 마지막 컬럼은 남은 공간 채우기
        
        # 저장된 컬럼 너비 복원 또는 기본 너비 설정
        default_widths = {
            "간호중재(코드명)": 200,
            "간호활동(코드명)": 200, 
            "간호속성코드(코드명)": 200,
            "속성": 150,
            "Duty(코드명)": 150,
            "시행일시": 150  # 맨 뒤로 이동되었지만 기본 너비 설정
        }
        
        for i, column_name in enumerate(columns):
            if column_name in self.column_widths:
                # 저장된 너비 사용
                self.nursing_table.setColumnWidth(i, self.column_widths[column_name])
            else:
                # 기본 너비 사용
                self.nursing_table.setColumnWidth(i, default_widths[column_name])
        
        # 날짜/시간 컨럼 정렬 (시행일시가 마지막 컨럼이므로)
        self.nursing_table.sortByColumn(len(columns) - 1, Qt.AscendingOrder)  # 마지막 컨럼(시행일시)로 정렬
        
        # 원본 데이터 저장
        self.original_data = records
        
        # 헤더 컴텍스트 메뉴 설정 (엑셀 스타일 필터)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_column_filter_menu)
        
        # 컬럼 필터 초기화 - 처음에는 모든 값이 선택된 상태
        self.column_filters = {}
        for i in range(self.nursing_table.columnCount()):
            column_name = self.nursing_table.horizontalHeaderItem(i).text()
            self.column_filters[column_name] = "ALL_SELECTED"  # 초기에는 모든 값 선택된 상태
        
        # 컬럼 너비 변경 시 저장하는 시그널 연결
        header.sectionResized.connect(self.save_column_width)
    
    def save_column_width(self, logical_index, old_size, new_size):
        """컬럼 너비 변경 시 저장"""
        header_item = self.nursing_table.horizontalHeaderItem(logical_index)
        if header_item:
            column_name = header_item.text()
            self.column_widths[column_name] = new_size
            print(f"컬럼 '{column_name}' 너비 저장: {new_size}")
    
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
        self.current_alarm_id = ""
        
        # 알람 관련 필드 초기화
        self.isalarm_status_label.setText("None")
        self.isalarm_status_label.setStyleSheet("")
        self.comment_text.setText("")
        
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
        is_alarm = self.isalarm_status_label.text() == "True"
        
        if self.current_alarm_id:
            # 주석 데이터 저장
            self.set_annotation(self.current_alarm_id, is_alarm, comment)
            # CSV 파일에 저장
            self.save_annotations()
            print(f"주석 저장됨 - ID: {self.current_alarm_id}, isAlarm: {is_alarm}, Comment: {comment}")
        else:
            print("저장할 알람이 선택되지 않았습니다")
    
    def set_isalarm(self, status):
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
            self.set_annotation(self.current_alarm_id, status, comment)
            # CSV 파일에 저장
            self.save_annotations()
            print(f"isAlarm 즉시 저장됨 - ID: {self.current_alarm_id}, isAlarm: {status}, Comment: {comment}")
        else:
            print("저장할 알람이 선택되지 않았습니다")
    
    # CSV 관련 메서드들
    def generate_alarm_id(self, patient_id, date_str, time_str):
        """알람 ID 생성: 환자ID-날짜-시간 형태"""
        return f"{patient_id}-{date_str}-{time_str}"
    
    def load_annotations(self):
        """CSV 파일에서 주석 데이터 로드"""
        self.annotation_data = {}
        
        if not os.path.exists(self.csv_file_path):
            # CSV 파일이 없으면 헤더만 생성
            self.save_annotations()
            return
        
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    alarm_id = row['AlarmID']
                    is_alarm = row['isAlarm'].lower() == 'true'
                    comment = row['Comment']
                    self.annotation_data[alarm_id] = {
                        'isAlarm': is_alarm,
                        'comment': comment
                    }
            print(f"주석 데이터 로드 완료: {len(self.annotation_data)}개")
        except Exception as e:
            print(f"주석 데이터 로드 오류: {e}")
    
    def save_annotations(self):
        """주석 데이터를 CSV 파일에 저장"""
        try:
            with open(self.csv_file_path, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['AlarmID', 'isAlarm', 'Comment']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # 헤더 작성
                writer.writeheader()
                
                # 데이터 작성
                for alarm_id, data in self.annotation_data.items():
                    writer.writerow({
                        'AlarmID': alarm_id,
                        'isAlarm': str(data['isAlarm']),
                        'Comment': data['comment']
                    })
            print(f"주석 데이터 저장 완료: {self.csv_file_path}")
        except Exception as e:
            print(f"주석 데이터 저장 오류: {e}")
    
    def get_annotation(self, alarm_id):
        """특정 알람 ID의 주석 데이터 가져오기"""
        return self.annotation_data.get(alarm_id, {'isAlarm': None, 'comment': ''})
    
    def set_annotation(self, alarm_id, is_alarm, comment):
        """특정 알람 ID의 주석 데이터 설정"""
        self.annotation_data[alarm_id] = {
            'isAlarm': is_alarm,
            'comment': comment
        }
    
    # 엑셀 스타일 컬럼 필터 관련 메서드들
    def show_column_filter_menu(self, position):
        """컬럼 헤더 우클릭 시 엑셀 스타일 필터 메뉴 표시"""
        # 이미 다이얼로그가 열려있으면 닫기
        if self.filter_dialog is not None:
            self.filter_dialog.close()
            self.filter_dialog = None
        
        header = self.nursing_table.horizontalHeader()
        column_index = header.logicalIndexAt(position)
        
        if column_index < 0:
            return
        
        column_name = self.nursing_table.horizontalHeaderItem(column_index).text()
        
        # 해당 컨럼의 고유한 값들 수집
        unique_values = set()
        for row in range(self.nursing_table.rowCount()):
            item = self.nursing_table.item(row, column_index)
            if item:
                value = item.text().strip()
                if value:  # 빈 값 제외
                    unique_values.add(value)
        
        # 현재 선택된 값들 가져오기
        current_selected = self.column_filters.get(column_name, "ALL_SELECTED")
        if current_selected == "ALL_SELECTED":  # 모든 값이 선택된 경우
            current_selected = unique_values.copy()
        elif isinstance(current_selected, set) and len(current_selected) == 0:
            # 빈 세트인 경우 아무것도 선택되지 않은 상태
            current_selected = set()
        
        # 엑셀 스타일 필터 다이얼로그 열기 (비모달)
        self.filter_dialog = ExcelColumnFilterDialog(column_name, unique_values, current_selected, self)
        
        # 다이얼로그가 닫힘 때 참조 제거
        self.filter_dialog.finished.connect(lambda: setattr(self, 'filter_dialog', None))
        
        # 다이얼로그를 클릭한 위치 근처에 표시 (화면 범위 내에서)
        global_pos = header.mapToGlobal(position)
        dialog_x = min(global_pos.x(), self.screen().availableGeometry().width() - self.filter_dialog.width())
        dialog_y = min(global_pos.y() + 30, self.screen().availableGeometry().height() - self.filter_dialog.height())
        self.filter_dialog.move(dialog_x, dialog_y)
        
        # 비모달로 열기 (스플리터 사용 가능)
        self.filter_dialog.show()
    
    def apply_column_filters(self):
        """컬럼 필터 적용"""
        for row in range(self.nursing_table.rowCount()):
            show_row = True
            
            # 각 컨럼에 대한 필터 확인
            for column_name, selected_values in self.column_filters.items():
                # 컨럼 인덱스 찾기
                column_index = -1
                for col in range(self.nursing_table.columnCount()):
                    header_item = self.nursing_table.horizontalHeaderItem(col)
                    if header_item and header_item.text() == column_name:
                        column_index = col
                        break
                
                if column_index >= 0:
                    item = self.nursing_table.item(row, column_index)
                    if item:
                        cell_value = item.text().strip()
                        
                        # 필터 로직 변경: 빈 세트이면 아무것도 표시하지 않음
                        if selected_values == "ALL_SELECTED":
                            # 모든 값이 선택된 경우 - 모든 행 표시
                            continue
                        elif isinstance(selected_values, set) and len(selected_values) == 0:
                            # 아무것도 선택되지 않은 경우 - 아무 행도 표시하지 않음
                            show_row = False
                            break
                        elif isinstance(selected_values, set) and cell_value not in selected_values:
                            # 일부만 선택된 경우 - 선택된 값만 표시
                            show_row = False
                            break
            
            self.nursing_table.setRowHidden(row, not show_row)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SICUMonitoring()
    window.show()
    sys.exit(app.exec())
