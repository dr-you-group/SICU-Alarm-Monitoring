from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QCheckBox)
from PySide6.QtCore import Qt, QTimer
from data_structure import patient_data
from datetime import datetime, timedelta

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


class NursingRecordManager:
    def __init__(self, nursing_table, record_info_label, parent_window):
        self.nursing_table = nursing_table
        self.record_info_label = record_info_label
        self.parent_window = parent_window
        
        # 컬럼 필터 상태 관리
        self.column_filters = {}  # 각 컬럼에 대한 필터 상태
        self.original_data = []  # 원본 데이터 저장
        self.filter_dialog = None  # 현재 열린 다이얼로그 추적
        self.column_widths = {}  # 컬럼 너비 저장
    
    def load_nursing_record(self, patient_id, timestamp):
        print(f"간호기록 로드: {timestamp}")
        
        # 기존 간호기록 지우기
        self.clear_nursing_records()
        
        # 데이터 구조에서 선택된 알람 시간 기준 ±30분 범위의 간호기록 가져오기
        records = patient_data.get_nursing_records_for_alarm(patient_id, timestamp)
        
        # 간호기록 테이블에 데이터 추가
        self.setup_nursing_table(records)
    
    def clear_nursing_records(self):
        """간호기록 테이블 초기화"""
        self.nursing_table.setRowCount(0)
        self.nursing_table.setColumnCount(0)
    
    def setup_nursing_table(self, records):
        """간호기록 테이블 설정 및 데이터 추가 (스크롤 방식)"""
        if not records:
            return
        
        # 기존 컬럼 너비 저장
        if self.nursing_table.columnCount() > 0:
            for i in range(self.nursing_table.columnCount()):
                header_item = self.nursing_table.horizontalHeaderItem(i)
                if header_item:
                    column_name = header_item.text()
                    self.column_widths[column_name] = self.nursing_table.columnWidth(i)
        
        # 컬럼 설정 (시행일시를 맨 앞으로)
        columns = [
            "시행일시",  # 맨 앞
            "간호진단프로토콜(코드명)",
            "간호중재(코드명)",
            "간호활동(코드명)", 
            "간호속성코드(코드명)",
            "속성",
            "Duty(코드명)"
        ]
        
        self.nursing_table.setColumnCount(len(columns))
        self.nursing_table.setHorizontalHeaderLabels(columns)
        self.nursing_table.setRowCount(len(records))
        
        # 데이터 추가
        for row_idx, record in enumerate(records):
            for col_idx, column in enumerate(columns):
                value = record.get(column, "")
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용
                self.nursing_table.setItem(row_idx, col_idx, item)
        
        # 컬럼 크기 조정 (마우스로 조절 가능)
        header = self.nursing_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)  # 모든 컬럼 마우스로 조절 가능
        header.setStretchLastSection(True)  # 마지막 컬럼은 남은 공간 채우기
        
        # 저장된 컬럼 너비 복원 또는 기본 너비 설정
        default_widths = {
            "시행일시": 140,
            "간호진단프로토콜(코드명)": 180,
            "간호중재(코드명)": 180,
            "간호활동(코드명)": 180, 
            "간호속성코드(코드명)": 180,
            "속성": 120,
            "Duty(코드명)": 120
        }
        
        for i, column_name in enumerate(columns):
            if column_name in self.column_widths:
                self.nursing_table.setColumnWidth(i, self.column_widths[column_name])
            else:
                self.nursing_table.setColumnWidth(i, default_widths[column_name])
        
        # 시행일시 기준으로 정렬
        self.nursing_table.sortByColumn(0, Qt.AscendingOrder)
        
        # 원본 데이터 저장
        self.original_data = records
        
        # 헤더 컨텍스트 메뉴 설정 (엑셀 스타일 필터)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_column_filter_menu)
        
        # 컬럼 필터 초기화
        self.column_filters = {}
        for i in range(self.nursing_table.columnCount()):
            column_name = self.nursing_table.horizontalHeaderItem(i).text()
            self.column_filters[column_name] = "ALL_SELECTED"
        
        # 컬럼 너비 변경 시 저장
        header.sectionResized.connect(self.save_column_width)
        
        print(f"간호기록 로드 완료: {len(records)}개 기록 (±30분 범위, 스크롤 방식)")
    
    def save_column_width(self, logical_index, old_size, new_size):
        """컬럼 너비 변경 시 저장"""
        header_item = self.nursing_table.horizontalHeaderItem(logical_index)
        if header_item:
            column_name = header_item.text()
            self.column_widths[column_name] = new_size
            print(f"컬럼 '{column_name}' 너비 저장: {new_size}")
    
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
        
        # 해당 컬럼의 고유한 값들 수집
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
        self.filter_dialog = ExcelColumnFilterDialog(column_name, unique_values, current_selected, self.parent_window)
        
        # 다이얼로그가 닫힘 때 참조 제거
        self.filter_dialog.finished.connect(lambda: setattr(self, 'filter_dialog', None))
        
        # 다이얼로그를 클릭한 위치 근처에 표시 (화면 범위 내에서)
        global_pos = header.mapToGlobal(position)
        dialog_x = min(global_pos.x(), self.parent_window.screen().availableGeometry().width() - self.filter_dialog.width())
        dialog_y = min(global_pos.y() + 30, self.parent_window.screen().availableGeometry().height() - self.filter_dialog.height())
        self.filter_dialog.move(dialog_x, dialog_y)
        
        # 비모달로 열기 (스플리터 사용 가능)
        self.filter_dialog.show()
    
    def apply_column_filters(self):
        """컬럼 필터 적용"""
        for row in range(self.nursing_table.rowCount()):
            show_row = True
            
            # 각 컬럼에 대한 필터 확인
            for column_name, selected_values in self.column_filters.items():
                # 컬럼 인덱스 찾기
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
