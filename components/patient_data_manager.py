from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from data_structure import patient_data, ALARM_COLORS

TIMELINE_HEIGHT = 40

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


class PatientDataManager:
    def __init__(self, patient_id_input, admission_combo, date_combo, alarm_info_label, timeline_widget):
        self.patient_id_input = patient_id_input
        self.admission_combo = admission_combo
        self.date_combo = date_combo
        self.alarm_info_label = alarm_info_label
        self.timeline_widget = timeline_widget
        
        # 상태 변수들
        self.current_patient_id = ""
        self.current_admission_id = ""
        self.has_selected_date = False
        self.has_selected_alarm = False
        self.selected_alarm_color = "None"
    
    def search_patient(self):
        patient_id = self.patient_id_input.text()
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
    
    def date_selected(self, date_str):
        if not date_str:
            return
            
        self.has_selected_date = True
        
        # 날짜 선택 시 알람 선택 상태 초기화
        self.has_selected_alarm = False
        
        # 선택한 날짜에 대한 알람 데이터 로드
        self.load_alarm_data_for_date(date_str)
    
    def load_alarm_data_for_date(self, date_str):
        print(f"날짜 {date_str}의 알람 데이터 로드")
        
        # 데이터 구조에서 알람 정보 가져오기
        alarms = patient_data.get_alarms_for_date(self.current_patient_id, self.current_admission_id, date_str)
        
        # 타임라인 위젯에 알람 데이터 설정
        self.timeline_widget.set_alarms(alarms)
        
        # 날짜 선택 시 기본 알람 정보는 "None"으로 설정
        self.update_selected_alarm("None", "")
    
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
        
        self.update_alarm_info_style()
        
        print(f"선택 알람 정보 업데이트: {color}")
    
    def update_alarm_info_style(self):
        if self.selected_alarm_color in ALARM_COLORS:
            color = ALARM_COLORS[self.selected_alarm_color]
            self.alarm_info_label.setStyleSheet(f"color: {color};")
    
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
