import sys
import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QFrame, QScrollArea,
                             QTableWidget, QTableWidgetItem, QTextEdit, QCheckBox, QDateEdit,
                             QComboBox, QHeaderView, QSplitter, QSizePolicy, QGridLayout,
                             QCalendarWidget, QDialog, QListWidget, QListWidgetItem,
                             QDialogButtonBox, QMenu, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, QDate, QSize, QRect, QPoint, Signal, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QBrush, QAction

from data_structure import patient_data, ALARM_COLORS
import pandas as pd

# 분리된 컴포넌트들 import
from components.waveform_manager import WaveformWidget, WaveformManager
from components.nursing_record_manager import NursingRecordManager

WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
PATIENT_LIST_WIDTH = 280  # 최소 공간으로 더 줄임
WAVEFORM_HEIGHT = 300
HEADER_HEIGHT = 25
SAVE_BUTTON_WIDTH = 60
COMMENT_HEIGHT = 30

class PatientListWidget(QTreeWidget):
    """접을 수 있는 환자 리스트 트리 위젯"""
    alarmSelected = Signal(str, str, str, str, dict)  # patient_id, admission_id, date_str, time_str, alarm_data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Patient List")
        self.setMaximumWidth(PATIENT_LIST_WIDTH)
        self.setMinimumWidth(PATIENT_LIST_WIDTH)
        self.current_alarm_item = None  # 현재 선택된 알람 아이템 추적
        
        # 다크 테마 스타일
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #2A2A2A;
                color: white;
                border: 1px solid #444444;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 3px;
                border-bottom: 1px solid #333333;
            }
            QTreeWidget::item:selected {
                background-color: #404040;
            }
            QTreeWidget::item:hover {
                background-color: #353535;
            }
            QTreeWidget::branch:has-children:open {
                image: none;
            }
            QTreeWidget::branch:has-children:closed {
                image: none;
            }
        """)
        
        self.itemClicked.connect(self.on_item_clicked)
        self.load_patient_list()
    
    def load_patient_list(self):
        """환자 리스트 로드"""
        self.clear()
        
        patient_ids = patient_data.get_all_patient_ids()
        
        for patient_id in patient_ids:
            # 환자 통계 정보 가져오기
            stats = patient_data.get_patient_alarm_stats(patient_id)
            
            # 환자 노드 생성
            patient_item = QTreeWidgetItem(self)
            patient_item.setText(0, f"{patient_id} ({stats['labeled']}/{stats['total']})")
            patient_item.setData(0, Qt.UserRole, {'type': 'patient', 'patient_id': patient_id})
            
            # 입원 기간들 추가
            admission_periods = patient_data.get_admission_periods(patient_id)
            for admission in admission_periods:
                admission_item = QTreeWidgetItem(patient_item)
                admission_text = f"{admission['start']} ~ {admission['end']}"
                admission_item.setText(0, admission_text)
                admission_item.setData(0, Qt.UserRole, {
                    'type': 'admission',
                    'patient_id': patient_id,
                    'admission_id': admission['id']
                })
                
                # 날짜들 추가
                dates = patient_data.get_available_dates(patient_id, admission['id'])
                for date_str in dates:
                    date_item = QTreeWidgetItem(admission_item)
                    date_item.setText(0, date_str)
                    date_item.setData(0, Qt.UserRole, {
                        'type': 'date',
                        'patient_id': patient_id,
                        'admission_id': admission['id'],
                        'date_str': date_str
                    })
                    
                    # 해당 날짜의 알람들 추가
                    alarms = patient_data.get_alarms_for_date(patient_id, admission['id'], date_str)
                    for alarm in alarms:
                        alarm_item = QTreeWidgetItem(date_item)
                        
                        # 라벨링 상태에 따른 표시
                        classification = alarm.get('classification')
                        if classification is None:
                            status_icon = "⚪"  # 라벨링 안됨
                        elif classification:
                            status_icon = "🔴"  # True
                        else:
                            status_icon = "⚫"  # False
                        
                        # 시간 포맷 정리 (밀리초 제거)
                        time_str = alarm['time']
                        if '.' in time_str:  # 밀리초가 있는 경우
                            time_str = time_str.split('.')[0]  # 밀리초 부분 제거
                        
                        # 알람 텍스트 구성 (색깔과 시:분:초만)
                        alarm_text = f"{status_icon} {alarm['color']} {time_str}"
                        
                        alarm_item.setText(0, alarm_text)
                        alarm_item.setData(0, Qt.UserRole, {
                            'type': 'alarm',
                            'patient_id': patient_id,
                            'admission_id': admission['id'],
                            'date_str': date_str,
                            'time_str': alarm['time'],
                            'alarm_data': alarm
                        })
                
                # 날짜 노드들을 기본적으로 접힌 상태로
                admission_item.setExpanded(False)
            
            # 입원 기간 노드들을 기본적으로 접힌 상태로
            patient_item.setExpanded(False)
    
    def refresh_patient_stats(self):
        """환자 통계 정보 새로고침 (라벨링 후 호출)"""
        for i in range(self.topLevelItemCount()):
            patient_item = self.topLevelItem(i)
            data = patient_item.data(0, Qt.UserRole)
            if data and data.get('type') == 'patient':
                patient_id = data['patient_id']
                stats = patient_data.get_patient_alarm_stats(patient_id)
                patient_item.setText(0, f"{patient_id} ({stats['labeled']}/{stats['total']})")
        
        # 알람 아이템들의 상태 아이콘도 업데이트
        self.refresh_alarm_status_icons()
    
    def refresh_alarm_status_icons(self):
        """알람 아이템들의 상태 아이콘 업데이트"""
        def update_items(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                data = child.data(0, Qt.UserRole)
                if data and data.get('type') == 'alarm':
                    # 최신 알람 데이터 가져오기
                    patient_id = data['patient_id']
                    admission_id = data['admission_id']
                    date_str = data['date_str']
                    time_str = data['time_str']
                    alarm_data = data['alarm_data']  # 원래 알람 데이터
                    
                    annotation = patient_data.get_alarm_annotation(patient_id, admission_id, date_str, time_str)
                    classification = annotation['classification']
                    
                    if classification is None:
                        status_icon = "⚪"  # 라벨링 안됨
                    elif classification:
                        status_icon = "🔴"  # True
                    else:
                        status_icon = "⚫"  # False
                    
                    # 시간 포맷 정리 (Patient List에서만 밀리초 제거)
                    time_display = time_str
                    if '.' in time_display:  # 밀리초가 있는 경우
                        time_display = time_display.split('.')[0]  # 밀리초 부분 제거
                    
                    # 알람 텍스트 구성 (Patient List에서는 색깔과 시:분:초만)
                    alarm_text = f"{status_icon} {alarm_data['color']} {time_display}"
                    
                    child.setText(0, alarm_text)
                else:
                    # 재귀적으로 하위 아이템들도 업데이트
                    update_items(child)
        
        # 모든 최상위 아이템부터 시작
        for i in range(self.topLevelItemCount()):
            update_items(self.topLevelItem(i))
    
    def on_item_clicked(self, item, column):
        """아이템 클릭 처리"""
        data = item.data(0, Qt.UserRole)
        if data and data.get('type') == 'alarm':
            self.current_alarm_item = item  # 현재 선택된 알람 아이템 저장
            # 알람 클릭 시 신호 발생
            self.alarmSelected.emit(
                data['patient_id'],
                data['admission_id'], 
                data['date_str'],
                data['time_str'],
                data['alarm_data']
            )
            # print(f"알람 선택: {data['patient_id']} - {data['alarm_data']['color']} {data['time_str']}")  # 디버그 로그 비활성화
    
    def select_next_alarm(self):
        """다음 알람으로 이동"""
        if not self.current_alarm_item:
            # 현재 선택된 알람이 없으면 첫 번째 알람 선택
            first_alarm = self.find_first_alarm_item()
            if first_alarm:
                self.setCurrentItem(first_alarm)
                self.on_item_clicked(first_alarm, 0)
                return True
            return False
        
        # 현재 아이템의 다음 알람 찾기
        next_item = self.find_next_alarm_item(self.current_alarm_item)
        
        if next_item:
            # 다음 알람 선택
            self.setCurrentItem(next_item)
            self.on_item_clicked(next_item, 0)
            return True
        
        return False
    
    def select_previous_alarm(self):
        """이전 알람으로 이동"""
        if not self.current_alarm_item:
            # 현재 선택된 알람이 없으면 마지막 알람 선택
            last_alarm = self.find_last_alarm_item()
            if last_alarm:
                self.setCurrentItem(last_alarm)
                self.on_item_clicked(last_alarm, 0)
                return True
            return False
        
        # 현재 아이템의 이전 알람 찾기
        prev_item = self.find_previous_alarm_item(self.current_alarm_item)
        
        if prev_item:
            # 이전 알람 선택
            self.setCurrentItem(prev_item)
            self.on_item_clicked(prev_item, 0)
            return True
        
        return False
    
    def find_next_alarm_item(self, current_item):
        """트리에서 다음 알람 아이템 찾기"""
        # 현재 아이템의 부모(날짜 노드)
        date_parent = current_item.parent()
        if not date_parent:
            return None
        
        # 같은 날짜 내에서 다음 알람 찾기
        current_index = date_parent.indexOfChild(current_item)
        if current_index < date_parent.childCount() - 1:
            # 같은 날짜의 다음 알람이 있음
            return date_parent.child(current_index + 1)
        
        # 다음 날짜 찾기
        admission_parent = date_parent.parent()
        if not admission_parent:
            return None
        
        date_index = admission_parent.indexOfChild(date_parent)
        
        # 같은 입원 기간 내 다음 날짜 확인
        for i in range(date_index + 1, admission_parent.childCount()):
            next_date = admission_parent.child(i)
            if next_date.childCount() > 0:
                # 다음 날짜의 첫 번째 알람 반환
                return next_date.child(0)
        
        # 다음 입원 기간 찾기
        patient_parent = admission_parent.parent()
        if not patient_parent:
            return None
        
        admission_index = patient_parent.indexOfChild(admission_parent)
        
        # 같은 환자의 다음 입원 기간 확인
        for i in range(admission_index + 1, patient_parent.childCount()):
            next_admission = patient_parent.child(i)
            # 입원 기간의 첫 번째 날짜 찾기
            for j in range(next_admission.childCount()):
                date_node = next_admission.child(j)
                if date_node.childCount() > 0:
                    # 첫 번째 알람 반환
                    return date_node.child(0)
        
        # 다음 환자 찾기
        root_index = self.indexOfTopLevelItem(patient_parent)
        
        # 다음 환자들 확인
        for i in range(root_index + 1, self.topLevelItemCount()):
            next_patient = self.topLevelItem(i)
            # 환자의 첫 번째 입원 기간
            for j in range(next_patient.childCount()):
                admission_node = next_patient.child(j)
                # 입원 기간의 첫 번째 날짜
                for k in range(admission_node.childCount()):
                    date_node = admission_node.child(k)
                    if date_node.childCount() > 0:
                        # 첫 번째 알람 반환
                        return date_node.child(0)
        
        return None  # 더 이상 알람이 없음
    
    def find_previous_alarm_item(self, current_item):
        """트리에서 이전 알람 아이템 찾기"""
        # 현재 아이템의 부모(날짜 노드)
        date_parent = current_item.parent()
        if not date_parent:
            return None
        
        # 같은 날짜 내에서 이전 알람 찾기
        current_index = date_parent.indexOfChild(current_item)
        if current_index > 0:
            # 같은 날짜의 이전 알람이 있음
            return date_parent.child(current_index - 1)
        
        # 이전 날짜 찾기
        admission_parent = date_parent.parent()
        if not admission_parent:
            return None
        
        date_index = admission_parent.indexOfChild(date_parent)
        
        # 같은 입원 기간 내 이전 날짜 확인
        for i in range(date_index - 1, -1, -1):
            prev_date = admission_parent.child(i)
            if prev_date.childCount() > 0:
                # 이전 날짜의 마지막 알람 반환
                return prev_date.child(prev_date.childCount() - 1)
        
        # 이전 입원 기간 찾기
        patient_parent = admission_parent.parent()
        if not patient_parent:
            return None
        
        admission_index = patient_parent.indexOfChild(admission_parent)
        
        # 같은 환자의 이전 입원 기간 확인
        for i in range(admission_index - 1, -1, -1):
            prev_admission = patient_parent.child(i)
            # 입원 기간의 마지막 날짜 찾기
            for j in range(prev_admission.childCount() - 1, -1, -1):
                date_node = prev_admission.child(j)
                if date_node.childCount() > 0:
                    # 마지막 알람 반환
                    return date_node.child(date_node.childCount() - 1)
        
        # 이전 환자 찾기
        root_index = self.indexOfTopLevelItem(patient_parent)
        
        # 이전 환자들 확인
        for i in range(root_index - 1, -1, -1):
            prev_patient = self.topLevelItem(i)
            # 환자의 마지막 입원 기간
            for j in range(prev_patient.childCount() - 1, -1, -1):
                admission_node = prev_patient.child(j)
                # 입원 기간의 마지막 날짜
                for k in range(admission_node.childCount() - 1, -1, -1):
                    date_node = admission_node.child(k)
                    if date_node.childCount() > 0:
                        # 마지막 알람 반환
                        return date_node.child(date_node.childCount() - 1)
        
        return None  # 더 이상 알람이 없음
    
    def find_first_alarm_item(self):
        """트리에서 첫 번째 알람 아이템 찾기"""
        for i in range(self.topLevelItemCount()):
            patient = self.topLevelItem(i)
            for j in range(patient.childCount()):
                admission = patient.child(j)
                for k in range(admission.childCount()):
                    date_node = admission.child(k)
                    if date_node.childCount() > 0:
                        return date_node.child(0)
        return None
    
    def find_last_alarm_item(self):
        """트리에서 마지막 알람 아이템 찾기"""
        for i in range(self.topLevelItemCount() - 1, -1, -1):
            patient = self.topLevelItem(i)
            for j in range(patient.childCount() - 1, -1, -1):
                admission = patient.child(j)
                for k in range(admission.childCount() - 1, -1, -1):
                    date_node = admission.child(k)
                    if date_node.childCount() > 0:
                        return date_node.child(date_node.childCount() - 1)
        return None


class SICUMonitoring(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_patient_id = ""
        self.current_admission_id = ""
        self.current_date_str = ""
        self.current_time_str = ""
        self.current_alarm_data = {}
        
        # 분리된 컴포넌트 관리자들
        self.waveform_manager = None  # UI 생성 후 초기화
        self.nursing_manager = None   # UI 생성 후 초기화
        
        self.initUI()
        self.connectSignals()
        
    def initUI(self):
        self.setWindowTitle("SICU - Monitoring (New Design)")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.setStyleSheet("background-color: #333333; color: white;")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 왼쪽: 환자 리스트
        self.patient_list = PatientListWidget()
        main_layout.addWidget(self.patient_list)
        
        # 오른쪽: 콘텐츠 영역
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 상단: 선택된 알람 정보만
        self.alarm_info_section = self.createAlarmInfoSection()
        right_layout.addWidget(self.alarm_info_section)
        
        # 중단: 콘텐츠 (2x2 그리드)
        content_splitter = self.createContentSection()
        right_layout.addWidget(content_splitter)
        
        main_layout.addWidget(right_container)
        
        # 초기 비율 설정
        main_layout.setStretch(0, 0)  # 환자 리스트는 고정 크기
        main_layout.setStretch(1, 1)  # 콘텐츠 영역은 늘어남
        
        # 컴포넌트 관리자들 초기화 (UI 생성 후)
        self.waveform_manager = WaveformManager(
            self.waveform_widget, self.waveform_info_label,
            self.numeric_table, self.numeric_info_label
        )
        self.nursing_manager = NursingRecordManager(self.nursing_table, self.record_info_label, self)
        
    def createAlarmInfoSection(self):
        """선택된 알람 정보 표시 섹션 (간단하게)"""
        info_section = QWidget()
        info_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        info_section.setFixedHeight(60)  # 높이 줄임
        info_layout = QVBoxLayout(info_section)
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_layout.setSpacing(5)
        
        # 선택된 알람 정보만 표시
        self.selected_alarm_label = QLabel("알람을 선택해주세요")
        self.selected_alarm_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        info_layout.addWidget(self.selected_alarm_label)
        
        return info_section
    
    def createContentSection(self):
        """콘텐츠 섹션 - 상하 2층, 좌우 2열 레이아웃"""
        # 메인 스플리터 (상하 분할)
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setChildrenCollapsible(False)
        
        # 상단 스플리터 (좌우 분할)
        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setChildrenCollapsible(False)
        
        # 하단 스플리터 (좌우 분할)
        bottom_splitter = QSplitter(Qt.Horizontal)
        bottom_splitter.setChildrenCollapsible(False)
        
        # 4개 프레임 생성
        classification_comment_frame = self.createClassificationCommentFrame()  # 상좌
        numeric_frame = self.createNumericFrame()                              # 상우
        waveform_frame = self.createWaveformFrame()                            # 하좌
        nursing_frame = self.createNursingRecordFrame()                        # 하우
        
        # 상단 스플리터에 추가
        top_splitter.addWidget(classification_comment_frame)
        top_splitter.addWidget(numeric_frame)
        
        # 하단 스플리터에 추가
        bottom_splitter.addWidget(waveform_frame)
        bottom_splitter.addWidget(nursing_frame)
        
        # 메인 스플리터에 추가
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(bottom_splitter)
        
        # 비율 설정: 상단(40%) | 하단(60%)
        main_splitter.setSizes([400, 600])
        
        # 상단 좌우 비율: Classification&Comment(50%) | NumericData(50%)
        top_splitter.setSizes([500, 500])
        
        # 하단 좌우 비율: Waveform(50%) | NursingRecord(50%)
        bottom_splitter.setSizes([500, 500])
        
        return main_splitter
    
    def createClassificationCommentFrame(self):
        """Classification + Comment 프레임 (좌상)"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        frame.setFrameShadow(QFrame.Plain)
        frame.setLineWidth(1)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # 1. Classification 섹션
        classification_section = QWidget()
        classification_layout = QVBoxLayout(classification_section)
        classification_layout.setContentsMargins(0, 0, 0, 0)
        classification_layout.setSpacing(5)
        
        # Classification 헤더
        class_header = QHBoxLayout()
        class_header.setContentsMargins(0, 0, 0, 0)
        
        class_label = QLabel("Classification:")
        class_label.setStyleSheet("font-weight: bold;")
        class_header.addWidget(class_label)
        
        self.classification_status_label = QLabel("None")
        class_header.addWidget(self.classification_status_label)
        class_header.addStretch()
        
        classification_layout.addLayout(class_header)
        
        # Classification 버튼들 (True/False만)
        class_buttons = QHBoxLayout()
        class_buttons.setContentsMargins(0, 0, 0, 0)
        class_buttons.setSpacing(5)
        
        self.true_button = QPushButton("True")
        self.true_button.setFixedWidth(70)
        self.true_button.setStyleSheet("QPushButton { font-weight: bold; }")
        
        self.false_button = QPushButton("False")
        self.false_button.setFixedWidth(70)
        self.false_button.setStyleSheet("QPushButton { font-weight: bold; }")
        
        class_buttons.addWidget(self.true_button)
        class_buttons.addWidget(self.false_button)
        class_buttons.addStretch()
        
        classification_layout.addLayout(class_buttons)
        
        layout.addWidget(classification_section)
        
        # 2. Comment 섹션
        comment_section = QWidget()
        comment_layout = QVBoxLayout(comment_section)
        comment_layout.setContentsMargins(0, 0, 0, 0)
        comment_layout.setSpacing(5)
        
        # Comment 헤더
        comment_header = QHBoxLayout()
        comment_header.setContentsMargins(0, 0, 0, 0)
        
        comment_label = QLabel("Comment:")
        comment_label.setStyleSheet("font-weight: bold;")
        comment_header.addWidget(comment_label)
        comment_header.addStretch()
        
        self.submit_button = QPushButton("저장")
        self.submit_button.setFixedWidth(SAVE_BUTTON_WIDTH)
        comment_header.addWidget(self.submit_button)
        
        comment_layout.addLayout(comment_header)
        
        self.comment_text = QLineEdit()
        self.comment_text.setFixedHeight(COMMENT_HEIGHT)
        comment_layout.addWidget(self.comment_text)
        
        layout.addWidget(comment_section)
        
        # 남은 공간 채우기
        layout.addStretch()
        
        return frame
    
    def createWaveformFrame(self):
        """파형 데이터 프레임 (좌하)"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        frame.setFrameShadow(QFrame.Plain)
        frame.setLineWidth(1)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        # 헤더
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
        
        self.waveform_info_label = QLabel("알람을 선택하세요")
        self.waveform_info_label.setAlignment(Qt.AlignCenter)
        self.waveform_info_label.setStyleSheet("color: #888888; font-size: 14px;")
        
        self.waveform_widget = WaveformWidget()
        
        layout.addWidget(header_widget)
        layout.addWidget(header_line)
        layout.addWidget(content_container, 1)
        
        content_layout.addWidget(self.waveform_info_label)
        content_layout.addWidget(self.waveform_widget)
        
        self.waveform_widget.setVisible(False)
        
        return frame
    
    def createNumericFrame(self):
        """Numeric Data 프레임 (우상)"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        frame.setFrameShadow(QFrame.Plain)
        frame.setLineWidth(1)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Numeric 헤더
        numeric_label = QLabel("Numeric Data:")
        numeric_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(numeric_label)
        
        # Numeric 정보 라벨
        self.numeric_info_label = QLabel("알람 선택 시 표시")
        self.numeric_info_label.setAlignment(Qt.AlignCenter)
        self.numeric_info_label.setStyleSheet("color: #888888; font-size: 12px;")
        layout.addWidget(self.numeric_info_label)
        
        # Numeric 데이터 테이블 (8개 파라미터가 모두 보이도록)
        self.numeric_table = QTableWidget()
        self.numeric_table.setColumnCount(3)
        self.numeric_table.setHorizontalHeaderLabels(["Parameter", "Value", "Time Diff (s)"])
        self.numeric_table.setRowCount(8)  # 8행 고정
        
        # 테이블 높이를 8개 행이 모두 보이도록 설정 (스크롤 없이)
        row_height = 22
        header_height = 28
        total_height = header_height + (row_height * 8) + 15
        self.numeric_table.setFixedHeight(total_height)
        
        # 테이블 스타일
        self.numeric_table.setStyleSheet("""
            QTableWidget {
                background-color: #000000;
                color: white;
                gridline-color: #444444;
                border: 1px solid #444444;
            }
            QTableWidget::item {
                background-color: #000000;
                color: white;
                padding: 3px;
                border-bottom: 1px solid #444444;
                font-size: 11px;
            }
            QTableWidget::item:selected {
                background-color: #1A1A1A;
            }
            QHeaderView::section {
                background-color: #1A1A1A;
                color: white;
                padding: 3px;
                border: 1px solid #444444;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        
        # 컬럼 크기 조정
        header = self.numeric_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        # 컬럼 너비 고정 설정
        self.numeric_table.setColumnWidth(0, 80)   # Parameter
        self.numeric_table.setColumnWidth(1, 80)   # Value
        
        # 행 높이 설정
        self.numeric_table.verticalHeader().setDefaultSectionSize(row_height)
        self.numeric_table.verticalHeader().setVisible(False)
        
        # 스크롤바 비활성화
        self.numeric_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.numeric_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        layout.addWidget(self.numeric_table)
        
        # 초기에는 테이블 숨김
        self.numeric_table.setVisible(False)
        
        # 남은 공간 채우기
        layout.addStretch()
        
        return frame
    
    def createNursingRecordFrame(self):
        """간호기록 프레임 (우하)"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        frame.setFrameShadow(QFrame.Plain)
        frame.setLineWidth(1)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        # 헤더
        header_widget = QWidget()
        header_widget.setFixedHeight(HEADER_HEIGHT)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 0, 5, 0)
        
        nursing_label = QLabel("Nursing Record")
        nursing_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_layout.addWidget(nursing_label)
        header_layout.addStretch()
        
        layout.addWidget(header_widget)
        
        header_line = QFrame()
        header_line.setFrameShape(QFrame.HLine)
        header_line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(header_line)
        
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content_container, 1)
        
        self.record_info_label = QLabel("알람을 선택하세요")
        self.record_info_label.setAlignment(Qt.AlignCenter)
        self.record_info_label.setStyleSheet("color: #888888; font-size: 14px;")
        content_layout.addWidget(self.record_info_label)
        
        # 간호기록 테이블
        self.nursing_table = QTableWidget()
        self.nursing_table.setAlternatingRowColors(False)
        self.nursing_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.nursing_table.setStyleSheet("""
            QTableWidget {
                background-color: #000000;
                color: white;
                gridline-color: #444444;
                border: 1px solid #444444;
            }
            QTableWidget::item {
                background-color: #000000;
                color: white;
                padding: 5px;
                border-bottom: 1px solid #444444;
            }
            QTableWidget::item:selected {
                background-color: #1A1A1A;
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
        
        return frame
    
    def set_classification(self, status):
        """Classification 상태 설정 (True/False만 지원)"""
        if status:
            self.classification_status_label.setText("True")
            self.classification_status_label.setStyleSheet("color: red;")
        else:
            self.classification_status_label.setText("False")
            self.classification_status_label.setStyleSheet("color: blue;")
        
        # 메모리에 즉시 저장 (비동기로 파일 저장)
        self.save_annotation_immediate(status)
        
        # UI가 블로킹되지 않도록 QTimer를 사용하여 비동기로 다음 알람으로 이동
        QTimer.singleShot(1, self.move_to_next_alarm)  # 1ms 후 다음 알람으로 이동 (즉각적)
    
    def move_to_next_alarm(self):
        """다음 알람으로 이동"""
        self.patient_list.select_next_alarm()
    
    def connectSignals(self):
        """시그널 연결"""
        self.patient_list.alarmSelected.connect(self.on_alarm_selected)
        self.submit_button.clicked.connect(self.save_annotation)
        self.true_button.clicked.connect(lambda: self.set_classification(True))
        self.false_button.clicked.connect(lambda: self.set_classification(False))
    
    def on_alarm_selected(self, patient_id, admission_id, date_str, time_str, alarm_data):
        """알람 선택 처리 (최적화)"""
        # 현재 알람 정보만 빠르게 업데이트
        self.current_patient_id = patient_id
        self.current_admission_id = admission_id
        self.current_date_str = date_str
        self.current_time_str = time_str
        self.current_alarm_data = alarm_data
        
        # UI 업데이트는 최소화
        timestamp = f"{date_str} {time_str}"
        alarm_text = f"Patient: {patient_id} | {alarm_data['color']} | {timestamp}"
        
        if 'label' in alarm_data and alarm_data['label']:
            alarm_text += f" | Label: {alarm_data['label']}"
        
        self.selected_alarm_label.setText(alarm_text)
        
        # 색상 스타일
        if alarm_data['color'] in ALARM_COLORS:
            color = ALARM_COLORS[alarm_data['color']]
            self.selected_alarm_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color};")
        
        # annotation 빠른 로드 (캐시에서)
        annotation = patient_data.get_alarm_annotation(patient_id, admission_id, date_str, time_str)
        classification = annotation['classification']
        
        # Classification UI만 업데이트
        if classification is None:
            self.classification_status_label.setText("None")
            self.classification_status_label.setStyleSheet("")
        elif classification:
            self.classification_status_label.setText("True")
            self.classification_status_label.setStyleSheet("color: red;")
        else:
            self.classification_status_label.setText("False")
            self.classification_status_label.setStyleSheet("color: blue;")
        
        # 코멘트 업데이트
        self.comment_text.setText(annotation['comment'])
        
        # 콘텐츠 표시
        self.show_content()
        
        # 무거운 데이터 로드는 지연 실행 (QTimer 사용)
        # 이렇게 하면 UI가 먼저 업데이트되고 데이터는 비동기로 로드
        QTimer.singleShot(1, lambda: self.waveform_manager.load_waveform_data(patient_id, timestamp))
        QTimer.singleShot(1, lambda: self.nursing_manager.load_nursing_record(patient_id, timestamp))
    
    def show_content(self):
        """콘텐츠 표시"""
        # 파형 섹션
        self.waveform_info_label.setVisible(False)
        self.waveform_widget.setVisible(True)
        
        # Numeric 데이터 섹션
        self.numeric_info_label.setVisible(False)
        self.numeric_table.setVisible(True)
        
        # 간호기록 섹션
        self.record_info_label.setVisible(False)
        self.nursing_table.setVisible(True)
    

    
    def hide_content(self):
        """콘텐츠 숨김"""
        # 파형 섹션
        self.waveform_info_label.setVisible(True)
        self.waveform_widget.setVisible(False)
        
        # Numeric 데이터 섹션
        self.numeric_info_label.setVisible(True)
        self.numeric_table.setVisible(False)
        
        # 간호기록 섹션
        self.record_info_label.setVisible(True)
        self.nursing_table.setVisible(False)
    
    def save_annotation_immediate(self, classification):
        """즉시 annotation 저장 (메모리 즉시, 파일은 비동기)"""
        if self.current_patient_id and self.current_time_str:
            comment = self.comment_text.text()
            
            # set_alarm_annotation은 내부적으로 비동기 저장을 사용
            success = patient_data.set_alarm_annotation(
                self.current_patient_id,
                self.current_admission_id,
                self.current_date_str,
                self.current_time_str,
                classification,
                comment
            )
            
            if success:
                # 환자 리스트 통계 즉시 업데이트 (UI는 메모리 기반)
                self.patient_list.refresh_patient_stats()
    
    def save_annotation(self):
        """저장 버튼 클릭 시 annotation 저장 (코멘트 수정 시)"""
        if not self.current_patient_id or not self.current_time_str:
            return
        
        # 현재 classification 상태 가져오기
        classification_text = self.classification_status_label.text()
        if classification_text == "True":
            classification = True
        elif classification_text == "False":
            classification = False
        else:
            classification = None
        
        comment = self.comment_text.text()
        
        success = patient_data.set_alarm_annotation(
            self.current_patient_id,
            self.current_admission_id,
            self.current_date_str,
            self.current_time_str,
            classification,
            comment
        )
        
        if success:
            # 환자 리스트 통계 업데이트
            self.patient_list.refresh_patient_stats()
    
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
    
    app.setStyle("Fusion")  # 모던한 스타일 적용
    
    # Qt 팔레트를 라이트 모드로 강제 설정 (다크 모드 방지)
    from PySide6.QtGui import QPalette
    light_palette = QPalette()
    light_palette.setColor(QPalette.Window, Qt.white)
    light_palette.setColor(QPalette.WindowText, Qt.black)
    light_palette.setColor(QPalette.Base, Qt.white)
    light_palette.setColor(QPalette.AlternateBase, Qt.lightGray)
    light_palette.setColor(QPalette.ToolTipBase, Qt.white)
    light_palette.setColor(QPalette.ToolTipText, Qt.black)
    light_palette.setColor(QPalette.Text, Qt.black)
    light_palette.setColor(QPalette.Button, Qt.white)
    light_palette.setColor(QPalette.ButtonText, Qt.black)
    light_palette.setColor(QPalette.BrightText, Qt.red)
    light_palette.setColor(QPalette.Link, Qt.blue)
    light_palette.setColor(QPalette.Highlight, Qt.blue)
    light_palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(light_palette)
    
    # 애플리케이션 전체에 흰색 배경 강제 적용
    app.setStyleSheet("""
        QApplication {
            background-color: white;
            color: #333333;
        }
        QWidget {
            background-color: white;
            color: #333333;
        }
        QDialog {
            background-color: white;
            color: #333333;
        }
    """)

    window = SICUMonitoring()
    window.show()
    sys.exit(app.exec())
