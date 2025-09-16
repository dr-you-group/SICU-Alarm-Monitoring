import sys
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QWidget, QToolTip, QTableWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor, QFont, QBrush
from data_structure import patient_data

WAVEFORM_HEIGHT = 300

class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(WAVEFORM_HEIGHT)
        self.signals = ["ABP", "Lead-II", "Resp", "Pleth"]
        self.waveform_data = None
        self.decoded_waveforms = {}
        
        # 각 신호별 샘플링 레이트 설정
        self.SAMPLING_RATES = {
            "Lead-II": 500,   # Hz
            "ABP": 125,       # Hz
            "Pleth": 125,     # Hz
            "Resp": 62.5      # Hz
        }
        
        # 마우스 추적 활성화
        self.setMouseTracking(True)
        
        # 호버 정보 저장
        self.hover_info = {
            'x': -1,
            'y': -1,
            'signal': None,
            'value': None,
            'time': None
        }
        
    def set_waveform_data(self, data):
        self.waveform_data = data
        self.decoded_waveforms = {}
        
        # 파형 데이터 처리 (이미 numpy 배열로 변환된 상태)
        if self.waveform_data:
            for signal in self.signals:
                if signal in self.waveform_data:
                    if isinstance(self.waveform_data[signal], np.ndarray):
                        # 이미 numpy 배열로 변환된 데이터 사용
                        self.decoded_waveforms[signal] = self.waveform_data[signal]
                    else:
                        print(f"Unexpected data type for {signal}: {type(self.waveform_data[signal])}")
                        self.decoded_waveforms[signal] = np.array([])
                else:
                    # 해당 신호가 없는 경우 빈 배열
                    self.decoded_waveforms[signal] = np.array([])
        
        self.update()
    
    def get_sampling_rate(self, signal_name):
        """특정 신호의 샘플링 레이트 반환 (Hz)"""
        return self.SAMPLING_RATES.get(signal_name, 250)  # 기본값 250Hz
    
    def get_max_time_duration(self):
        """모든 신호 중 가장 긴 시간 길이 반환 (초)"""
        max_duration = 0
        for signal in self.signals:
            if signal in self.decoded_waveforms and len(self.decoded_waveforms[signal]) > 0:
                sampling_rate = self.get_sampling_rate(signal)
                duration = len(self.decoded_waveforms[signal]) / sampling_rate
                max_duration = max(max_duration, duration)
        return max_duration if max_duration > 0 else 10  # 기본값 10초
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        total_height = self.height()
        signal_height = total_height / len(self.signals)
        
        # 여백 설정 (원래대로 복구)
        LEFT_MARGIN = 80
        RIGHT_MARGIN = 20
        TOP_MARGIN = 10  # 원래대로 복구
        BOTTOM_MARGIN = 30
        
        # 배경색 설정
        painter.fillRect(0, 0, width, total_height, QColor("#2A2A2A"))
        
        # 모든 신호 중 가장 긴 시간 길이 계산 (각 신호의 샘플링 레이트 고려)
        total_time_seconds = self.get_max_time_duration()
        
        for i, signal in enumerate(self.signals):
            signal_top = i * signal_height
            signal_bottom = (i + 1) * signal_height
            y_base = signal_top + signal_height / 2
            
            # 신호 라벨을 각 영역의 가운데에 표시 (왼쪽)
            painter.setPen(QPen(Qt.white, 1))
            painter.drawText(10, y_base + 5, signal)
            
            # Y축 그리기 (각 신호별 왼쪽 축)
            painter.setPen(QPen(Qt.lightGray, 1))
            painter.drawLine(LEFT_MARGIN, signal_top + TOP_MARGIN, 
                           LEFT_MARGIN, signal_bottom - BOTTOM_MARGIN)
            
            # 파형 그리기 영역 정의
            plot_width = width - LEFT_MARGIN - RIGHT_MARGIN
            plot_height = signal_height - TOP_MARGIN - BOTTOM_MARGIN
            plot_top = signal_top + TOP_MARGIN
            plot_bottom = signal_bottom - BOTTOM_MARGIN
            
            # 디코딩된 파형 데이터가 있는 경우에만 그리기
            if signal in self.decoded_waveforms and len(self.decoded_waveforms[signal]) > 0:
                waveform = self.decoded_waveforms[signal]
                
                if len(waveform) > 0:
                    # 파형의 y값 범위 계산
                    min_val = np.min(waveform)
                    max_val = np.max(waveform)
                    value_range = max(max_val - min_val, 1e-5)  # 0으로 나누기 방지
                    
                    # Y축 보조선 먼저 그리기
                    painter.setPen(QPen(Qt.darkGray, 1, Qt.DotLine))
                    painter.drawLine(LEFT_MARGIN, plot_top, width - RIGHT_MARGIN, plot_top)  # 최대값 선
                    painter.drawLine(LEFT_MARGIN, plot_bottom, width - RIGHT_MARGIN, plot_bottom)  # 최소값 선
                    
                    # Y축 눈금 표시 (보조선과 정확히 매칭)
                    painter.setPen(QPen(Qt.lightGray, 1))
                    painter.drawText(45, plot_top + 12, f"{max_val:.1f}")     # 최대값 선 아래에
                    painter.drawText(45, plot_bottom - 5, f"{min_val:.1f}")   # 최소값 선 위에
                    
                    # 파형 그리기
                    painter.setPen(QPen(Qt.green if signal == "ABP" else 
                                      Qt.red if signal == "Lead-II" else
                                      Qt.cyan if signal == "Resp" else
                                      Qt.yellow, 2))
                    
                    path = QPainterPath()
                    points_to_draw = min(len(waveform), plot_width)
                    
                    for j in range(points_to_draw):
                        x = LEFT_MARGIN + j * (plot_width / points_to_draw)
                        # 값을 화면 높이에 맞게 스케일링 (위아래 반전)
                        value_idx = int(j * len(waveform) / points_to_draw)
                        normalized_value = (waveform[value_idx] - min_val) / value_range
                        y = plot_bottom - normalized_value * plot_height
                        
                        if j == 0:
                            path.moveTo(x, y)
                        else:
                            path.lineTo(x, y)
                    
                    painter.drawPath(path)
                    
                else:
                    # 데이터가 비어있을 때 안내 메시지만 표시
                    painter.setPen(QPen(Qt.darkGray, 1))
                    painter.drawText(LEFT_MARGIN + 10, y_base, "No data")
            else:
                # 해당 신호가 없을 때 안내 메시지만 표시 (Y축 라벨 없음)
                painter.setPen(QPen(Qt.darkGray, 1))
                painter.drawText(LEFT_MARGIN + 10, y_base, "No data")
            
            # 신호 간 구분선 그리기
            if i < len(self.signals) - 1:
                painter.setPen(QPen(Qt.gray, 1))
                painter.drawLine(0, signal_bottom, width, signal_bottom)
        
        # X축 (시간축) 그리기 - 맨 아래
        painter.setPen(QPen(Qt.lightGray, 1))
        painter.drawLine(LEFT_MARGIN, total_height - BOTTOM_MARGIN, 
                        width - RIGHT_MARGIN, total_height - BOTTOM_MARGIN)
        
        # X축 눈금 표시 (실제 데이터 길이에 맞게 동적 계산)
        time_marks = 5  # 5개 눈금
        for i in range(time_marks + 1):
            x = LEFT_MARGIN + i * (width - LEFT_MARGIN - RIGHT_MARGIN) / time_marks
            painter.drawLine(x, total_height - BOTTOM_MARGIN, x, total_height - BOTTOM_MARGIN + 5)
            # 시간 라벨 (실제 데이터 길이 기준)
            time_seconds = (i * total_time_seconds) / time_marks
            if total_time_seconds < 1:
                time_label = f"{time_seconds*1000:.0f}ms"  # 1초 미만은 밀리초로
            elif total_time_seconds < 60:
                time_label = f"{time_seconds:.1f}s"  # 1분 미만은 초로
            else:
                time_label = f"{time_seconds/60:.1f}m"  # 1분 이상은 분으로
            painter.drawText(x - 15, total_height - 10, time_label)
        
        # 마우스 호버 정보 표시
        if (self.hover_info['x'] != -1 and self.hover_info['signal'] is not None and 
            self.hover_info['value'] is not None):
            
            # 호버 지점에 수직선 그리기
            painter.setPen(QPen(Qt.white, 1, Qt.DashLine))
            painter.drawLine(self.hover_info['x'], 0, self.hover_info['x'], total_height - BOTTOM_MARGIN)
            
            # 호버 지점에 점 그리기
            painter.setPen(QPen(Qt.white, 3))
            painter.drawPoint(self.hover_info['x'], self.hover_info['y'])
            
            # 툴팁 텍스트 준비
            time_str = f"{self.hover_info['time']:.3f}s" if self.hover_info['time'] is not None else "N/A"
            value_str = f"{self.hover_info['value']:.2f}"
            tooltip_text = f"{self.hover_info['signal']}: {value_str} ({time_str})"
            
            # 툴팅 배경 그리기
            font_metrics = painter.fontMetrics()
            text_width = font_metrics.horizontalAdvance(tooltip_text)
            text_height = font_metrics.height()
            
            tooltip_x = self.hover_info['x'] + 10
            tooltip_y = self.hover_info['y'] - 30
            
            # 화면 밖으로 나가지 않도록 조정
            if tooltip_x + text_width > width - 10:
                tooltip_x = self.hover_info['x'] - text_width - 10
            if tooltip_y < 10:
                tooltip_y = self.hover_info['y'] + 30
                
            # 툴팁 배경
            painter.setPen(QPen(Qt.white, 1))
            painter.setBrush(QColor(0, 0, 0, 180))  # 반투명 검은색
            painter.drawRect(tooltip_x - 5, tooltip_y - text_height, 
                           text_width + 10, text_height + 5)
            
            # 툴팁 텍스트
            painter.setPen(QPen(Qt.white, 1))
            painter.drawText(tooltip_x, tooltip_y, tooltip_text)
    
    def mouseMoveEvent(self, event):
        """마우스 이동 시 해당 위치의 파형 값 계산 (화면 크기 변경에 대한 안정성 보장)"""
        width = self.width()
        total_height = self.height()
        
        if width <= 0 or total_height <= 0:
            return
            
        signal_height = total_height / len(self.signals)
        
        LEFT_MARGIN = 80
        RIGHT_MARGIN = 20
        TOP_MARGIN = 10
        BOTTOM_MARGIN = 30
        
        mouse_x = event.position().x()
        mouse_y = event.position().y()
        
        # 파형 영역 밖이면 호버 정보 초기화
        if mouse_x < LEFT_MARGIN or mouse_x > width - RIGHT_MARGIN:
            self.hover_info = {'x': -1, 'y': -1, 'signal': None, 'value': None, 'time': None}
            self.update()
            return
        
        # 어떤 신호 영역에 있는지 확인
        signal_index = int(mouse_y // signal_height)
        if signal_index < 0 or signal_index >= len(self.signals):
            self.hover_info = {'x': -1, 'y': -1, 'signal': None, 'value': None, 'time': None}
            self.update()
            return
            
        signal_name = self.signals[signal_index]
        
        # 해당 신호에 데이터가 있는지 확인
        if (signal_name not in self.decoded_waveforms or 
            len(self.decoded_waveforms[signal_name]) == 0):
            self.hover_info = {'x': -1, 'y': -1, 'signal': None, 'value': None, 'time': None}
            self.update()
            return
        
        # 마우스 위치에서 데이터 인덱스 계산 (안정적인 좌표 매핑)
        plot_width = max(width - LEFT_MARGIN - RIGHT_MARGIN, 1)  # 0 방지
        relative_x = max(0, min(mouse_x - LEFT_MARGIN, plot_width))  # 범위 제한
        
        waveform = self.decoded_waveforms[signal_name]
        
        # 정규화된 좌표로 데이터 인덱스 계산 (더 정확한 매핑)
        normalized_x = relative_x / plot_width  # 0.0 ~ 1.0
        data_index = int(normalized_x * (len(waveform) - 1))  # 마지막 인덱스 포함
        data_index = max(0, min(data_index, len(waveform) - 1))  # 범위 제한
        
        # 해당 위치의 값 가져오기
        value = waveform[data_index]
        
        # 시간 계산 (해당 신호의 샘플링 레이트 사용)
        sampling_rate = self.get_sampling_rate(signal_name)
        time_seconds = data_index / sampling_rate
        
        # Y 좌표 계산 (화면에서의 실제 위치)
        signal_top = signal_index * signal_height
        signal_bottom = (signal_index + 1) * signal_height
        plot_top = signal_top + TOP_MARGIN
        plot_bottom = signal_bottom - BOTTOM_MARGIN
        plot_height = max(plot_bottom - plot_top, 1)  # 0 방지
        
        # 파형의 최대/최소값으로 정규화 (안정적인 Y 좌표)
        min_val = np.min(waveform)
        max_val = np.max(waveform)
        value_range = max(max_val - min_val, 1e-5)  # 0 방지
        
        normalized_value = (value - min_val) / value_range
        y_pos = plot_bottom - normalized_value * plot_height
        
        # 호버 정보 업데이트 (더 정확한 값들)
        self.hover_info = {
            'x': int(mouse_x),
            'y': int(y_pos),
            'signal': signal_name,
            'value': value,
            'time': time_seconds
        }
        
        self.update()
    
    def leaveEvent(self, event):
        """마우스가 위젯을 벗어났을 때 호버 정보 초기화"""
        self.hover_info = {'x': -1, 'y': -1, 'signal': None, 'value': None, 'time': None}
        self.update()


class WaveformManager:
    def __init__(self, waveform_widget, waveform_info_label, numeric_table=None, numeric_info_label=None):
        self.waveform_widget = waveform_widget
        self.waveform_info_label = waveform_info_label
        self.numeric_table = numeric_table
        self.numeric_info_label = numeric_info_label
    
    def load_waveform_data(self, patient_id, timestamp):
        print(f"파형 데이터 로드: {timestamp}")
        
        # 데이터 구조에서 파형 데이터 가져오기
        waveform_data = patient_data.get_waveform_data(patient_id, timestamp)
        
        # 파형 위젯에 데이터 설정
        self.waveform_widget.set_waveform_data(waveform_data)
        
        # Numeric 데이터 처리
        if self.numeric_table is not None and waveform_data:
            self.load_numeric_data(waveform_data)
    
    def load_numeric_data(self, waveform_data):
        """Numeric 데이터를 8행 고정 테이블에 로드"""
        # 먼저 모든 행 초기화 (3개 컬럼)
        for row in range(8):
            for col in range(3):
                empty_item = QTableWidgetItem("")
                empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsEditable)
                self.numeric_table.setItem(row, col, empty_item)
        
        if not waveform_data or "Numeric" not in waveform_data:
            # Numeric 데이터가 없는 경우
            if self.numeric_info_label:
                self.numeric_info_label.setText("Numeric 데이터가 없습니다")
                self.numeric_info_label.setVisible(True)
            self.numeric_table.setVisible(False)
            return
        
        numeric_data = waveform_data["Numeric"]
        
        # PKL 파일의 Numeric 데이터 구조: 이미 [value, time_diff_sec] 형태
        # 데이터 입력 (최대 8개)
        for row, (parameter, data) in enumerate(list(numeric_data.items())[:8]):
            # 데이터 구조: [value, time_diff_sec]
            if isinstance(data, (list, tuple)) and len(data) >= 2:
                value, time_diff_sec = data[0], data[1]
            else:
                # 단일 값인 경우 time_diff를 0으로 설정
                value = data if not isinstance(data, (list, tuple)) else data[0] if len(data) > 0 else None
                time_diff_sec = 0
            
            # Parameter 컬럼
            param_item = QTableWidgetItem(str(parameter))
            param_item.setFlags(param_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용
            self.numeric_table.setItem(row, 0, param_item)
            
            # Value 컬럼 (NaN/None 처리 추가)
            if pd.isna(value) or value is None:
                value_text = "None"
            elif isinstance(value, float):
                value_text = f"{value:.2f}"
            else:
                value_text = str(value)
            
            value_item = QTableWidgetItem(value_text)
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용
            
            self.numeric_table.setItem(row, 1, value_item)
            
            # Time Diff Sec 컬럼 (NaN/None 처리 추가)
            if pd.isna(time_diff_sec) or time_diff_sec is None:
                time_text = "None"
            elif isinstance(time_diff_sec, float):
                time_text = f"{time_diff_sec:.3f}"
            else:
                time_text = str(time_diff_sec)
            
            time_item = QTableWidgetItem(time_text)
            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)  # 읽기 전용
            self.numeric_table.setItem(row, 2, time_item)
        
        # 테이블 표시
        if self.numeric_info_label:
            self.numeric_info_label.setVisible(False)
        self.numeric_table.setVisible(True)
        
        print(f"Numeric 데이터 로드 완료: {len(numeric_data)}개 파라미터 (8행 3컴럼 테이블)")
