#!/usr/bin/env python3
"""
PKL 파일 기반 데이터 관리 - 캐시 없는 버전 (항상 파일에서 직접 읽기)
"""

import pickle
import pandas as pd
import numpy as np  # numpy 타입 처리를 위해 필요
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
    """캐시 없이 항상 파일에서 직접 읽는 데이터 관리"""
    
    def __init__(self, data_directory: str = "DATA"):
        self.data_dir = Path(data_directory)
        
        if not self.data_dir.exists():
            print(f"DATA 디렉토리 생성: {self.data_dir}")
            self.data_dir.mkdir(exist_ok=True)
    
    def _load_patient_data(self, patient_id: str) -> Optional[pd.DataFrame]:
        """항상 파일에서 직접 로드 (캐시 사용 안함)"""
        pkl_file = self.data_dir / f"{patient_id}.pkl"
        
        try:
            with open(pkl_file, 'rb') as f:
                df = pickle.load(f)
            
            print(f"[DEBUG] Loaded {patient_id}: {len(df)} rows")
            
            # Classification 컬럼 디버그
            if 'Classification' in df.columns:
                non_null = df['Classification'].notna().sum()
                print(f"[DEBUG] Classification column exists, non-null: {non_null}")
            else:
                print(f"[DEBUG] WARNING: Classification column does NOT exist in {patient_id}.pkl!")
                print(f"[DEBUG] Available columns: {df.columns.tolist()[:10]}...")  # 처음 10개만
            
            # isView=True 필터링
            if 'isView' in df.columns:
                df = df[df['isView'].fillna(False) == True]
                print(f"[DEBUG] After isView filter: {len(df)} rows")
            
            # 중복 제거
            if 'TimeStamp' in df.columns and len(df) > 0:
                df = df.drop_duplicates(subset=['TimeStamp'], keep='first')
                print(f"[DEBUG] After dedup: {len(df)} rows")
            
            if len(df) > 0:
                return df
            else:
                return None
                
        except FileNotFoundError:
            print(f"[ERROR] File not found: {pkl_file}")
            return None
        except Exception as e:
            print(f"[ERROR] 로드 오류: {e}")
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
        
        # Classification 컬럼 존재 여부 확인
        if 'Classification' in df.columns:
            labeled_alarms = df['Classification'].notna().sum()
        else:
            print(f"[DEBUG] get_patient_info: Classification column missing for {patient_id}")
            labeled_alarms = 0
        
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
        
        print(f"[DEBUG] get_alarms_for_date: {patient_id}, {date_str}, found {len(df)} rows")
        
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
            
            # Classification - numpy 타입 포함 처리
            classification_value = None
            if 'Classification' in row.index:
                raw_val = row['Classification']
                
                if pd.notna(raw_val):
                    # numpy bool 타입 처리 추가
                    if isinstance(raw_val, (bool, np.bool_)):
                        classification_value = bool(raw_val)  # Python bool로 변환
                    elif isinstance(raw_val, (int, float, np.integer, np.floating)):
                        if raw_val == 0 or raw_val == 0.0:
                            classification_value = False
                        elif raw_val == 1 or raw_val == 1.0:
                            classification_value = True
                    elif isinstance(raw_val, str):
                        if raw_val.lower() == 'true':
                            classification_value = True
                        elif raw_val.lower() == 'false':
                            classification_value = False
            
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
        df = self._load_patient_data(patient_id)
        if df is None:
            return None
        
        # 정확한 매칭 시도
        mask = df['TimeStamp'].astype(str) == timestamp
        
        if not mask.any():
            # 부분 매칭 시도
            mask = df['TimeStamp'].astype(str).str.contains(timestamp.replace('.', r'\.'), regex=True, na=False)
        
        if not mask.any():
            # 날짜와 시간 부분으로 분리하여 매칭 시도
            if ' ' in timestamp:
                date_part, time_part = timestamp.split(' ', 1)
                mask = df['TimeStamp'].astype(str).str.contains(date_part, regex=False, na=False) & \
                       df['TimeStamp'].astype(str).str.contains(time_part.split('.')[0], regex=False, na=False)
        
        if not mask.any():
            return None
        
        row = df[mask].iloc[0]
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
                else:
                    waveform_data[display_name] = np.array([])
        
        # Numeric 데이터
        numeric_data = {}
        numeric_params = ['SpO2', 'Pulse', 'ST', 'Tskin', 'ABP', 'NBP', 'HR', 'RR']
        
        for param in numeric_params:
            numeric_col = f"{param}_numeric"
            time_diff_col = f"{param}_numeric_time_diff_sec"
            
            if numeric_col in row.index:
                value = None if pd.isna(row[numeric_col]) else row[numeric_col]
                time_diff = None
                if time_diff_col in row.index:
                    time_diff = None if pd.isna(row[time_diff_col]) else row[time_diff_col]
                    
                numeric_data[param] = [value, time_diff]
        
        if numeric_data:
            waveform_data['Numeric'] = numeric_data
        
        # AlarmLabel
        waveform_data['AlarmLabel'] = ""
        if 'Label' in row.index:
            label = row['Label']
            if isinstance(label, (list, np.ndarray)):
                waveform_data['AlarmLabel'] = ' / '.join(str(l) for l in label)
            elif label is not None and pd.notna(label):
                waveform_data['AlarmLabel'] = str(label)
        
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
            print(f"[DEBUG] get_alarm_annotation: No data for patient {patient_id}")
            return {'classification': None, 'comment': ''}
        
        timestamp = f"{date_str} {time_str}"
        
        # TimeStamp 컬럼의 타입 확인 및 문자열 변환
        df['TimeStamp_str'] = df['TimeStamp'].astype(str)
        
        # 정확한 매칭 시도
        mask = df['TimeStamp_str'] == timestamp
        
        if not mask.any():
            # 부분 매칭 시도 (마이크로초 제외)
            timestamp_base = timestamp.split('.')[0] if '.' in timestamp else timestamp
            mask = df['TimeStamp_str'].str.contains(timestamp_base, regex=False, na=False)
        
        if not mask.any():
            # 더 유연한 매칭 - 날짜와 시간의 시:분:초까지만 매칭
            if ' ' in timestamp:
                date_part, time_part = timestamp.split(' ', 1)
                time_hms = time_part.split('.')[0]  # 시:분:초만 추출
                pattern = f"{date_part} {time_hms}"
                mask = df['TimeStamp_str'].str.startswith(pattern)
        
        if not mask.any():
            print(f"[DEBUG] get_alarm_annotation: No matching timestamp")
            print(f"[DEBUG] Looking for: {timestamp}")
            print(f"[DEBUG] Sample timestamps in data (first 5):")
            for ts in df['TimeStamp_str'].head(5):
                print(f"    - {ts}")
            return {'classification': None, 'comment': ''}
        
        row = df[mask].iloc[0]
        
        # 더 자세한 디버깅 정보
        print(f"\n[DEBUG] get_alarm_annotation for {patient_id}, {timestamp}:")
        print(f"  - Row index: {df[mask].index[0]}")
        print(f"  - Has Classification column: {'Classification' in row.index}")
        
        classification = None
        if 'Classification' in row.index:
            raw_val = row['Classification']
            print(f"  - Classification raw value: {repr(raw_val)}")
            print(f"  - Classification type: {type(raw_val)}")
            print(f"  - pd.isna: {pd.isna(raw_val)}, pd.notna: {pd.notna(raw_val)}")
            
            if pd.notna(raw_val):
                # numpy bool 타입 처리 추가
                if isinstance(raw_val, (bool, np.bool_)):
                    classification = bool(raw_val)  # Python bool로 변환
                    print(f"  - Converted bool/np.bool: {classification}")
                elif isinstance(raw_val, (int, float, np.integer, np.floating)):
                    if raw_val == 0 or raw_val == 0.0:
                        classification = False
                    elif raw_val == 1 or raw_val == 1.0:
                        classification = True
                    print(f"  - Converted numeric: {classification}")
                elif isinstance(raw_val, str):
                    if raw_val.lower() == 'true':
                        classification = True
                    elif raw_val.lower() == 'false':
                        classification = False
                    print(f"  - Converted string: {classification}")
                else:
                    print(f"  - Unknown type, cannot convert!")
            else:
                print(f"  - Value is NaN/None")
        else:
            print(f"  - Classification column not in row.index!")
        
        comment = str(row['Comment']) if 'Comment' in row.index and pd.notna(row['Comment']) else ''
        
        print(f"  - Final result: classification={classification}, comment={comment}")
        return {'classification': classification, 'comment': comment}
    
    def set_alarm_annotation(self, patient_id: str, admission_id: str, date_str: str, 
                           time_str: str, classification, comment: str) -> bool:
        """annotation 저장"""
        print(f"\n=== SAVE DEBUG ===")
        print(f"Patient: {patient_id}, Date: {date_str}, Time: {time_str}")
        print(f"Classification: {classification} (type: {type(classification)}), Comment: {comment}")
        
        pkl_file = self.data_dir / f"{patient_id}.pkl"
        
        if not pkl_file.exists():
            print(f"ERROR: File does not exist: {pkl_file}")
            return False
        
        try:
            # 파일에서 직접 읽기 (필터링 없이 원본 데이터)
            with open(pkl_file, 'rb') as f:
                df_original = pickle.load(f)
            print(f"Loaded DataFrame shape: {df_original.shape}")
            
            # isView=True 필터링 적용 (읽을 때와 동일하게)
            if 'isView' in df_original.columns:
                # 필터링 전에 원본 인덱스 매핑 저장
                df_filtered = df_original[df_original['isView'].fillna(False) == True].copy()
                print(f"After isView filter for matching: {len(df_filtered)} rows")
            else:
                df_filtered = df_original.copy()
            
            timestamp = f"{date_str} {time_str}"
            
            # 필터링된 데이터에서 매칭
            mask = df_filtered['TimeStamp'].astype(str) == timestamp
            
            if not mask.any():
                time_str_base = time_str.split('.')[0] if '.' in time_str else time_str
                timestamp_base = f"{date_str} {time_str_base}"
                df_timestamps_base = df_filtered['TimeStamp'].astype(str).str.split('.').str[0]
                mask = df_timestamps_base.str.contains(timestamp_base, regex=False, na=False)
            
            print(f"Found {mask.sum()} matching rows in filtered data for timestamp: {timestamp}")
            
            if not mask.any():
                print(f"ERROR: No matching timestamp found in filtered data!")
                return False
            
            # 필터링된 데이터에서의 인덱스 가져오기
            filtered_idx = df_filtered[mask].index[0]
            print(f"Found at filtered index: {filtered_idx}")
            
            # 원본 데이터프레임에서 해당 인덱스 찾기
            original_idx = filtered_idx  # 인덱스는 보존됨
            print(f"Updating row at original index: {original_idx}")
            
            # 컬럼 추가 (원본에)
            if 'Classification' not in df_original.columns:
                df_original['Classification'] = pd.NA
            if 'Comment' not in df_original.columns:
                df_original['Comment'] = ''
            if 'isSelected' not in df_original.columns:
                df_original['isSelected'] = False
            
            # 값 업데이트 전 상태
            print(f"Before: Classification={df_original.loc[original_idx, 'Classification']}, Comment={df_original.loc[original_idx, 'Comment']}")
            
            # 원본 데이터프레임에 값 업데이트
            if classification is not None:
                df_original.loc[original_idx, 'Classification'] = bool(classification)
                df_original.loc[original_idx, 'isSelected'] = True
            else:
                df_original.loc[original_idx, 'Classification'] = pd.NA
                df_original.loc[original_idx, 'isSelected'] = False
            
            df_original.loc[original_idx, 'Comment'] = comment
            
            print(f"After: Classification={df_original.loc[original_idx, 'Classification']} (type: {type(df_original.loc[original_idx, 'Classification'])})")
            
            # 파일 저장 (원본 저장)
            with open(pkl_file, 'wb') as f:
                pickle.dump(df_original, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"File saved!")
            
            # 검증
            with open(pkl_file, 'rb') as f:
                df_verify = pickle.load(f)
            verify_value = df_verify.loc[original_idx, 'Classification']
            print(f"Verification: Classification in file = {verify_value} (type: {type(verify_value)})")
            
            print(f"=== SAVE SUCCESS ===\n")
            return True
            
        except Exception as e:
            print(f"ERROR: Exception during save: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_patient_alarm_stats(self, patient_id: str) -> Dict:
        """환자 알람 통계"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return {'labeled': 0, 'total': 0}
        
        total_count = len(df)
        
        # Classification 컬럼 존재 여부 확인
        if 'Classification' in df.columns:
            labeled_count = df['Classification'].notna().sum()
        else:
            print(f"[DEBUG] get_patient_alarm_stats: Classification column missing for {patient_id}")
            labeled_count = 0
        
        return {'labeled': labeled_count, 'total': total_count}

# 전역 인스턴스
patient_data = PatientData()

# 하위 호환성
PatientDataJson = PatientData
