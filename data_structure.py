#!/usr/bin/env python3
"""
SQLite 기반 데이터 관리 - 빠른 개별 행 업데이트 지원
테이블명 = patient ID (patient_ 접두사 없음)
"""

import sqlite3
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

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

class PatientDataSQLite:
    """SQLite 기반 빠른 데이터 관리"""
    
    def __init__(self, db_path: str = "sicu_alarms.db"):
        self.db_path = db_path
        
        if not Path(db_path).exists():
            print(f"[WARNING] Database not found: {db_path}")
            print(f"Please run 'python pkl_to_sqlite.py' first to convert PKL files to SQLite")
    
    @contextmanager
    def get_connection(self):
        """컨텍스트 관리자로 안전한 DB 연결"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        try:
            yield conn
        finally:
            conn.close()
    
    def _deserialize_json(self, value):
        """JSON 문자열을 Python 객체로 변환"""
        if value is None or value == '':
            return None
        if isinstance(value, str) and value.startswith('['):
            try:
                return json.loads(value)
            except:
                return value
        return value
    
    def get_all_patient_ids(self) -> List[str]:
        """모든 환자 ID 목록 (테이블명에서 가져옴)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' 
                    AND name NOT IN ('sqlite_sequence')
                    ORDER BY name
                """)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] Failed to get patient IDs: {e}")
            return []
    
    def get_patient_info(self, patient_id: str) -> Optional[Dict]:
        """환자 정보"""
        try:
            with self.get_connection() as conn:
                table_name = f"`{patient_id}`"
                
                # isView 컬럼 존재 확인
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                has_isView = 'isView' in columns
                
                # 전체 행 수
                if has_isView:
                    cursor = conn.execute(f"""
                        SELECT COUNT(*) FROM {table_name} 
                        WHERE isView = 1 
                           OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                               AND (AdmissionOut IS NULL OR AdmissionOut = ''))
                    """)
                else:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                total_count = cursor.fetchone()[0]
                
                # 라벨링된 행 수
                if 'Classification' in columns:
                    if has_isView:
                        cursor = conn.execute(f"""
                            SELECT COUNT(*) FROM {table_name} 
                            WHERE Classification IS NOT NULL
                              AND (isView = 1 
                                   OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                                       AND (AdmissionOut IS NULL OR AdmissionOut = '')))
                        """)
                    else:
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name} WHERE Classification IS NOT NULL")
                    labeled_count = cursor.fetchone()[0]
                else:
                    labeled_count = 0
                
                return {
                    'patient_id': patient_id,
                    'total_alarms': total_count,
                    'labeled_alarms': labeled_count
                }
        except Exception as e:
            print(f"[ERROR] Failed to get patient info for {patient_id}: {e}")
            return None
    
    def get_admission_periods(self, patient_id: str) -> List[Dict]:
        """입원 기간 목록"""
        try:
            with self.get_connection() as conn:
                table_name = f"`{patient_id}`"
                
                # isView 컬럼 존재 확인
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                has_isView = 'isView' in columns
                
                if has_isView:
                    query = f"""
                        SELECT DISTINCT AdmissionIn, AdmissionOut 
                        FROM {table_name} 
                        WHERE AdmissionIn IS NOT NULL
                        AND (isView = 1 
                             OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                                 AND (AdmissionOut IS NULL OR AdmissionOut = '')))
                        ORDER BY AdmissionIn
                    """
                else:
                    query = f"""
                        SELECT DISTINCT AdmissionIn, AdmissionOut 
                        FROM {table_name} 
                        WHERE AdmissionIn IS NOT NULL
                        ORDER BY AdmissionIn
                    """
                
                cursor = conn.execute(query)
                
                admission_periods = []
                for row in cursor.fetchall():
                    start_date = str(row[0]).split(' ')[0]
                    # AdmissionOut이 NULL이거나 빈 문자열인 경우 처리 (현재 입원 중)
                    if row[1] is None or str(row[1]) == 'None' or str(row[1]) == '' or str(row[1]).strip() == '':
                        end_date = 'Ongoing'  # 현재 입원 중
                        admission_id = f"{start_date}_ongoing"
                    else:
                        end_date = str(row[1]).split(' ')[0]
                        admission_id = f"{start_date}_{end_date}"
                    
                    admission_periods.append({
                        'id': admission_id,
                        'start': start_date,
                        'end': end_date
                    })
                
                return admission_periods if admission_periods else [{'id': 'default', 'start': 'N/A', 'end': 'N/A'}]
        except Exception as e:
            print(f"[ERROR] Failed to get admission periods: {e}")
            return [{'id': 'default', 'start': 'N/A', 'end': 'N/A'}]
    
    def get_available_dates(self, patient_id: str, admission_id: str = None) -> List[str]:
        """알람 날짜 목록"""
        try:
            with self.get_connection() as conn:
                table_name = f"`{patient_id}`"
                
                # isView 컬럼 존재 확인
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                has_isView = 'isView' in columns
                
                if has_isView:
                    query = f"""
                        SELECT DISTINCT date(TimeStamp) as alarm_date
                        FROM {table_name}
                        WHERE isView = 1 
                           OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                               AND (AdmissionOut IS NULL OR AdmissionOut = ''))
                    """
                else:
                    query = f"""
                        SELECT DISTINCT date(TimeStamp) as alarm_date
                        FROM {table_name}
                        WHERE 1=1
                    """
                
                if admission_id and admission_id != 'default':
                    parts = admission_id.split('_')
                    if len(parts) == 2:
                        if parts[1] == 'ongoing':  # 현재 입원 중인 경우
                            query += f" AND date(AdmissionIn) = '{parts[0]}' AND (AdmissionOut IS NULL OR AdmissionOut = '')"
                        else:
                            query += f" AND date(AdmissionIn) = '{parts[0]}' AND date(AdmissionOut) = '{parts[1]}'"
                
                query += " ORDER BY alarm_date"
                
                cursor = conn.execute(query)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] Failed to get available dates: {e}")
            return []
    
    def get_alarms_for_date(self, patient_id: str, admission_id: str, date_str: str) -> List[Dict]:
        """특정 날짜의 알람 목록"""
        try:
            with self.get_connection() as conn:
                table_name = f"`{patient_id}`"
                
                # isView 컬럼 존재 확인
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                has_isView = 'isView' in columns
                
                if has_isView:
                    query = f"""
                        SELECT TimeStamp, Label, SeverityColor, Severity, Classification, Comment
                        FROM {table_name}
                        WHERE date(TimeStamp) = ? 
                          AND (isView = 1 
                               OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                                   AND (AdmissionOut IS NULL OR AdmissionOut = '')))
                    """
                else:
                    query = f"""
                        SELECT TimeStamp, Label, SeverityColor, Severity, Classification, Comment
                        FROM {table_name}
                        WHERE date(TimeStamp) = ?
                    """
                
                params = [date_str]
                
                if admission_id and admission_id != 'default':
                    parts = admission_id.split('_')
                    if len(parts) == 2:
                        if parts[1] == 'ongoing':  # 현재 입원 중인 경우
                            query += " AND date(AdmissionIn) = ? AND (AdmissionOut IS NULL OR AdmissionOut = '')"
                            params.append(parts[0])
                        else:
                            query += " AND date(AdmissionIn) = ? AND date(AdmissionOut) = ?"
                            params.extend(parts)
                
                query += " ORDER BY TimeStamp"
                
                cursor = conn.execute(query, params)
                
                alarms = []
                for row in cursor.fetchall():
                    timestamp_str = str(row['TimeStamp'])
                    alarm_time = timestamp_str.split(' ')[1] if ' ' in timestamp_str else '00:00:00'
                    
                    # Label 처리
                    label_str = ""
                    if 'Label' in row.keys() and row['Label']:
                        label_data = self._deserialize_json(row['Label'])
                        if label_data:
                            if isinstance(label_data, list):
                                label_str = ' / '.join(str(l) for l in label_data)
                            else:
                                label_str = str(label_data)
                    
                    # Classification 처리 (0/1 -> False/True)
                    classification = None
                    if 'Classification' in row.keys() and row['Classification'] is not None:
                        classification = bool(row['Classification'])
                    
                    alarms.append({
                        'time': alarm_time,
                        'color': row['SeverityColor'] if row['SeverityColor'] else 'White',
                        'severity': row['Severity'] if row['Severity'] else '',
                        'label': label_str,
                        'classification': classification,
                        'comment': row['Comment'] if row['Comment'] else ''
                    })
                
                return alarms
        except Exception as e:
            print(f"[ERROR] Failed to get alarms for date: {e}")
            return []
    
    def get_alarm_annotation(self, patient_id: str, admission_id: str, date_str: str, time_str: str) -> Dict:
        """annotation 가져오기"""
        try:
            with self.get_connection() as conn:
                table_name = f"`{patient_id}`"
                timestamp = f"{date_str} {time_str}"
                
                # isView 컬럼 존재 확인
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                has_isView = 'isView' in columns
                
                # 정확한 매칭 또는 시:분:초까지만 매칭
                if has_isView:
                    query = f"""
                        SELECT Classification, Comment 
                        FROM {table_name}
                        WHERE (TimeStamp = ? OR TimeStamp LIKE ?)
                        AND (isView = 1 
                             OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                                 AND (AdmissionOut IS NULL OR AdmissionOut = '')))
                        LIMIT 1
                    """
                else:
                    query = f"""
                        SELECT Classification, Comment 
                        FROM {table_name}
                        WHERE (TimeStamp = ? OR TimeStamp LIKE ?)
                        LIMIT 1
                    """
                
                time_prefix = timestamp.split('.')[0]  # 마이크로초 제외
                cursor = conn.execute(query, (timestamp, f"{time_prefix}%"))
                row = cursor.fetchone()
                
                if row:
                    classification = bool(row['Classification']) if row['Classification'] is not None else None
                    comment = row['Comment'] if row['Comment'] else ''
                    return {'classification': classification, 'comment': comment}
                
                return {'classification': None, 'comment': ''}
        except Exception as e:
            print(f"[ERROR] Failed to get annotation: {e}")
            return {'classification': None, 'comment': ''}
    
    def set_alarm_annotation(self, patient_id: str, admission_id: str, date_str: str, 
                           time_str: str, classification, comment: str) -> bool:
        """annotation 저장 - 매우 빠른 업데이트!"""
        try:
            with self.get_connection() as conn:
                table_name = f"`{patient_id}`"
                timestamp = f"{date_str} {time_str}"
                
                # isView 컬럼 존재 확인
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                has_isView = 'isView' in columns
                has_isSelected = 'isSelected' in columns
                
                # Classification을 0/1로 변환
                class_value = None
                if classification is not None:
                    class_value = 1 if classification else 0
                
                # UPDATE 쿼리 - 정확한 매칭 또는 시:분:초까지 매칭
                if has_isView:
                    if has_isSelected:
                        update_query = f"""
                            UPDATE {table_name}
                            SET Classification = ?, Comment = ?, isSelected = ?
                            WHERE (TimeStamp = ? OR TimeStamp LIKE ?)
                            AND (isView = 1 
                                 OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                                     AND (AdmissionOut IS NULL OR AdmissionOut = '')))
                        """
                        isSelected = 1 if classification is not None else 0
                        params = (class_value, comment, isSelected, timestamp, f"{timestamp.split('.')[0]}%")
                    else:
                        update_query = f"""
                            UPDATE {table_name}
                            SET Classification = ?, Comment = ?
                            WHERE (TimeStamp = ? OR TimeStamp LIKE ?)
                            AND (isView = 1 
                                 OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                                     AND (AdmissionOut IS NULL OR AdmissionOut = '')))
                        """
                        params = (class_value, comment, timestamp, f"{timestamp.split('.')[0]}%")
                else:
                    if has_isSelected:
                        update_query = f"""
                            UPDATE {table_name}
                            SET Classification = ?, Comment = ?, isSelected = ?
                            WHERE (TimeStamp = ? OR TimeStamp LIKE ?)
                        """
                        isSelected = 1 if classification is not None else 0
                        params = (class_value, comment, isSelected, timestamp, f"{timestamp.split('.')[0]}%")
                    else:
                        update_query = f"""
                            UPDATE {table_name}
                            SET Classification = ?, Comment = ?
                            WHERE (TimeStamp = ? OR TimeStamp LIKE ?)
                        """
                        params = (class_value, comment, timestamp, f"{timestamp.split('.')[0]}%")
                
                cursor = conn.execute(update_query, params)
                conn.commit()
                
                if cursor.rowcount > 0:
                    print(f"[DEBUG] Updated {cursor.rowcount} row(s) for {patient_id} at {timestamp}")
                    return True
                else:
                    print(f"[WARNING] No rows updated for {patient_id} at {timestamp}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Failed to save annotation: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_waveform_data(self, patient_id: str, timestamp: str) -> Optional[Dict]:
        """파형 데이터"""
        try:
            with self.get_connection() as conn:
                table_name = f"`{patient_id}`"
                
                # isView 컬럼 존재 확인
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                has_isView = 'isView' in columns
                
                if has_isView:
                    query = f"""
                        SELECT * FROM {table_name}
                        WHERE (TimeStamp = ? OR TimeStamp LIKE ?)
                        AND (isView = 1 
                             OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                                 AND (AdmissionOut IS NULL OR AdmissionOut = '')))
                        LIMIT 1
                    """
                else:
                    query = f"""
                        SELECT * FROM {table_name}
                        WHERE (TimeStamp = ? OR TimeStamp LIKE ?)
                        LIMIT 1
                    """
                
                time_prefix = timestamp.split('.')[0]
                cursor = conn.execute(query, (timestamp, f"{time_prefix}%"))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                waveform_data = {}
                
                # 파형 신호
                waveform_mappings = {
                    'ABP': 'ABP_WAVEFORM',
                    'Lead-II': 'ECG_WAVEFORM',
                    'Pleth': 'PPG_WAVEFORM',
                    'Resp': 'RESP_WAVEFORM'
                }
                
                for display_name, column_name in waveform_mappings.items():
                    if column_name in columns and row[column_name]:
                        waveform = self._deserialize_json(row[column_name])
                        if waveform and isinstance(waveform, list):
                            waveform_data[display_name] = np.array(waveform, dtype=np.float64)
                        else:
                            waveform_data[display_name] = np.array([])
                    else:
                        waveform_data[display_name] = np.array([])
                
                # Numeric 데이터
                numeric_data = {}
                numeric_params = ['SpO2', 'Pulse', 'ST', 'Tskin', 'ABP', 'NBP', 'HR', 'RR']
                
                for param in numeric_params:
                    value_col = f"{param}_numeric"
                    time_diff_col = f"{param}_numeric_time_diff_sec"
                    
                    value = None
                    time_diff = None
                    
                    if value_col in columns and row[value_col] is not None:
                        value = row[value_col]
                    if time_diff_col in columns and row[time_diff_col] is not None:
                        time_diff = row[time_diff_col]
                    
                    numeric_data[param] = [value, time_diff]
                
                if numeric_data:
                    waveform_data['Numeric'] = numeric_data
                
                # AlarmLabel
                if 'Label' in columns and row['Label']:
                    label_data = self._deserialize_json(row['Label'])
                    if label_data:
                        if isinstance(label_data, list):
                            waveform_data['AlarmLabel'] = ' / '.join(str(l) for l in label_data)
                        else:
                            waveform_data['AlarmLabel'] = str(label_data)
                    else:
                        waveform_data['AlarmLabel'] = ""
                else:
                    waveform_data['AlarmLabel'] = ""
                
                return waveform_data
                
        except Exception as e:
            print(f"[ERROR] Failed to get waveform data: {e}")
            return None
    
    def get_nursing_records_for_alarm(self, patient_id: str, timestamp_str: str) -> List[Dict]:
        """간호기록"""
        try:
            with self.get_connection() as conn:
                table_name = f"`{patient_id}`"
                
                # isView 컬럼 존재 확인  
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                has_isView = 'isView' in columns
                
                if has_isView:
                    query = f"""
                        SELECT NursingRecords_ba30 FROM {table_name}
                        WHERE (TimeStamp = ? OR TimeStamp LIKE ?)
                        AND (isView = 1 
                             OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                                 AND (AdmissionOut IS NULL OR AdmissionOut = '')))
                        LIMIT 1
                    """
                else:
                    query = f"""
                        SELECT NursingRecords_ba30 FROM {table_name}
                        WHERE (TimeStamp = ? OR TimeStamp LIKE ?)
                        LIMIT 1
                    """
                
                time_prefix = timestamp_str.split('.')[0]
                cursor = conn.execute(query, (timestamp_str, f"{time_prefix}%"))
                row = cursor.fetchone()
                
                if row and 'NursingRecords_ba30' in columns and row['NursingRecords_ba30']:
                    records = self._deserialize_json(row['NursingRecords_ba30'])
                    if records and isinstance(records, list):
                        return records
                
                return []
                
        except Exception as e:
            print(f"[ERROR] Failed to get nursing records: {e}")
            return []
    
    def get_patient_alarm_stats(self, patient_id: str) -> Dict:
        """환자 알람 통계"""
        try:
            with self.get_connection() as conn:
                table_name = f"`{patient_id}`"
                
                # 컬럼 존재 확인
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                has_isView = 'isView' in columns
                has_classification = 'Classification' in columns
                
                # 전체 카운트 - isView 조건 제거 또는 완화
                # AdmissionIn만 있는 경우도 포함하기 위해
                if has_isView:
                    # isView=1이거나 AdmissionIn만 있는 경우도 포함
                    cursor = conn.execute(f"""
                        SELECT COUNT(*) FROM {table_name} 
                        WHERE isView = 1 
                           OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                               AND (AdmissionOut IS NULL OR AdmissionOut = ''))
                    """)
                else:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                total_count = cursor.fetchone()[0]
                
                # 라벨링된 카운트
                labeled_count = 0
                if has_classification:
                    if has_isView:
                        cursor = conn.execute(f"""
                            SELECT COUNT(*) FROM {table_name} 
                            WHERE Classification IS NOT NULL
                              AND (isView = 1 
                                   OR (AdmissionIn IS NOT NULL AND AdmissionIn != '' 
                                       AND (AdmissionOut IS NULL OR AdmissionOut = '')))
                        """)
                    else:
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name} WHERE Classification IS NOT NULL")
                    labeled_count = cursor.fetchone()[0]
                
                return {'labeled': labeled_count, 'total': total_count}
                
        except Exception as e:
            print(f"[ERROR] Failed to get patient alarm stats: {e}")
            return {'labeled': 0, 'total': 0}

# 전역 인스턴스 - 기존 코드와의 호환성
patient_data = PatientDataSQLite()

# 하위 호환성
PatientData = PatientDataSQLite
PatientDataJson = PatientDataSQLite
