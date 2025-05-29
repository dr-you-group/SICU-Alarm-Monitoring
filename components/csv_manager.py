import os
import csv

class CSVManager:
    def __init__(self, csv_file_path="alarm_annotations.csv"):
        self.csv_file_path = csv_file_path
        self.annotation_data = {}
        self.load_annotations()
    
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
