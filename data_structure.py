#!/usr/bin/env python3
"""
PKL 파일 기반 데이터 관리 - 최소 읽기 캐시 (저장 시 무효화)
"""

import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any

# 알람 색상 상수
ALARM_COLORS = {
    "Red": "#FF0000",
    "Yellow": "#FFFF00",
    "ShortYellow": "#FFFF00",
    "SevereCyan": "#00FFFF",
    "Cyan": "#00FFFF",
    "SilentCyan": "#00FFFF",
    "White": "#FFFFFF",
}

class PatientData:
    """최소 읽기 캐시를 사용하는 데이터 관리"""
    
    def __init__(self, data_directory: str = "DATA"):
        self.data_dir = Path(data_directory)
        self._read_cache = {}  # 읽기 전용 캐시 (저장 시 무효화)
        
        if not self.data_dir.exists():
            print(f"DATA 디렉토리 생성: {self.data_dir}")
            self.data_dir.mkdir(exist_ok=True)
    
    def _load_patient_data(self, patient_id: str) -> Optional[pd.DataFrame]:
        """캐시 확인 후 없으면 파일에서 로드"""
        # 캐시에서 확인
        if patient_id in self._read_cache:
            return self._read_cache[patient_id]
        
        pkl_file = self.data_dir / f"{patient_id}.pkl"
        
        try:
            with open(pkl_file, 'rb') as f:
                df = pickle.load(f)
            
            # isView=True 필터링
            if 'isView' in df.columns:
                df = df[df['isView'].fillna(False) == True]
            
            # 중복 제거
            if 'TimeStamp' in df.columns and len(df) > 0:
                df = df.drop_duplicates(subset=['TimeStamp'], keep='first')
            
            if len(df) > 0:
                # 캐시에 저장
                self._read_cache[patient_id] = df
                return df
            else:
                return None
                
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"로드 오류: {e}")
            return None
    
    def get_all_patient_ids(self) -> List[str]:
        """모든 환자 ID 목록"""
        try:
            pkl_files = list(self.data_dir.glob("*.pkl"))
            return sorted([f.stem for f in pkl_files])
        except Exception:
            return []
    
    def get_patient_info(self, patient_id: str) -> Optional[Dict]:
        """환자 정보"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return None
        
        labeled_alarms = df['Classification'].notna().sum() if 'Classification' in df.columns else 0
        
        return {
            'patient_id': patient_id,
            'total_alarms': len(df),
            'labeled_alarms': labeled_alarms
        }
    
    def get_admission_periods(self, patient_id: str) -> List[Dict]:
        """입원 기간 목록"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return []
        
        admission_periods = []
        if 'AdmissionIn' in df.columns and 'AdmissionOut' in df.columns:
            mask = df['AdmissionIn'].notna() & df['AdmissionOut'].notna()
            if mask.any():
                unique_admissions = df.loc[mask, ['AdmissionIn', 'AdmissionOut']].drop_duplicates()
                
                for idx, row in unique_admissions.iterrows():
                    start_date = str(row['AdmissionIn']).split(' ')[0]
                    end_date = str(row['AdmissionOut']).split(' ')[0]
                    
                    admission_periods.append({
                        'id': f"{start_date}_{end_date}",
                        'start': start_date,
                        'end': end_date
                    })
        
        return admission_periods if admission_periods else [{'id': 'default', 'start': 'N/A', 'end': 'N/A'}]
    
    def get_available_dates(self, patient_id: str, admission_id: str = None) -> List[str]:
        """알람 날짜 목록"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return []
        
        # 입원 기간 필터링
        if admission_id and admission_id != 'default':
            parts = admission_id.split('_')
            if len(parts) == 2:
                admission_start, admission_end = parts[0], parts[1]
                
                if 'AdmissionIn' in df.columns and 'AdmissionOut' in df.columns:
                    df['admission_start'] = df['AdmissionIn'].astype(str).str.split(' ').str[0]
                    df['admission_end'] = df['AdmissionOut'].astype(str).str.split(' ').str[0]
                    mask = (df['admission_start'] == admission_start) & (df['admission_end'] == admission_end)
                    df = df[mask]
        
        # 날짜 추출
        if 'TimeStamp' in df.columns:
            dates = df['TimeStamp'].astype(str).str.split(' ').str[0].unique()
            return sorted(dates.tolist())
        
        return []
    
    def get_alarms_for_date(self, patient_id: str, admission_id: str, date_str: str) -> List[Dict]:
        """특정 날짜 알람 목록"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return []
        
        # 입원 기간 필터링
        if admission_id and admission_id != 'default':
            parts = admission_id.split('_')
            if len(parts) == 2:
                admission_start, admission_end = parts[0], parts[1]
                
                if 'AdmissionIn' in df.columns and 'AdmissionOut' in df.columns:
                    df['admission_start'] = df['AdmissionIn'].astype(str).str.split(' ').str[0]
                    df['admission_end'] = df['AdmissionOut'].astype(str).str.split(' ').str[0]
                    mask = (df['admission_start'] == admission_start) & (df['admission_end'] == admission_end)
                    df = df[mask]
        
        # 날짜 필터링
        mask = df['TimeStamp'].astype(str).str.startswith(date_str)
        df = df[mask]
        
        alarms = []
        for idx, row in df.iterrows():
            timestamp_str = str(row['TimeStamp'])
            alarm_time = timestamp_str.split(' ')[1] if ' ' in timestamp_str else '00:00:00'
            
            # Label 처리
            label_str = ""
            if 'Label' in row.index:
                label = row['Label']
                if isinstance(label, (list, np.ndarray)):
                    label_str = ' / '.join(str(l) for l in label)
                elif label is not None and pd.notna(label):
                    label_str = str(label)
            
            # Classification
            classification_value = None
            if 'Classification' in row.index and pd.notna(row['Classification']):
                classification_val = row['Classification']
                if isinstance(classification_val, bool):
                    classification_value = classification_val
                elif isinstance(classification_val, str):
                    classification_value = True if classification_val.lower() == 'true' else False if classification_val.lower() == 'false' else None
            
            # Color 처리
            color = 'White'
            if 'SeverityColor' in row.index:
                color_val = row['SeverityColor']
                if pd.notna(color_val):
                    color = color_val
            
            # Severity 처리
            severity = ''
            if 'Severity' in row.index:
                severity_val = row['Severity']
                if pd.notna(severity_val):
                    severity = str(severity_val)
            
            # Comment 처리
            comment = ''
            if 'Comment' in row.index:
                comment_val = row['Comment']
                if pd.notna(comment_val):
                    comment = str(comment_val)
            
            alarms.append({
                'time': alarm_time,
                'color': color,
                'severity': severity,
                'label': label_str,
                'classification': classification_value,
                'comment': comment,
                'row_index': idx
            })
        
        return sorted(alarms, key=lambda x: x['time'])
    
    def get_waveform_data(self, patient_id: str, timestamp: str) -> Optional[Dict]:
        """파형 데이터"""
        print(f"DEBUG: get_waveform_data - patient_id: {patient_id}, timestamp: {timestamp}")
        df = self._load_patient_data(patient_id)
        if df is None:
            print(f"DEBUG: DataFrame is None")
            return None
        
        print(f"DEBUG: DataFrame shape: {df.shape}")
        print(f"DEBUG: First 5 timestamps in df:")
        for i, ts in enumerate(df['TimeStamp'].head(5)):
            print(f"  {i}: {ts}")
        
        # 정확한 매칭 시도
        mask = df['TimeStamp'].astype(str) == timestamp
        print(f"DEBUG: Exact match found: {mask.any()}")
        
        if not mask.any():
            # 부분 매칭 시도
            mask = df['TimeStamp'].astype(str).str.contains(timestamp.replace('.', r'\.'), regex=True, na=False)
            print(f"DEBUG: Partial match found: {mask.any()}")
        
        if not mask.any():
            # 날짜와 시간 부분으로 분리하여 매칭 시도
            if ' ' in timestamp:
                date_part, time_part = timestamp.split(' ', 1)
                mask = df['TimeStamp'].astype(str).str.contains(date_part, regex=False, na=False) & \
                       df['TimeStamp'].astype(str).str.contains(time_part.split('.')[0], regex=False, na=False)
                print(f"DEBUG: Date+Time partial match found: {mask.any()}")
        
        if not mask.any():
            print(f"DEBUG: No matching timestamp found")
            print(f"DEBUG: Looking for: {timestamp}")
            return None
        
        row = df[mask].iloc[0]
        print(f"DEBUG: Found row with index: {row.name}")
        waveform_data = {}
        
        # 파형 신호
        waveform_mappings = {
            'ABP': 'ABP_WAVEFORM',
            'Lead-II': 'ECG_WAVEFORM',
            'Pleth': 'PPG_WAVEFORM', 
            'Resp': 'RESP_WAVEFORM'
        }
        
        for display_name, column_name in waveform_mappings.items():
            if column_name in row.index:
                waveform = row[column_name]
                if isinstance(waveform, (list, np.ndarray)) and len(waveform) > 0:
                    waveform_data[display_name] = np.array(waveform, dtype=np.float64)
                    print(f"DEBUG: Added {display_name} waveform with {len(waveform_data[display_name])} samples")
                else:
                    waveform_data[display_name] = np.array([])
                    print(f"DEBUG: {display_name} waveform is empty")
            else:
                print(f"DEBUG: {column_name} not found in row")
        
        # Numeric 데이터
        numeric_data = {}
        numeric_params = ['SpO2', 'Pulse', 'ST', 'Tskin', 'ABP', 'NBP', 'HR', 'RR']
        
        print(f"DEBUG: Processing Numeric data...")
        for param in numeric_params:
            numeric_col = f"{param}_numeric"
            time_diff_col = f"{param}_numeric_time_diff_sec"
            
            if numeric_col in row.index:
                value = None if pd.isna(row[numeric_col]) else row[numeric_col]
                time_diff = None
                if time_diff_col in row.index:
                    time_diff = None if pd.isna(row[time_diff_col]) else row[time_diff_col]
                    
                numeric_data[param] = [value, time_diff]
                print(f"DEBUG: {param} = {value}, time_diff = {time_diff}")
            else:
                print(f"DEBUG: {numeric_col} not found in row")
        
        if numeric_data:
            waveform_data['Numeric'] = numeric_data
            print(f"DEBUG: Added Numeric data with {len(numeric_data)} parameters")
        else:
            print(f"DEBUG: No Numeric data found")
        
        # AlarmLabel
        waveform_data['AlarmLabel'] = ""
        if 'Label' in row.index:
            label = row['Label']
            if isinstance(label, (list, np.ndarray)):
                waveform_data['AlarmLabel'] = ' / '.join(str(l) for l in label)
            elif label is not None and pd.notna(label):
                waveform_data['AlarmLabel'] = str(label)
        
        print(f"DEBUG: Final waveform_data keys: {list(waveform_data.keys())}")
        print(f"DEBUG: Returning waveform_data with {len(waveform_data)} items")
        
        return waveform_data
    
    def get_nursing_records_for_alarm(self, patient_id: str, timestamp_str: str) -> List[Dict]:
        """간호기록"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return []
        
        mask = df['TimeStamp'].astype(str) == timestamp_str
        if not mask.any():
            timestamp_without_micro = timestamp_str.split('.')[0]
            mask = df['TimeStamp'].astype(str).str.startswith(timestamp_without_micro)
        
        if not mask.any():
            return []
        
        row = df[mask].iloc[0]
        
        if 'NursingRecords_ba30' in row.index:
            nursing_records = row['NursingRecords_ba30']
            if isinstance(nursing_records, (list, np.ndarray)):
                return list(nursing_records)
        
        return []
    
    def get_alarm_annotation(self, patient_id: str, admission_id: str, date_str: str, time_str: str) -> Dict:
        """annotation 가져오기"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return {'classification': None, 'comment': ''}
        
        timestamp = f"{date_str} {time_str}"
        mask = df['TimeStamp'].astype(str).str.contains(timestamp, regex=False, na=False)
        
        if not mask.any():
            return {'classification': None, 'comment': ''}
        
        row = df[mask].iloc[0]
        
        classification = None
        if 'Classification' in row.index and pd.notna(row['Classification']):
            classification_val = row['Classification']
            if isinstance(classification_val, bool):
                classification = classification_val
            elif isinstance(classification_val, str):
                classification = True if classification_val.lower() == 'true' else False if classification_val.lower() == 'false' else None
        
        comment = str(row['Comment']) if 'Comment' in row.index and pd.notna(row['Comment']) else ''
        
        return {'classification': classification, 'comment': comment}
    
    def set_alarm_annotation(self, patient_id: str, admission_id: str, date_str: str, 
                           time_str: str, classification, comment: str) -> bool:
        """annotation 저장 - 캐시 무효화"""
        pkl_file = self.data_dir / f"{patient_id}.pkl"
        
        if not pkl_file.exists():
            return False
        
        try:
            # 파일에서 직접 읽기 (캐시 사용 안 함)
            with open(pkl_file, 'rb') as f:
                df = pickle.load(f)
            
            timestamp = f"{date_str} {time_str}"
            mask = df['TimeStamp'].astype(str).str.contains(timestamp, regex=False, na=False)
            
            if not mask.any():
                return False
            
            idx = df[mask].index[0]
            
            # 컬럼 추가
            if 'Classification' not in df.columns:
                df['Classification'] = None
            if 'Comment' not in df.columns:
                df['Comment'] = ''
            if 'isSelected' not in df.columns:
                df['isSelected'] = False
            
            # 값 업데이트
            df.loc[idx, 'Classification'] = classification
            df.loc[idx, 'Comment'] = comment
            if classification is not None:
                df.loc[idx, 'isSelected'] = True
            
            # 파일 저장
            with open(pkl_file, 'wb') as f:
                pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            # 캐시 무효화 (다음 읽기 시 최신 버전 로드)
            if patient_id in self._read_cache:
                del self._read_cache[patient_id]
            
            return True
            
        except Exception as e:
            print(f"annotation 저장 오류: {e}")
            return False
    
    def get_patient_alarm_stats(self, patient_id: str) -> Dict:
        """환자 알람 통계"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return {'labeled': 0, 'total': 0}
        
        total_count = len(df)
        labeled_count = df['Classification'].notna().sum() if 'Classification' in df.columns else 0
        
        return {'labeled': labeled_count, 'total': total_count}

# 전역 인스턴스
patient_data = PatientData()

# 하위 호환성
PatientDataJson = PatientData
