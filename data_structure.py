from datetime import datetime, timedelta
import base64
import random
import numpy as np

ALARM_COLORS = {
    "White": "#FFFFFF",
    "SilentCyan": "#00FFFF",
    "Cyan": "#00FFFF",
    "ShortYellow": "#FFFF00",
    "Yellow": "#FFFF00",
    "Red": "#FF0000",
    "None": "#808080"
}

class PatientData:
    def __init__(self):
        # 환자 데이터 (한 명만 정의)
        self.patients = {
            "1160 4980": {
                "admission_period": "24/04/01 — 25/08/09",
                "alarms": {
                    "2025-05-01": [
                        {"time": "02:15:30", "color": "Red", "id": "2025-05-01-02:15:30-1160 4980", "timestamp": "2025-05-01 02:15:30"},
                        {"time": "05:45:12", "color": "Yellow", "id": "2025-05-01-05:45:12-1160 4980", "timestamp": "2025-05-01 05:45:12"},
                        {"time": "09:22:05", "color": "SilentCyan", "id": "2025-05-01-09:22:05-1160 4980", "timestamp": "2025-05-01 09:22:05"},
                        {"time": "14:08:45", "color": "White", "id": "2025-05-01-14:08:45-1160 4980", "timestamp": "2025-05-01 14:08:45"},
                        {"time": "19:35:22", "color": "Red", "id": "2025-05-01-19:35:22-1160 4980", "timestamp": "2025-05-01 19:35:22"}
                    ],
                    "2025-05-02": [
                        {"time": "01:30:20", "color": "Cyan", "id": "2025-05-02-01:30:20-1160 4980", "timestamp": "2025-05-02 01:30:20"},
                        {"time": "07:12:43", "color": "ShortYellow", "id": "2025-05-02-07:12:43-1160 4980", "timestamp": "2025-05-02 07:12:43"},
                        {"time": "12:29:24", "color": "Red", "id": "2025-05-02-12:29:24-1160 4980", "timestamp": "2025-05-02 12:29:24"},
                        {"time": "18:57:10", "color": "Yellow", "id": "2025-05-02-18:57:10-1160 4980", "timestamp": "2025-05-02 18:57:10"}
                    ],
                    "2025-05-03": [
                        {"time": "04:10:15", "color": "White", "id": "2025-05-03-04:10:15-1160 4980", "timestamp": "2025-05-03 04:10:15"},
                        {"time": "10:25:33", "color": "Red", "id": "2025-05-03-10:25:33-1160 4980", "timestamp": "2025-05-03 10:25:33"},
                        {"time": "16:45:18", "color": "SilentCyan", "id": "2025-05-03-16:45:18-1160 4980", "timestamp": "2025-05-03 16:45:18"},
                        {"time": "22:05:49", "color": "Yellow", "id": "2025-05-03-22:05:49-1160 4980", "timestamp": "2025-05-03 22:05:49"}
                    ]
                },
                
                # Base64로 인코딩된 파형 데이터
                "waveforms": {
                    "2025-05-01 02:15:30": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-01 05:45:12": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-01 09:22:05": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-01 14:08:45": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-01 19:35:22": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-02 01:30:20": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-02 07:12:43": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-02 12:29:24": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-02 18:57:10": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-03 04:10:15": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-03 10:25:33": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-03 16:45:18": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    },
                    "2025-05-03 22:05:49": {
                        "ABP": self._generate_base64_waveform(),
                        "Lead-II": self._generate_base64_waveform(),
                        "Resp": self._generate_base64_waveform(),
                        "Pleth": self._generate_base64_waveform()
                    }
                },

                # 직접 정의된 간호기록 데이터 (단일 객체, 배열 아님)
                "nursing_records": {
                    "2025-05-01 01:55:22": {
                        "간호중재(코드명)": "약물 투여(A24.3)",
                        "간호활동(코드명)": "정맥주사(B62.1)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-01 01:55:22"
                    },
                    "2025-05-01 02:10:15": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "PRN",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-01 02:10:15"
                    },
                    "2025-05-01 02:18:45": {
                        "간호중재(코드명)": "통증 관리(A18.2)",
                        "간호활동(코드명)": "통증 사정(B32.4)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "PRN",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-01 02:18:45"
                    },
                    "2025-05-01 02:30:10": {
                        "간호중재(코드명)": "수액 관리(A15.6)",
                        "간호활동(코드명)": "수액 주입속도 조절(B25.8)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-01 02:30:10"
                    },
                    "2025-05-01 05:25:00": {
                        "간호중재(코드명)": "피부 관리(A33.7)",
                        "간호활동(코드명)": "드레싱 교환(B42.9)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-01 05:25:00"
                    },
                    "2025-05-01 05:42:30": {
                        "간호중재(코드명)": "호흡 관리(A09.4)",
                        "간호활동(코드명)": "산소요법(B19.3)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "응급",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-01 05:42:30"
                    },
                    "2025-05-01 05:48:15": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "응급",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-01 05:48:15"
                    },
                    "2025-05-01 05:55:40": {
                        "간호중재(코드명)": "약물 투여(A24.3)",
                        "간호활동(코드명)": "정맥주사(B62.1)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "응급",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-01 05:55:40"
                    },
                    "2025-05-01 06:05:10": {
                        "간호중재(코드명)": "의사 호출(A42.1)",
                        "간호활동(코드명)": "환자 상태 보고(B70.3)",
                        "간호속성코드(코드명)": "의뢰(C21)",
                        "속성": "응급",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-01 06:05:10"
                    },
                    "2025-05-01 09:00:20": {
                        "간호중재(코드명)": "영양 관리(A21.8)",
                        "간호활동(코드명)": "영양 상태 사정(B38.6)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Day(D1)",
                        "시행일시": "2025-05-01 09:00:20"
                    },
                    "2025-05-01 09:15:30": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Day(D1)",
                        "시행일시": "2025-05-01 09:15:30"
                    },
                    "2025-05-01 09:25:45": {
                        "간호중재(코드명)": "약물 투여(A24.3)",
                        "간호활동(코드명)": "정맥주사(B62.1)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Day(D1)",
                        "시행일시": "2025-05-01 09:25:45"
                    },
                    "2025-05-01 09:40:10": {
                        "간호중재(코드명)": "수액 관리(A15.6)",
                        "간호활동(코드명)": "수액 주입속도 조절(B25.8)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Day(D1)",
                        "시행일시": "2025-05-01 09:40:10"
                    },
                    "2025-05-01 13:50:20": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Day(D1)",
                        "시행일시": "2025-05-01 13:50:20"
                    },
                    "2025-05-01 14:05:30": {
                        "간호중재(코드명)": "약물 투여(A24.3)",
                        "간호활동(코드명)": "정맥주사(B62.1)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Day(D1)",
                        "시행일시": "2025-05-01 14:05:30"
                    },
                    "2025-05-01 14:15:45": {
                        "간호중재(코드명)": "통증 관리(A18.2)",
                        "간호활동(코드명)": "통증 사정(B32.4)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "PRN",
                        "Duty(코드명)": "Day(D1)",
                        "시행일시": "2025-05-01 14:15:45"
                    },
                    "2025-05-01 19:15:00": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Evening(D2)",
                        "시행일시": "2025-05-01 19:15:00"
                    },
                    "2025-05-01 19:30:20": {
                        "간호중재(코드명)": "약물 투여(A24.3)",
                        "간호활동(코드명)": "정맥주사(B62.1)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "PRN",
                        "Duty(코드명)": "Evening(D2)",
                        "시행일시": "2025-05-01 19:30:20"
                    },
                    "2025-05-01 19:40:15": {
                        "간호중재(코드명)": "수액 관리(A15.6)",
                        "간호활동(코드명)": "수액 주입속도 조절(B25.8)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Evening(D2)",
                        "시행일시": "2025-05-01 19:40:15"
                    },
                    "2025-05-01 19:55:30": {
                        "간호중재(코드명)": "호흡 관리(A09.4)",
                        "간호활동(코드명)": "산소요법(B19.3)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "PRN",
                        "Duty(코드명)": "Evening(D2)",
                        "시행일시": "2025-05-01 19:55:30"
                    },
                    "2025-05-02 01:10:00": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-02 01:10:00"
                    },
                    "2025-05-02 01:25:15": {
                        "간호중재(코드명)": "약물 투여(A24.3)",
                        "간호활동(코드명)": "정맥주사(B62.1)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-02 01:25:15"
                    },
                    "2025-05-02 01:35:40": {
                        "간호중재(코드명)": "통증 관리(A18.2)",
                        "간호활동(코드명)": "통증 사정(B32.4)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "PRN",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-02 01:35:40"
                    },
                    "2025-05-02 06:50:10": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-02 06:50:10"
                    },
                    "2025-05-02 12:10:15": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Day(D1)",
                        "시행일시": "2025-05-02 12:10:15"
                    },
                    "2025-05-02 18:35:20": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Evening(D2)",
                        "시행일시": "2025-05-02 18:35:20"
                    },
                    "2025-05-03 03:50:20": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Night(D3)",
                        "시행일시": "2025-05-03 03:50:20"
                    },
                    "2025-05-03 10:05:40": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Day(D1)",
                        "시행일시": "2025-05-03 10:05:40"
                    },
                    "2025-05-03 16:25:20": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Evening(D2)",
                        "시행일시": "2025-05-03 16:25:20"
                    },
                    "2025-05-03 21:45:20": {
                        "간호중재(코드명)": "환자 상태 확인(A12.5)",
                        "간호활동(코드명)": "활력징후 측정(B15.7)",
                        "간호속성코드(코드명)": "수행(C12)",
                        "속성": "정규",
                        "Duty(코드명)": "Evening(D2)",
                        "시행일시": "2025-05-03 21:45:20"
                    }
                },
            }
        }
    
    def _generate_base64_waveform(self):
        # 예시로 랜덤 파형 데이터 생성 후 base64로 인코딩
        # 실제 환경에서는 미리 인코딩된 문자열을 사용할 것
        sample_count = 200
        t = np.linspace(0, 4*np.pi, sample_count)
        amplitude = random.uniform(0.5, 2.0)
        frequency = random.uniform(1.0, 3.0)
        noise = np.random.normal(0, 0.1, sample_count)
        
        # 기본 사인파 생성
        waveform = amplitude * np.sin(frequency * t) + noise
        
        # float 배열을 bytes로 변환
        waveform_bytes = waveform.tobytes()
        
        # base64로 인코딩
        base64_str = base64.b64encode(waveform_bytes).decode('utf-8')
        
        return base64_str
    
    def get_patient_info(self, patient_id):
        return self.patients.get(patient_id)
    
    def get_available_dates(self, patient_id):
        if patient_id not in self.patients:
            return []
        
        return sorted(list(self.patients[patient_id]["alarms"].keys()))
    
    def get_alarms_for_date(self, patient_id, date_str):
        if patient_id not in self.patients:
            return []
        
        return self.patients[patient_id]["alarms"].get(date_str, [])
    
    def get_waveform_data(self, patient_id, timestamp):
        if patient_id not in self.patients:
            return None
        
        return self.patients[patient_id]["waveforms"].get(timestamp)
    
    def get_nursing_records_for_alarm(self, patient_id, timestamp_str):
        if patient_id not in self.patients:
            return []
        
        try:
            # 알람 타임스탬프 파싱
            alarm_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            
            # 시간 범위 정의 (±30분)
            start_time = alarm_time - timedelta(minutes=30)
            end_time = alarm_time + timedelta(minutes=30)
            
            filtered_records = []
            
            # 모든 간호기록 타임스탬프에 대해 시간 범위 내에 있는지 확인
            for record_time_str, record in self.patients[patient_id]["nursing_records"].items():
                record_time = datetime.strptime(record_time_str, "%Y-%m-%d %H:%M:%S")
                
                if start_time <= record_time <= end_time:
                    filtered_records.append(record)
            
            # 시행일시 기준으로 정렬
            filtered_records.sort(key=lambda x: x["시행일시"])
            
            return filtered_records
        except Exception as e:
            print(f"Error getting nursing records: {e}")
            return []

    @staticmethod
    def decode_base64_waveform(base64_str):
        """
        base64로 인코딩된 파형 데이터를 디코딩하여 numpy 배열로 반환
        """
        try:
            # base64 문자열을 바이트로 디코딩
            binary_data = base64.b64decode(base64_str)
            
            # 바이트를 float64 numpy 배열로 변환 (실제 데이터 형식에 맞게 조정 필요)
            waveform = np.frombuffer(binary_data, dtype=np.float64)
            
            return waveform
        except Exception as e:
            print(f"Error decoding base64 waveform: {e}")
            return np.array([])  # 오류 시 빈 배열 반환

# 전역 인스턴스
patient_data = PatientData()
