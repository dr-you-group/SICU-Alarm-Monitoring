"""
JSON 기반 annotation 관리자 (기존 CSV 방식에서 변경)
이제 JSON 파일에 직접 classification과 comment를 저장합니다.
"""

class CSVManager:
    """기존 코드와의 호환성을 위한 더미 클래스"""
    
    def __init__(self, csv_file_path="alarm_annotations.csv"):
        """
        더 이상 CSV 파일을 사용하지 않지만 기존 코드 호환성을 위해 유지
        실제 데이터는 JSON 파일에 저장됩니다.
        """
        self.csv_file_path = csv_file_path
        print("CSV 관리자 초기화됨 (JSON 저장 방식 사용)")
    
    def generate_alarm_id(self, patient_id, date_str, time_str):
        """알람 ID 생성: 환자ID-날짜-시간 형태 (기존 호환성)"""
        return f"{patient_id}-{date_str}-{time_str}"
    
    def load_annotations(self):
        """더미 메서드 - JSON에서 직접 로드됨"""
        print("load_annotations 호출됨 (JSON에서 직접 처리)")
    
    def save_annotations(self):
        """더미 메서드 - JSON에 직접 저장됨"""
        print("save_annotations 호출됨 (JSON에 직접 저장)")
    
    def get_annotation(self, alarm_id):
        """
        기존 호환성을 위한 메서드 - 실제로는 사용하지 않음
        새로운 코드에서는 patient_data.get_alarm_annotation() 사용
        """
        print(f"get_annotation 호출됨: {alarm_id} (JSON 방식 사용 권장)")
        return {'isAlarm': None, 'comment': ''}
    
    def set_annotation(self, alarm_id, is_alarm, comment):
        """
        기존 호환성을 위한 메서드 - 실제로는 사용하지 않음  
        새로운 코드에서는 patient_data.set_alarm_annotation() 사용
        """
        print(f"set_annotation 호출됨: {alarm_id} (JSON 방식 사용 권장)")
