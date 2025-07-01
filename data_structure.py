#!/usr/bin/env python3
"""
JSON 파일 기반 환자 데이터 관리 클래스
기존의 하드코딩된 데이터 대신 JSON 파일에서 데이터를 로드하여 사용
"""

import json
import base64
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# 알람 색상 상수는 그대로 유지
ALARM_COLORS = {
    "Red": "#FF0000",
    "Yellow": "#FFFF00",
    "ShortYellow": "#FFFF00",
    "SevereCyan": "#00FFFF",
    "Cyan": "#00FFFF",
    "SilentCyan": "#00FFFF",
    "White": "#FFFFFF",
}

class PatientDataJson:
    """JSON 파일 기반 환자 데이터 관리 클래스"""
    
    def __init__(self, data_directory: str = "DATA"):
        """
        Args:
            data_directory: 환자 데이터 JSON 파일들이 저장된 디렉토리 경로
        """
        self.data_dir = Path(data_directory)
        self.loaded_patients = {}  # 캐시된 환자 데이터
        
        # DATA 디렉토리 확인
        if not self.data_dir.exists():
            print(f"DATA 디렉토리가 존재하지 않습니다: {self.data_dir}")
            self.data_dir.mkdir(exist_ok=True)
            print(f"DATA 디렉토리를 생성했습니다: {self.data_dir}")
    
    def _load_patient_data(self, patient_id: str) -> Optional[Dict]:
        """특정 환자 ID의 JSON 파일에서 데이터를 로드"""
        # 이미 로드된 환자 데이터가 있으면 반환
        if patient_id in self.loaded_patients:
            return self.loaded_patients[patient_id]
        
        # 환자 JSON 파일 경로
        patient_file = self.data_dir / f"{patient_id}.json"
        
        try:
            with open(patient_file, 'r', encoding='utf-8') as f:
                patient_data = json.load(f)
            
            # 캐시에 저장
            self.loaded_patients[patient_id] = patient_data
            print(f"환자 데이터 로드 완료: {patient_file}")
            return patient_data
            
        except FileNotFoundError:
            print(f"환자 파일을 찾을 수 없습니다: {patient_file}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류 ({patient_file}): {e}")
            return None
    
    def reload_patient_data(self, patient_id: str):
        """특정 환자의 JSON 파일을 다시 로드 (런타임 중 파일이 변경된 경우)"""
        if patient_id in self.loaded_patients:
            del self.loaded_patients[patient_id]
        return self._load_patient_data(patient_id)
    
    def save_patient_data(self, patient_id: str, backup: bool = True):
        """특정 환자의 데이터를 JSON 파일에 저장"""
        if patient_id not in self.loaded_patients:
            print(f"로드되지 않은 환자 데이터: {patient_id}")
            return False
        
        patient_file = self.data_dir / f"{patient_id}.json"
        
        try:
            # 백업 생성
            if backup and patient_file.exists():
                backup_path = patient_file.with_suffix('.json.backup')
                import shutil
                shutil.copy2(patient_file, backup_path)
                print(f"백업 파일 생성: {backup_path}")
            
            # JSON 파일 저장
            with open(patient_file, 'w', encoding='utf-8') as f:
                json.dump(self.loaded_patients[patient_id], f, ensure_ascii=False, indent=4)
            
            print(f"환자 데이터 저장 완료: {patient_file}")
            return True
            
        except Exception as e:
            print(f"데이터 저장 오류 ({patient_id}): {e}")
            return False
    
    def get_patient_info(self, patient_id: str) -> Optional[Dict]:
        """환자 정보 반환"""
        patient_data = self._load_patient_data(patient_id)
        return patient_data
    
    def get_admission_periods(self, patient_id: str) -> List[Dict]:
        """환자의 입원 기간 목록 반환"""
        patient_data = self._load_patient_data(patient_id)
        if not patient_data:
            return []
        
        return patient_data.get("admission_periods", [])
    
    def get_available_dates(self, patient_id: str, admission_id: str) -> List[str]:
        """특정 입원 기간의 알람 데이터가 있는 날짜 목록 반환"""
        patient_data = self._load_patient_data(patient_id)
        if not patient_data:
            return []
        
        alarms = patient_data.get("alarms", {})
        if admission_id not in alarms:
            return []
        
        return sorted(list(alarms[admission_id].keys()))
    
    def get_alarms_for_date(self, patient_id: str, admission_id: str, date_str: str) -> List[Dict]:
        """특정 날짜의 알람 목록 반환"""
        patient_data = self._load_patient_data(patient_id)
        if not patient_data:
            return []
        
        alarms = patient_data.get("alarms", {})
        if admission_id not in alarms:
            return []
        
        return alarms[admission_id].get(date_str, [])
    
    def get_waveform_data(self, patient_id: str, timestamp: str) -> Optional[Dict]:
        """특정 타임스탬프의 파형 데이터 반환 (배열 또는 base64 형태 모두 지원)"""
        patient_data = self._load_patient_data(patient_id)
        if not patient_data:
            print(f"DEBUG: 환자 데이터를 찾을 수 없음: {patient_id}")
            return None
        
        waveforms = patient_data.get("waveforms", {})
        print(f"DEBUG: 전체 waveform 타임스탬프들: {list(waveforms.keys())[:5]}...")  # 처음 5개만 표시
        
        raw_data = waveforms.get(timestamp)
        print(f"DEBUG: 타임스탬프 '{timestamp}'에서 가져온 raw_data 키들: {list(raw_data.keys()) if raw_data else 'None'}")
        
        if not raw_data:
            print(f"DEBUG: 타임스탬프 '{timestamp}'에 대한 데이터가 없음")
            return None
            
        # 파형 데이터를 numpy 배열로 변환하여 반환
        processed_data = {}
        for signal_name, signal_data in raw_data.items():
            # AlarmLabel 데이터는 맨 먼저 처리 (문자열 또는 리스트 그대로 유지)
            if signal_name == "AlarmLabel":
                print(f"DEBUG: AlarmLabel 원본 데이터: {signal_data} (타입: {type(signal_data)})")
                processed_data[signal_name] = signal_data
                continue
                
            # Numeric 데이터는 dict 형태로 그대로 유지
            if signal_name == "Numeric":
                if isinstance(signal_data, dict):
                    processed_data[signal_name] = signal_data
                else:
                    print(f"Numeric 데이터가 예상과 다른 형태입니다: {type(signal_data)}")
                    processed_data[signal_name] = {}
                continue
            
            # 파형 신호들은 numpy 배열로 변환
            if isinstance(signal_data, str):
                # base64 문자열인 경우 디코딩
                try:
                    processed_data[signal_name] = self.decode_base64_waveform(signal_data)
                except Exception as e:
                    print(f"Base64 디코딩 실패 ({signal_name}): {e}")
                    processed_data[signal_name] = np.array([])
            elif isinstance(signal_data, list):
                # 이미 배열 형태인 경우 numpy 배열로 변환
                try:
                    processed_data[signal_name] = np.array(signal_data, dtype=np.float64)
                except Exception as e:
                    print(f"배열 변환 실패 ({signal_name}): {e}")
                    processed_data[signal_name] = np.array([])
            elif isinstance(signal_data, np.ndarray):
                # 이미 numpy 배열인 경우 그대로 사용
                processed_data[signal_name] = signal_data
            else:
                print(f"지원되지 않는 데이터 타입 ({signal_name}): {type(signal_data)}")
                processed_data[signal_name] = np.array([])
                
        return processed_data
    
    def get_nursing_records_for_alarm(self, patient_id: str, timestamp_str: str) -> List[Dict]:
        """알람 시간 기준 ±30분 내의 간호기록 반환"""
        patient_data = self._load_patient_data(patient_id)
        if not patient_data:
            return []
        
        try:
            # 알람 타임스탬프 파싱
            alarm_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            
            # 시간 범위 정의 (±30분)
            start_time = alarm_time - timedelta(minutes=30)
            end_time = alarm_time + timedelta(minutes=30)
            
            filtered_records = []
            
            # 모든 간호기록 타임스탬프에 대해 시간 범위 내에 있는지 확인
            nursing_records = patient_data.get("nursing_records", {})
            for record_time_str, records in nursing_records.items():
                record_time = datetime.strptime(record_time_str, "%Y-%m-%d %H:%M:%S")
                
                if start_time <= record_time <= end_time:
                    # 새로운 구조: 배열 형태 처리
                    if isinstance(records, list):
                        # 새로운 배열 구조
                        filtered_records.extend(records)
                    elif isinstance(records, dict):
                        # 기존 단일 객체 구조 (하위 호환성)
                        filtered_records.append(records)
            
            # 시행일시 기준으로 정렬
            filtered_records.sort(key=lambda x: x.get("시행일시", ""))
            
            return filtered_records
        except Exception as e:
            print(f"간호기록 조회 오류: {e}")
            return []
    
    def get_all_patient_ids(self) -> List[str]:
        """DATA 디렉토리에 있는 모든 환자 ID 목록 반환"""
        try:
            json_files = list(self.data_dir.glob("*.json"))
            patient_ids = [f.stem for f in json_files]
            return sorted(patient_ids)
        except Exception as e:
            print(f"환자 ID 목록 조회 오류: {e}")
            return []
    
    def add_patient(self, patient_id: str, patient_data: Dict):
        """새 환자 데이터 추가"""
        self.loaded_patients[patient_id] = patient_data
        # 파일로 저장
        self.save_patient_data(patient_id, backup=False)
    
    def update_patient_data(self, patient_id: str, field: str, data: Any):
        """환자 데이터의 특정 필드 업데이트"""
        patient_data = self._load_patient_data(patient_id)
        if patient_data:
            patient_data[field] = data
            self.save_patient_data(patient_id)
            return True
        return False
    
    def add_alarm(self, patient_id: str, admission_id: str, date_str: str, alarm_data: Dict):
        """새 알람 데이터 추가"""
        patient_data = self._load_patient_data(patient_id)
        if not patient_data:
            return False
        
        # 필요한 구조가 없으면 생성
        if "alarms" not in patient_data:
            patient_data["alarms"] = {}
        
        if admission_id not in patient_data["alarms"]:
            patient_data["alarms"][admission_id] = {}
        
        if date_str not in patient_data["alarms"][admission_id]:
            patient_data["alarms"][admission_id][date_str] = []
        
        patient_data["alarms"][admission_id][date_str].append(alarm_data)
        self.save_patient_data(patient_id)
        return True
    
    def add_nursing_record(self, patient_id: str, timestamp: str, record_data: Dict):
        """새 간호기록 추가 (배열 구조)"""
        patient_data = self._load_patient_data(patient_id)
        if not patient_data:
            return False
        
        if "nursing_records" not in patient_data:
            patient_data["nursing_records"] = {}
        
        # 새로운 배열 구조: 같은 타임스탬프에 여러 기록 가능
        if timestamp not in patient_data["nursing_records"]:
            patient_data["nursing_records"][timestamp] = []
        
        # 기존 데이터가 dict라면 list로 변환 (마이그레이션)
        existing_data = patient_data["nursing_records"][timestamp]
        if isinstance(existing_data, dict):
            patient_data["nursing_records"][timestamp] = [existing_data]
        
        # 새 기록 추가
        patient_data["nursing_records"][timestamp].append(record_data)
        
        self.save_patient_data(patient_id)
        return True
    
    def add_waveform_data(self, patient_id: str, timestamp: str, waveform_data: Dict):
        """새 파형 데이터 추가 (배열 또는 base64 형태 모두 지원)"""
        patient_data = self._load_patient_data(patient_id)
        if not patient_data:
            return False
        
        if "waveforms" not in patient_data:
            patient_data["waveforms"] = {}
        
        # 파형 데이터 전처리: numpy 배열을 리스트로 변환하여 저장 (JSON 직렬화 대비)
        processed_waveform_data = {}
        for signal_name, signal_data in waveform_data.items():
            if isinstance(signal_data, np.ndarray):
                # numpy 배열을 리스트로 변환
                processed_waveform_data[signal_name] = signal_data.tolist()
            elif isinstance(signal_data, list):
                # 이미 리스트 형태는 그대로 사용
                processed_waveform_data[signal_name] = signal_data
            elif isinstance(signal_data, str):
                # base64 문자열도 그대로 사용
                processed_waveform_data[signal_name] = signal_data
            else:
                print(f"경고: 지원되지 않는 데이터 타입 ({signal_name}): {type(signal_data)}")
                processed_waveform_data[signal_name] = []
        
        patient_data["waveforms"][timestamp] = processed_waveform_data
        self.save_patient_data(patient_id)
        return True
    
    @staticmethod
    def decode_base64_waveform(base64_str: str) -> np.ndarray:
        """
        base64로 인코딩된 파형 데이터를 디코딩하여 numpy 배열로 반환
        
        Args:
            base64_str: base64로 인코딩된 파형 데이터
            
        Returns:
            numpy 배열로 변환된 파형 데이터
        """
        try:
            # base64 문자열을 바이트로 디코딩
            binary_data = base64.b64decode(base64_str)
            
            # 바이트를 float64 numpy 배열로 변환
            waveform = np.frombuffer(binary_data, dtype=np.float64)
            
            return waveform
        except Exception as e:
            print(f"파형 데이터 디코딩 오류: {e}")
            return np.array([])  # 오류 시 빈 배열 반환
    
    @staticmethod
    def encode_waveform_to_base64(waveform: np.ndarray) -> str:
        """
        numpy 배열을 base64 문자열로 인코딩
        
        Args:
            waveform: numpy 배열 형태의 파형 데이터
            
        Returns:
            base64로 인코딩된 문자열
        """
        try:
            # numpy 배열을 바이트로 변환
            waveform_bytes = waveform.astype(np.float64).tobytes()
            
            # base64로 인코딩
            base64_str = base64.b64encode(waveform_bytes).decode('utf-8')
            
            return base64_str
        except Exception as e:
            print(f"파형 데이터 인코딩 오류: {e}")
            return ""
    
    def migrate_nursing_records_to_array_format(self, patient_id: str = None) -> Dict[str, bool]:
        """간호기록 데이터를 배열 형태로 마이그레이션
        
        Args:
            patient_id: 특정 환자 ID. None이면 모든 환자 마이그레이션
            
        Returns:
            각 환자의 마이그레이션 성공 여부
        """
        if patient_id:
            patient_ids = [patient_id]
        else:
            patient_ids = self.get_all_patient_ids()
        
        results = {}
        
        for pid in patient_ids:
            try:
                patient_data = self._load_patient_data(pid)
                if not patient_data:
                    results[pid] = False
                    continue
                
                nursing_records = patient_data.get("nursing_records", {})
                migrated = False
                
                # 각 타임스탬프를 확인하여 dict 형태를 list로 변환
                for timestamp, records in nursing_records.items():
                    if isinstance(records, dict):
                        # 기존 dict 구조를 list로 변환
                        nursing_records[timestamp] = [records]
                        migrated = True
                        print(f"환자 {pid} - {timestamp}: dict → list 변환")
                    elif isinstance(records, list):
                        # 이미 변환된 상태
                        pass
                    else:
                        print(f"환자 {pid} - {timestamp}: 예상치 못한 데이터 타입: {type(records)}")
                
                if migrated:
                    # 변경된 데이터 저장
                    success = self.save_patient_data(pid)
                    results[pid] = success
                    if success:
                        print(f"환자 {pid} 간호기록 마이그레이션 완료")
                else:
                    results[pid] = True  # 마이그레이션이 필요 없음
                    print(f"환자 {pid} 간호기록 마이그레이션 불필요 (이미 새 구조)")
                    
            except Exception as e:
                print(f"환자 {pid} 마이그레이션 오류: {e}")
                results[pid] = False
        
        return results
    
    def get_data_summary(self) -> Dict[str, Any]:
        """데이터 요약 정보 반환"""
        patient_ids = self.get_all_patient_ids()
        
        summary = {
            "total_patients": len(patient_ids),
            "patients": {}
        }
        
        for patient_id in patient_ids:
            patient_data = self._load_patient_data(patient_id)
            if patient_data:
                # 간호기록 총 수 계산 (배열 구조 고려)
                total_nursing_records = 0
                nursing_records = patient_data.get("nursing_records", {})
                for timestamp, records in nursing_records.items():
                    if isinstance(records, list):
                        total_nursing_records += len(records)
                    elif isinstance(records, dict):
                        total_nursing_records += 1
                
                patient_summary = {
                    "admission_periods": len(patient_data.get("admission_periods", [])),
                    "total_alarms": 0,
                    "total_nursing_records": total_nursing_records,
                    "total_waveforms": len(patient_data.get("waveforms", {}))
                }
                
                # 모든 입원 기간의 알람 수 계산
                alarms = patient_data.get("alarms", {})
                for admission_id, admission_alarms in alarms.items():
                    for date_str, date_alarms in admission_alarms.items():
                        patient_summary["total_alarms"] += len(date_alarms)
                
                summary["patients"][patient_id] = patient_summary
        
        return summary

# 전역 인스턴스 생성 (기존 코드와의 호환성 유지)
patient_data = PatientDataJson()

# 하위 호환성을 위한 별칭
PatientData = PatientDataJson
