#!/usr/bin/env python3
"""
PKL 파일 기반 환자 데이터 관리 클래스
DataFrame 형태의 PKL 파일에서 데이터를 로드하여 사용
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from PySide6.QtCore import QThread, Signal
import threading
import queue
import time

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

class SaveWorkerThread(QThread):
    """백그라운드에서 파일 저장을 처리하는 스레드"""
    save_completed = Signal(str)  # 저장 완료 시그널 추가
    save_failed = Signal(str, str)  # 저장 실패 시그널 (patient_id, error_msg)
    
    def __init__(self):
        super().__init__()
        self.save_queue = queue.Queue()
        self.running = True
    
    def run(self):
        """스레드 메인 루프"""
        while self.running:
            try:
                # 큐에서 작업 가져오기 (0.1초 타임아웃)
                task = self.save_queue.get(timeout=0.1)
                if task is None:  # 종료 신호
                    break
                
                # 작업 실행
                func, args, kwargs, patient_id = task
                try:
                    func(*args, **kwargs)
                    self.save_completed.emit(patient_id)
                except Exception as e:
                    self.save_failed.emit(patient_id, str(e))
                    print(f"백그라운드 저장 실패 ({patient_id}): {e}")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"SaveWorkerThread 오류: {e}")
    
    def add_save_task(self, func, patient_id, *args, **kwargs):
        """저장 작업을 큐에 추가"""
        self.save_queue.put((func, args, kwargs, patient_id))
    
    def stop(self):
        """스레드 종료"""
        self.running = False
        self.save_queue.put(None)
        self.wait()  # 스레드가 종료될 때까지 대기


class PatientDataJson:
    """PKL 파일 기반 환자 데이터 관리 클래스 (기존 이름 유지)"""
    
    def __init__(self, data_directory: str = "DATA"):
        """
        Args:
            data_directory: 환자 데이터 PKL 파일들이 저장된 디렉토리 경로
        """
        self.data_dir = Path(data_directory)
        self.patient_dataframes = {}  # 환자별 DataFrame 캐시
        self.patient_timestamp_indices = {}  # 타임스탬프 인덱스 캐시 (빠른 검색용)
        
        # 백그라운드 저장 스레드 시작
        self.save_thread = SaveWorkerThread()
        self.save_thread.start()
        
        # 저장 대기 중인 환자 ID 추적 (중복 저장 방지)
        self.pending_saves = set()
        self.save_lock = threading.Lock()
        
        # DATA 디렉토리 확인
        if not self.data_dir.exists():
            print(f"DATA 디렉토리가 존재하지 않습니다: {self.data_dir}")
            self.data_dir.mkdir(exist_ok=True)
            print(f"DATA 디렉토리를 생성했습니다: {self.data_dir}")
    
    def __del__(self):
        """소멸자 - 스레드 정리"""
        if hasattr(self, 'save_thread'):
            self.save_thread.stop()
    
    def _load_patient_data(self, patient_id: str) -> Optional[pd.DataFrame]:
        """특정 환자 ID의 PKL 파일에서 데이터를 로드"""
        # 이미 로드된 데이터가 있으면 반환
        if patient_id in self.patient_dataframes:
            return self.patient_dataframes[patient_id]
        
        # 환자 PKL 파일 경로
        pkl_file = self.data_dir / f"{patient_id}.pkl"
        
        try:
            with open(pkl_file, 'rb') as f:
                df = pickle.load(f)
            
            # isView가 True인 행만 필터링
            if 'isView' in df.columns:
                df_filtered = df[df['isView'].fillna(False) == True].copy()
            else:
                df_filtered = df.copy()
            
            # TimeStamp 기준으로 중복 제거
            if 'TimeStamp' in df_filtered.columns and len(df_filtered) > 0:
                # TimeStamp를 문자열로 변환하여 정확한 비교
                df_filtered['TimeStamp_str'] = df_filtered['TimeStamp'].astype(str)
                
                # 중복 제거 전 개수
                before_dedup = len(df_filtered)
                
                # TimeStamp가 완전히 동일한 행들 중 첫 번째만 유지
                df_filtered = df_filtered.drop_duplicates(subset=['TimeStamp_str'], keep='first')
                
                # TimeStamp_str 컬럼 제거
                df_filtered = df_filtered.drop(columns=['TimeStamp_str'])
                
                # 중복 제거 후 개수
                after_dedup = len(df_filtered)
                
                # if before_dedup > after_dedup:
                #     print(f"환자 {patient_id}: {before_dedup - after_dedup}개의 중복 알람 제거")
            
            if len(df_filtered) > 0:
                self.patient_dataframes[patient_id] = df_filtered
                # print(f"환자 {patient_id} 데이터 로드 완료: {len(df_filtered)}개 알람")
                return df_filtered
            else:
                print(f"환자 {patient_id}: isView=True인 데이터가 없습니다")
                return None
                
        except FileNotFoundError:
            print(f"환자 파일을 찾을 수 없습니다: {pkl_file}")
            return None
        except Exception as e:
            print(f"PKL 파일 로드 오류 ({pkl_file}): {e}")
            return None
    
    def _save_patient_data_sync(self, patient_id: str):
        """동기적으로 데이터 저장 (백그라운드 스레드에서 호출)"""
        if patient_id not in self.patient_dataframes:
            return False
        
        pkl_file = self.data_dir / f"{patient_id}.pkl"
        
        try:
            # 원본 파일 읽기
            if pkl_file.exists():
                with open(pkl_file, 'rb') as f:
                    original_df = pickle.load(f)
                
                # isView=False인 데이터 복원 (캐시에는 isView=True만 있음)
                modified_df = self.patient_dataframes[patient_id]
                
                # 캐시에 있는 인덱스만 업데이트
                for idx in modified_df.index:
                    if idx in original_df.index:
                        # 변경 가능한 컬럼만 업데이트
                        for col in ['Classification', 'Comment', 'isSelected']:
                            if col in modified_df.columns:
                                if col not in original_df.columns:
                                    # 컬럼이 없으면 추가
                                    if col == 'Classification':
                                        original_df[col] = None
                                    elif col == 'Comment':
                                        original_df[col] = ''
                                    else:  # isSelected
                                        original_df[col] = False
                                original_df.loc[idx, col] = modified_df.loc[idx, col]
            else:
                # 파일이 없는 경우 캐시 데이터 그대로 저장
                original_df = self.patient_dataframes[patient_id]
            
            # PKL 파일로 저장 (빠른 프로토콜 사용)
            with open(pkl_file, 'wb') as f:
                pickle.dump(original_df, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            # 저장 완료 후 pending_saves에서 제거
            with self.save_lock:
                self.pending_saves.discard(patient_id)
            
            return True
            
        except Exception as e:
            print(f"데이터 저장 오류 ({patient_id}): {e}")
            with self.save_lock:
                self.pending_saves.discard(patient_id)
            return False
    
    def save_patient_data_async(self, patient_id: str):
        """비동기적으로 데이터 저장 (백그라운드 스레드 사용)"""
        with self.save_lock:
            # 이미 저장 대기 중인 경우 중복 요청 무시
            if patient_id in self.pending_saves:
                return True
            self.pending_saves.add(patient_id)
        
        # 백그라운드 스레드에 저장 작업 추가
        self.save_thread.add_save_task(self._save_patient_data_sync, patient_id, patient_id)
        return True
    
    def save_patient_data_fast(self, patient_id: str, idx: int, updates: dict):
        """특정 인덱스만 빠르게 업데이트하여 저장 (비동기)"""
        # 메모리 캐시만 즉시 업데이트
        if patient_id in self.patient_dataframes:
            df = self.patient_dataframes[patient_id]
            for col, val in updates.items():
                if col not in df.columns:
                    if col == 'Classification':
                        df[col] = None
                    elif col == 'Comment':
                        df[col] = ''
                    else:  # isSelected
                        df[col] = False
                df.loc[idx, col] = val
        
        # 백그라운드에서 파일 저장
        return self.save_patient_data_async(patient_id)
    
    def save_patient_data(self, patient_id: str, backup: bool = False):
        """변경된 데이터를 PKL 파일로 저장 (비동기)"""
        return self.save_patient_data_async(patient_id)
    
    def get_all_patient_ids(self) -> List[str]:
        """DATA 디렉토리에 있는 모든 환자 ID 목록 반환"""
        try:
            pkl_files = list(self.data_dir.glob("*.pkl"))
            patient_ids = [f.stem for f in pkl_files]
            return sorted(patient_ids)
        except Exception as e:
            print(f"환자 ID 목록 조회 오류: {e}")
            return []
    
    def get_patient_info(self, patient_id: str) -> Optional[Dict]:
        """환자 정보 반환"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return None
        
        labeled_alarms = 0
        if 'Classification' in df.columns:
            # Classification이 None이 아닌 경우를 라벨링된 것으로 간주
            labeled_alarms = df['Classification'].notna().sum()
        
        return {
            'patient_id': patient_id,
            'total_alarms': len(df),
            'labeled_alarms': labeled_alarms
        }
    
    def get_admission_periods(self, patient_id: str) -> List[Dict]:
        """환자의 입원 기간 목록 반환"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return []
        
        # AdmissionIn과 AdmissionOut에서 고유한 입원 기간 추출
        admission_periods = []
        if 'AdmissionIn' in df.columns and 'AdmissionOut' in df.columns:
            # 비어있지 않은 값만 필터링하고 중복 제거
            df_filtered = df[df['AdmissionIn'].notna() & df['AdmissionOut'].notna()]
            if len(df_filtered) > 0:
                unique_admissions = df_filtered[['AdmissionIn', 'AdmissionOut']].drop_duplicates()
                
                for idx, row in unique_admissions.iterrows():
                    admission_in = row['AdmissionIn']
                    admission_out = row['AdmissionOut']
                    
                    # 날짜 형식 변환
                    if pd.notna(admission_in) and pd.notna(admission_out):
                        if isinstance(admission_in, str):
                            start_date = admission_in.split(' ')[0] if ' ' in admission_in else admission_in
                            end_date = admission_out.split(' ')[0] if ' ' in admission_out else admission_out
                        else:
                            start_date = str(admission_in).split(' ')[0]
                            end_date = str(admission_out).split(' ')[0]
                        
                        admission_periods.append({
                            'id': f"{start_date}_{end_date}",
                            'start': start_date,
                            'end': end_date
                        })
        
        return admission_periods if admission_periods else [{'id': 'default', 'start': 'N/A', 'end': 'N/A'}]
    
    def get_available_dates(self, patient_id: str, admission_id: str = None) -> List[str]:
        """특정 입원 기간의 알람 데이터가 있는 날짜 목록 반환"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return []
        
        # admission_id를 파싱하여 입원 시작/종료 날짜 추출
        admission_start = None
        admission_end = None
        if admission_id and admission_id != 'default':
            parts = admission_id.split('_')
            if len(parts) == 2:
                admission_start = parts[0]
                admission_end = parts[1]
        
        # TimeStamp에서 날짜 추출
        dates = set()
        for idx, row in df.iterrows():
            # 입원 기간 체크 (admission_id가 지정된 경우)
            if admission_id and admission_id != 'default':
                # AdmissionIn과 AdmissionOut 확인
                if 'AdmissionIn' in row.index and 'AdmissionOut' in row.index:
                    row_admission_in = row['AdmissionIn']
                    row_admission_out = row['AdmissionOut']
                    
                    # 입원 날짜 추출 (None 처리 포함)
                    row_start = None
                    row_end = None
                    
                    if pd.notna(row_admission_in):
                        if isinstance(row_admission_in, str):
                            row_start = row_admission_in.split(' ')[0]
                        else:
                            row_start = str(row_admission_in).split(' ')[0]
                    
                    if pd.notna(row_admission_out):
                        if isinstance(row_admission_out, str):
                            row_end = row_admission_out.split(' ')[0]
                        else:
                            row_end = str(row_admission_out).split(' ')[0]
                    
                    # admission_id와 정확히 일치하는지 확인
                    # admission_start와 admission_end 모두 일치해야 함
                    # None 값도 일치해야 함 (None == None은 True)
                    if not (row_start == admission_start and row_end == admission_end):
                        continue
            
            timestamp = row['TimeStamp']
            if pd.notna(timestamp):
                if isinstance(timestamp, str):
                    date_str = timestamp.split(' ')[0]
                else:
                    date_str = str(timestamp).split(' ')[0]
                dates.add(date_str)
        
        return sorted(list(dates))
    
    def get_alarms_for_date(self, patient_id: str, admission_id: str, date_str: str) -> List[Dict]:
        """특정 날짜의 알람 목록 반환"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return []
        
        # admission_id를 파싱하여 입원 시작/종료 날짜 추출
        admission_start = None
        admission_end = None
        if admission_id and admission_id != 'default':
            parts = admission_id.split('_')
            if len(parts) == 2:
                admission_start = parts[0]
                admission_end = parts[1]
        
        # 해당 날짜의 알람 필터링
        alarms = []
        for idx, row in df.iterrows():
            # 입원 기간 체크 (admission_id가 지정된 경우)
            if admission_id and admission_id != 'default':
                # AdmissionIn과 AdmissionOut 확인
                if 'AdmissionIn' in row.index and 'AdmissionOut' in row.index:
                    row_admission_in = row['AdmissionIn']
                    row_admission_out = row['AdmissionOut']
                    
                    # 입원 날짜 추출 (None 처리 포함)
                    row_start = None
                    row_end = None
                    
                    if pd.notna(row_admission_in):
                        if isinstance(row_admission_in, str):
                            row_start = row_admission_in.split(' ')[0]
                        else:
                            row_start = str(row_admission_in).split(' ')[0]
                    
                    if pd.notna(row_admission_out):
                        if isinstance(row_admission_out, str):
                            row_end = row_admission_out.split(' ')[0]
                        else:
                            row_end = str(row_admission_out).split(' ')[0]
                    
                    # admission_id와 정확히 일치하는지 확인
                    # admission_start와 admission_end 모두 일치해야 함
                    # None 값도 일치해야 함 (None == None은 True)
                    if not (row_start == admission_start and row_end == admission_end):
                        continue
            
            timestamp = row['TimeStamp']
            if pd.notna(timestamp):
                if isinstance(timestamp, str):
                    alarm_date = timestamp.split(' ')[0]
                    alarm_time = timestamp.split(' ')[1] if ' ' in timestamp else '00:00:00'
                else:
                    timestamp_str = str(timestamp)
                    alarm_date = timestamp_str.split(' ')[0]
                    alarm_time = timestamp_str.split(' ')[1] if ' ' in timestamp_str else '00:00:00'
                
                if alarm_date == date_str:
                    # Label 처리 (리스트를 문자열로)
                    label_str = ""
                    if 'Label' in row.index:
                        label = row['Label']
                        if isinstance(label, list):
                            label_str = ' / '.join(str(l) for l in label)
                        elif pd.notna(label):
                            label_str = str(label)
                    
                    # SeverityColor 가져오기
                    color = 'White'
                    if 'SeverityColor' in row.index:
                        color_val = row['SeverityColor']
                        if pd.notna(color_val):
                            color = color_val
                    
                    # Classification 확인 (직접 Classification 컬럼 사용)
                    classification_value = None
                    if 'Classification' in row.index:
                        classification_val = row['Classification']
                        if pd.notna(classification_val):
                            if isinstance(classification_val, bool):
                                classification_value = classification_val
                            elif isinstance(classification_val, str):
                                # 문자열인 경우 True/False로 변환
                                if classification_val.lower() == 'true':
                                    classification_value = True
                                elif classification_val.lower() == 'false':
                                    classification_value = False
                    
                    # Comment 가져오기
                    comment = ''
                    if 'Comment' in row.index:
                        comment_val = row['Comment']
                        if pd.notna(comment_val):
                            comment = comment_val
                    
                    # Severity 가져오기
                    severity = ''
                    if 'Severity' in row.index:
                        severity_val = row['Severity']
                        if pd.notna(severity_val):
                            severity = severity_val
                    
                    alarms.append({
                        'time': alarm_time,
                        'color': color,
                        'severity': severity,
                        'label': label_str,
                        'classification': classification_value,
                        'comment': comment,
                        'row_index': idx  # DataFrame 인덱스 저장
                    })
        
        return sorted(alarms, key=lambda x: x['time'])
    
    def get_waveform_data(self, patient_id: str, timestamp: str) -> Optional[Dict]:
        """특정 타임스탬프의 파형 데이터 반환"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return None
        
        # 타임스탬프로 행 찾기
        matching_rows = df[df['TimeStamp'] == timestamp]
        if len(matching_rows) == 0:
            # 시간 부분만 비교
            time_part = timestamp.split(' ')[1] if ' ' in timestamp else timestamp
            date_part = timestamp.split(' ')[0] if ' ' in timestamp else ''
            
            for idx, row in df.iterrows():
                row_timestamp = str(row['TimeStamp'])
                if date_part in row_timestamp and time_part in row_timestamp:
                    matching_rows = df.loc[[idx]]
                    break
        
        if len(matching_rows) == 0:
            return None
        
        row = matching_rows.iloc[0]
        
        # 파형 데이터 구성
        waveform_data = {}
        
        # 파형 신호들
        waveform_mappings = {
            'ABP': 'ABP_WAVEFORM',
            'Lead-II': 'ECG_WAVEFORM',
            'Pleth': 'PPG_WAVEFORM', 
            'Resp': 'RESP_WAVEFORM'
        }
        
        for display_name, column_name in waveform_mappings.items():
            # row는 Series이므로 column_name이 인덱스에 있는지 확인
            if column_name in row.index:
                waveform = row[column_name]
                # waveform이 리스트나 배열인지 확인 (pd.notna는 배열에 사용할 수 없음)
                if isinstance(waveform, (list, np.ndarray)):
                    if len(waveform) > 0:
                        waveform_data[display_name] = np.array(waveform, dtype=np.float64)
                    else:
                        waveform_data[display_name] = np.array([])
                elif pd.notna(waveform):  # 단일 값인 경우에만 pd.notna 사용
                    waveform_data[display_name] = np.array([])
                else:
                    waveform_data[display_name] = np.array([])
        
        # Numeric 데이터
        numeric_data = {}
        numeric_params = ['SpO2', 'Pulse', 'ST', 'Tskin', 'ABP', 'NBP', 'HR', 'RR']
        
        for param in numeric_params:
            numeric_col = f"{param}_numeric"
            time_diff_col = f"{param}_numeric_time_diff_sec"
            
            if numeric_col in row.index:
                value = row[numeric_col]
                # time_diff 값 가져오기
                time_diff = None
                if time_diff_col in row.index:
                    time_diff_value = row[time_diff_col]
                    if pd.notna(time_diff_value):
                        time_diff = time_diff_value
                    else:
                        time_diff = None
                
                # NaN이나 None이더라도 데이터는 추가 (표시할 때 None으로 처리하기 위해)
                # value가 NaN인 경우 None으로 변환
                if pd.isna(value):
                    value = None
                if pd.isna(time_diff):
                    time_diff = None
                    
                numeric_data[param] = [value, time_diff]
        
        if numeric_data:
            waveform_data['Numeric'] = numeric_data
        
        # AlarmLabel
        if 'Label' in row.index:
            label = row['Label']
            if isinstance(label, list):
                waveform_data['AlarmLabel'] = ' / '.join(str(l) for l in label)
            elif pd.notna(label):
                waveform_data['AlarmLabel'] = str(label)
            else:
                waveform_data['AlarmLabel'] = ""
        else:
            waveform_data['AlarmLabel'] = ""
        
        return waveform_data
    
    def get_nursing_records_for_alarm(self, patient_id: str, timestamp_str: str) -> List[Dict]:
        """알람의 간호기록 반환 (이미 ±30분 필터링됨)"""
        df = self._load_patient_data(patient_id)
        if df is None:
            print(f"DEBUG: 환자 데이터 없음: {patient_id}")
            return []
        
        print(f"DEBUG: 간호기록 조회 - Patient: {patient_id}, Timestamp: {timestamp_str}")
        
        # 타임스탬프로 행 찾기
        # 먼저 정확히 일치하는 것 찾기
        matching_rows = df[df['TimeStamp'] == timestamp_str]
        
        if len(matching_rows) == 0:
            # 다양한 형식 시도 (microseconds 제거 등)
            timestamp_without_micro = timestamp_str.split('.')[0]  # microseconds 제거
            
            for idx, row in df.iterrows():
                row_timestamp = str(row['TimeStamp'])
                
                # 여러 매칭 방법 시도
                if (timestamp_str == row_timestamp or
                    timestamp_str in row_timestamp or
                    timestamp_without_micro in row_timestamp or
                    row_timestamp.startswith(timestamp_str) or
                    row_timestamp.startswith(timestamp_without_micro)):
                    matching_rows = df.loc[[idx]]
                    print(f"DEBUG: 매칭 성공 - 원본: {timestamp_str}, 찾은 것: {row_timestamp}")
                    break
        
        if len(matching_rows) == 0:
            print(f"DEBUG: 매칭되는 타임스탬프 없음: {timestamp_str}")
            return []
        
        row = matching_rows.iloc[0]
        print(f"DEBUG: 찾은 행 인덱스: {matching_rows.index[0]}")
        
        # NursingRecords_ba30 컬럼에서 간호기록 가져오기
        if 'NursingRecords_ba30' in row.index:
            try:
                nursing_records = row['NursingRecords_ba30']
                print(f"DEBUG: NursingRecords_ba30 타입: {type(nursing_records)}")
                
                # 리스트나 배열인 경우 바로 처리
                if isinstance(nursing_records, (list, np.ndarray)):
                    print(f"DEBUG: 간호기록 개수: {len(nursing_records)}개")
                    if len(nursing_records) > 0:
                        first_record = nursing_records[0]
                        if isinstance(first_record, dict):
                            print(f"DEBUG: 첫 번째 간호기록 키: {list(first_record.keys())}")
                        else:
                            print(f"DEBUG: 첫 번째 간호기록 타입: {type(first_record)}")
                    return list(nursing_records)  # 리스트로 변환하여 반환
                
                # None 체크
                if nursing_records is None:
                    print(f"DEBUG: NursingRecords_ba30이 None")
                    return []
                
                # 스칼라 값에 대해서만 pd.isna 사용
                try:
                    if pd.isna(nursing_records):
                        print(f"DEBUG: NursingRecords_ba30이 NaN")
                        return []
                except:
                    pass
                
                print(f"DEBUG: NursingRecords_ba30이 예상치 못한 타입: {type(nursing_records)}")
                return []
                
            except Exception as e:
                print(f"DEBUG: NursingRecords_ba30 처리 중 오류: {e}")
                return []
        else:
            print(f"DEBUG: NursingRecords_ba30 컬럼이 없음")
            print(f"DEBUG: 사용 가능한 컬럼들: {list(row.index)[:10]}...")  # 처음 10개만 표시
            return []
    
    def get_alarm_annotation(self, patient_id: str, admission_id: str, date_str: str, time_str: str) -> Dict:
        """알람의 classification과 comment 가져오기 (최적화)"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return {'classification': None, 'comment': ''}
        
        # 타임스탬프 구성
        timestamp = f"{date_str} {time_str}"
        
        # 빠른 검색 (벡터화된 연산)
        df_timestamps = df['TimeStamp'].astype(str)
        
        # 정확히 일치하거나 포함하는 것 찾기
        mask = df_timestamps == timestamp
        if not mask.any():
            mask = df_timestamps.str.contains(timestamp, na=False, regex=False)
            if not mask.any():
                mask = (df_timestamps.str.contains(date_str, na=False, regex=False) & 
                       df_timestamps.str.contains(time_str, na=False, regex=False))
        
        if not mask.any():
            return {'classification': None, 'comment': ''}
        
        # 첫 번째 매칭 행 가져오기
        row = df[mask].iloc[0]
        
        # Classification 확인 (빠른 처리)
        classification = None
        if 'Classification' in df.columns:
            classification_val = row['Classification']
            if pd.notna(classification_val):
                if isinstance(classification_val, bool):
                    classification = classification_val
                elif isinstance(classification_val, str):
                    classification_lower = classification_val.lower()
                    if classification_lower == 'true':
                        classification = True
                    elif classification_lower == 'false':
                        classification = False
        
        # Comment 확인 (빠른 처리)
        comment = ''
        if 'Comment' in df.columns:
            comment_val = row['Comment']
            if pd.notna(comment_val):
                comment = str(comment_val)
        
        return {
            'classification': classification,
            'comment': comment
        }
    
    def set_alarm_annotation(self, patient_id: str, admission_id: str, date_str: str, 
                           time_str: str, classification, comment: str) -> bool:
        """알람의 classification과 comment 설정 (최적화된 버전)"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return False
        
        # 타임스탬프 구성
        timestamp = f"{date_str} {time_str}"
        
        # 빠른 검색을 위해 타임스탬프 컬럼을 문자열로 변환한 뒤 비교
        # (인덱싱 사용으로 속도 개선)
        df_timestamps = df['TimeStamp'].astype(str)
        
        # 정확히 일치하는 것 먼저 찾기
        mask = df_timestamps == timestamp
        if not mask.any():
            # 부분 매칭 시도
            mask = df_timestamps.str.contains(timestamp, na=False, regex=False)
            if not mask.any():
                # date_str과 time_str 둘 다 포함하는 것 찾기
                mask = (df_timestamps.str.contains(date_str, na=False, regex=False) & 
                       df_timestamps.str.contains(time_str, na=False, regex=False))
        
        if not mask.any():
            return False
        
        # 첫 번째 매칭되는 인덱스 가져오기
        found_idx = df[mask].index[0]
        
        # 컬럼 확인 및 생성 (한 번만)
        if 'Classification' not in df.columns:
            df['Classification'] = None
        if 'Comment' not in df.columns:
            df['Comment'] = ''
        if 'isSelected' not in df.columns:
            df['isSelected'] = False
        
        # 메모리에만 즉시 업데이트 (파일 저장은 백그라운드로)
        df.loc[found_idx, 'Classification'] = classification
        df.loc[found_idx, 'Comment'] = comment
        if classification is not None:
            df.loc[found_idx, 'isSelected'] = True
        
        # 메모리 캐시 업데이트
        self.patient_dataframes[patient_id] = df
        
        # 백그라운드로 파일 저장 (블로킹 없음)
        self.save_patient_data_async(patient_id)
        
        return True
    

    
    def get_patient_alarm_stats(self, patient_id: str) -> Dict:
        """환자의 알람 통계 정보 반환"""
        df = self._load_patient_data(patient_id)
        if df is None:
            return {'labeled': 0, 'total': 0}
        
        total_count = len(df)
        labeled_count = 0
        
        if 'Classification' in df.columns:
            # Classification이 None이 아닌 경우를 라벨링된 것으로 카운트
            labeled_count = df['Classification'].notna().sum()
        
        return {'labeled': labeled_count, 'total': total_count}
    
    def reload_patient_data(self, patient_id: str):
        """특정 환자의 PKL 파일을 다시 로드"""
        if patient_id in self.patient_dataframes:
            del self.patient_dataframes[patient_id]
        return self._load_patient_data(patient_id)
    
    def reload_all_patients(self):
        """모든 환자 데이터를 다시 로드하여 중복 제거 적용"""
        print("\n=== 모든 환자 데이터 재로드 시작 ===")
        
        # 캠시 초기화
        self.patient_dataframes = {}
        
        # 모든 환자 ID 가져오기
        patient_ids = self.get_all_patient_ids()
        
        total_duplicates_removed = 0
        for patient_id in patient_ids:
            df = self._load_patient_data(patient_id)
            if df is not None:
                print(f"\ud658자 {patient_id}: {len(df)}개 알람")
        
        print(f"\n=== 모든 환자 데이터 재로드 완료 ===")
        print(f"총 {len(patient_ids)}명의 환자 데이터 로드 완료")
        return True
    
    def get_data_summary(self) -> Dict[str, Any]:
        """데이터 요약 정보 반환"""
        patient_ids = self.get_all_patient_ids()
        
        summary = {
            "total_patients": len(patient_ids),
            "patients": {}
        }
        
        for patient_id in patient_ids:
            df = self._load_patient_data(patient_id)
            if df is not None:
                labeled_alarms = 0
                if 'Classification' in df.columns:
                    labeled_alarms = df['Classification'].notna().sum()
                
                patient_summary = {
                    "admission_periods": len(self.get_admission_periods(patient_id)),
                    "total_alarms": len(df),
                    "labeled_alarms": labeled_alarms,
                    "total_nursing_records": 0,
                    "total_waveforms": 0
                }
                
                # 간호기록 수 계산
                if 'NursingRecords_ba30' in df.columns:
                    for nr in df['NursingRecords_ba30']:
                        if pd.notna(nr) and isinstance(nr, list):
                            patient_summary["total_nursing_records"] += len(nr)
                
                # 파형 데이터가 있는 행 수
                waveform_cols = ['ABP_WAVEFORM', 'ECG_WAVEFORM', 'PPG_WAVEFORM', 'RESP_WAVEFORM']
                for col in waveform_cols:
                    if col in df.columns:
                        patient_summary["total_waveforms"] += df[col].notna().sum()
                
                summary["patients"][patient_id] = patient_summary
        
        return summary

# 전역 인스턴스 생성 (기존 코드와의 호환성 유지)
patient_data = PatientDataJson()

# 하위 호환성을 위한 별칭
PatientData = PatientDataJson