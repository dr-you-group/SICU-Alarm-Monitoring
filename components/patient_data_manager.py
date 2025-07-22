from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from data_structure import patient_data, ALARM_COLORS
from .alarm_filters import default_alarm_filter, AlarmFilterConfig

TIMELINE_HEIGHT = 40

class TimelineWidget(QWidget):
    alarmSelected = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(TIMELINE_HEIGHT)
        self.alarms = []
        self.selected_alarm_index = -1
        
        # 키보드 포커스 활성화
        self.setFocusPolicy(Qt.StrongFocus)
        
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
        
        # 포커스 상태일 때 테두리 표시
        if self.hasFocus() and self.alarms:
            painter.setPen(QPen(QColor("#0078D4"), 2))  # 파란색 테두리
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(1, 1, width - 2, height - 2)
        
        # 24시간 눈금선 그리기
        painter.setPen(QPen(Qt.white, 1, Qt.DotLine))
        for i in range(1, 24):
            x = (width - 10) * (i / 24) + 5
            painter.drawLine(x, 0, x, height)
        
        # 알람들 그리기
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
        
        # 키보드 사용법 히노트 (알람이 있고 포커스가 있을 때)
        if self.alarms and self.hasFocus():
            painter.setPen(QPen(QColor("#888888"), 1))
            hint_text = "← → 알람 이동"
            painter.drawText(width - 80, height - 5, hint_text)
    
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
            # 포커스 설정 (키보드 입력 가능)
            self.setFocus()
            # 새로운 메서드 사용으로 통일
            self.select_alarm_by_index(closest_alarm)
    
    def keyPressEvent(self, event):
        """키보드 이벤트 처리 (방향키로 알람 이동)"""
        if not self.alarms:  # 알람이 없으면 무시
            super().keyPressEvent(event)
            return
            
        if event.key() == Qt.Key_Right:
            # 다음 알람으로 이동
            self.select_next_alarm()
            event.accept()
        elif event.key() == Qt.Key_Left:
            # 이전 알람으로 이동
            self.select_previous_alarm()
            event.accept()
        elif event.key() in [Qt.Key_Up, Qt.Key_Down]:
            # 위/아래 화살표는 무시 (다른 컴포넌트로 포커스 이동)
            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
    
    def select_next_alarm(self):
        """다음 알람 선택"""
        if not self.alarms:
            return
            
        if self.selected_alarm_index < len(self.alarms) - 1:
            self.selected_alarm_index += 1
        else:
            # 마지막 알람에서 다음을 누르면 첫 번째로 순환
            self.selected_alarm_index = 0
            
        self.update()
        self.alarmSelected.emit(self.alarms[self.selected_alarm_index])
        print(f"다음 알람 선택: {self.alarms[self.selected_alarm_index]['color']} ({self.alarms[self.selected_alarm_index]['time']})")
    
    def select_previous_alarm(self):
        """이전 알람 선택"""
        if not self.alarms:
            return
            
        if self.selected_alarm_index > 0:
            self.selected_alarm_index -= 1
        else:
            # 첫 번째 알람에서 이전을 누르면 마지막으로 순환
            self.selected_alarm_index = len(self.alarms) - 1
            
        self.update()
        self.alarmSelected.emit(self.alarms[self.selected_alarm_index])
        print(f"이전 알람 선택: {self.alarms[self.selected_alarm_index]['color']} ({self.alarms[self.selected_alarm_index]['time']})")
    
    def select_alarm_by_index(self, index):
        """인덱스로 알람 선택 (마우스 클릭 또는 외부 호출용)"""
        if 0 <= index < len(self.alarms):
            self.selected_alarm_index = index
            self.update()
            self.alarmSelected.emit(self.alarms[index])
            print(f"알람 선택: {self.alarms[index]['color']} ({self.alarms[index]['time']})")
            return True
        return False


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
        raw_alarms = patient_data.get_alarms_for_date(self.current_patient_id, self.current_admission_id, date_str)
        
        # 필터 순차적 적용
        filtered_alarms = raw_alarms
        filter_steps = []
        
        # 1. 간호기록 필터 적용 (설정에서 활성화된 경우)
        if AlarmFilterConfig.is_nursing_record_filter_enabled():
            before_count = len(filtered_alarms)
            filtered_alarms = default_alarm_filter.filter_alarms_with_nursing_records(
                self.current_patient_id, date_str, filtered_alarms
            )
            after_count = len(filtered_alarms)
            filter_steps.append(f"간호기록 필터: {before_count}개 → {after_count}개")
        
        # 2. 기술적 알람 필터 적용 (설정에서 활성화된 경우)
        if AlarmFilterConfig.is_technical_alarm_filter_enabled():
            before_count = len(filtered_alarms)
            filtered_alarms = default_alarm_filter.filter_technical_alarms(
                self.current_patient_id, date_str, filtered_alarms
            )
            after_count = len(filtered_alarms)
            filter_steps.append(f"기술적 알람 필터: {before_count}개 → {after_count}개")
        
        # 필터링 결과 요약
        if filter_steps:
            print(f"알람 필터링 완료: 원본 {len(raw_alarms)}개 → 최종 {len(filtered_alarms)}개")
            for step in filter_steps:
                print(f"  - {step}")
        else:
            print(f"알람 필터링 비활성화: {len(filtered_alarms)}개 알람 모두 표시")
        
        # 타임라인 위젯에 알람 데이터 설정
        self.timeline_widget.set_alarms(filtered_alarms)
        
        # 알람이 있으면 첫 번째 알람 자동 선택 및 포커스 설정
        if filtered_alarms:
            # 타임라인 위젯에 포커스 설정 (키보드 입력 가능)
            self.timeline_widget.setFocus()
            # 첫 번째 알람 자동 선택
            self.timeline_widget.select_alarm_by_index(0)
        else:
            # 알람이 없으면 기본 상태로 설정
            if len(raw_alarms) > 0:
                # 원본 알람은 있었지만 필터링으로 제거된 경우
                enabled_filters = AlarmFilterConfig.get_enabled_filters_summary()
                self.update_selected_alarm("None", "", None, f"필터링으로 인해 표시할 알람이 없습니다\n{enabled_filters}")
            else:
                # 원본 알람이 아예 없는 경우
                self.update_selected_alarm("None", "", None, None)
    
    def update_selected_alarm(self, color, time_str, timestamp=None, alarm_label=None):
        self.selected_alarm_color = color
        
        if color == "None":
            if self.date_combo.currentText():
                alarm_text = f"선택 알람: None ({self.date_combo.currentText()})"
            else:
                alarm_text = "날짜를 선택해주세요"
        else:
            if timestamp:
                alarm_text = f"선택 알람: {color} ({timestamp})"
            else:
                date_str = self.date_combo.currentText()
                alarm_text = f"선택 알람: {color} ({date_str} {time_str})"
        
        # AlarmLabel이 있으면 추가로 표시
        if alarm_label and alarm_label.strip():
            alarm_text += f"\nAlarmLabel: {alarm_label}"
        
        self.alarm_info_label.setText(alarm_text)
        self.update_alarm_info_style()
        
        print(f"선택 알람 정보 업데이트: {color}")
        if alarm_label:
            print(f"AlarmLabel: {alarm_label}")
    
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
