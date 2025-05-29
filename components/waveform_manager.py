import sys
import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from data_structure import patient_data

WAVEFORM_HEIGHT = 300

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


class WaveformManager:
    def __init__(self, waveform_widget, waveform_info_label):
        self.waveform_widget = waveform_widget
        self.waveform_info_label = waveform_info_label
    
    def load_waveform_data(self, patient_id, timestamp):
        print(f"파형 데이터 로드: {timestamp}")
        
        # 데이터 구조에서 파형 데이터 가져오기
        waveform_data = patient_data.get_waveform_data(patient_id, timestamp)
        
        # 파형 위젯에 데이터 설정
        self.waveform_widget.set_waveform_data(waveform_data)
