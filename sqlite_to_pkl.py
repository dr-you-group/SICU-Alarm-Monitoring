#!/usr/bin/env python3
"""
SQLite 데이터베이스를 PKL 파일로 역변환하는 스크립트
테이블명 = 환자ID (patient_ 접두사 없음)
"""

import pickle
import sqlite3
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

def deserialize_value(value, column_name):
    """JSON 문자열을 원래 타입으로 역직렬화"""
    if value is None:
        return np.nan
    
    # Waveform이나 NursingRecords처럼 JSON으로 저장된 컬럼
    if column_name in ['ABP_WAVEFORM', 'ECG_WAVEFORM', 'PPG_WAVEFORM', 
                      'RESP_WAVEFORM', 'NursingRecords_ba30', 'Label']:
        if value and isinstance(value, str) and value.startswith('['):
            try:
                return json.loads(value)
            except:
                return value
    
    return value

def convert_sqlite_to_pkl(conn, patient_id, output_dir):
    """SQLite 테이블을 PKL 파일로 변환"""
    table_name = f"`{patient_id}`"
    output_file = output_dir / f"{patient_id}.pkl"
    
    print(f"Converting table {patient_id} to {output_file}...")
    
    try:
        # 테이블 데이터 읽기
        query = f"SELECT * FROM {table_name} ORDER BY TimeStamp"
        df = pd.read_sql_query(query, conn)
        
        print(f"  - Loaded {len(df)} rows from database")
        
        # TimeStamp를 pd.Timestamp로 변환
        if 'TimeStamp' in df.columns:
            df['TimeStamp'] = pd.to_datetime(df['TimeStamp'])
        
        # AdmissionIn/Out을 pd.Timestamp로 변환
        for col in ['AdmissionIn', 'AdmissionOut']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Classification, isView, isSelected를 bool로 변환
        for col in ['Classification', 'isView', 'isSelected']:
            if col in df.columns:
                # 0/1을 False/True로, NULL은 NaN으로
                df[col] = df[col].apply(lambda x: bool(x) if pd.notna(x) and x is not None else np.nan)
        
        # JSON으로 저장된 컬럼들 역직렬화
        json_columns = ['ABP_WAVEFORM', 'ECG_WAVEFORM', 'PPG_WAVEFORM', 
                       'RESP_WAVEFORM', 'NursingRecords_ba30', 'Label']
        
        for col in json_columns:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: deserialize_value(x, col))
        
        # 기타 object 타입 컬럼들 확인 및 역직렬화
        for col in df.columns:
            if df[col].dtype == 'object' and col not in json_columns:
                # JSON 문자열인지 확인
                sample = df[col].dropna().head(1)
                if len(sample) > 0:
                    val = sample.iloc[0]
                    if isinstance(val, str) and (val.startswith('[') or val.startswith('{')):
                        print(f"  - Deserializing JSON column: {col}")
                        df[col] = df[col].apply(lambda x: json.loads(x) if x and isinstance(x, str) else x)
        
        # NaN 값 정리 (None을 NaN으로 통일)
        df = df.where(pd.notna(df), np.nan)
        
        # PKL 파일로 저장
        with open(output_file, 'wb') as f:
            pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        print(f"  - Saved {len(df)} rows to {output_file}")
        return True
        
    except Exception as e:
        print(f"Error converting {patient_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # SQLite 데이터베이스 경로
    db_path = "sicu_alarms.db"
    
    if not Path(db_path).exists():
        print(f"ERROR: Database {db_path} not found!")
        return
    
    # 출력 디렉토리 생성
    output_dir = Path("DATA_RESTORED")
    output_dir.mkdir(exist_ok=True)
    
    print(f"Restoring PKL files from {db_path} to {output_dir}/")
    
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    
    # 테이블 목록 가져오기 (sqlite_sequence 제외)
    cursor = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT IN ('sqlite_sequence')
        ORDER BY name
    """)
    tables = cursor.fetchall()
    
    print(f"Found {len(tables)} patient tables to restore")
    
    success_count = 0
    for table in tables:
        patient_id = table[0]
        
        # 해당 테이블의 행 수 확인
        try:
            cursor2 = conn.execute(f"SELECT COUNT(*) FROM `{patient_id}`")
            row_count = cursor2.fetchone()[0]
            print(f"\n{patient_id}: {row_count} rows")
        except:
            print(f"\n{patient_id}: Error counting rows")
            continue
        
        if convert_sqlite_to_pkl(conn, patient_id, output_dir):
            success_count += 1
    
    conn.close()
    
    print(f"\n✅ Restoration complete!")
    print(f"Successfully restored {success_count}/{len(tables)} PKL files")
    print(f"Files saved in: {output_dir}/")
    
    # 원본과 복원된 파일 비교
    if Path("DATA").exists():
        original_files = list(Path("DATA").glob("*.pkl"))
        if original_files:
            original_size = sum(f.stat().st_size for f in original_files) / (1024*1024)
            restored_size = sum(f.stat().st_size for f in output_dir.glob("*.pkl")) / (1024*1024)
            
            print(f"\nSize comparison:")
            print(f"  Original PKL files: {original_size:.2f} MB")
            print(f"  Restored PKL files: {restored_size:.2f} MB")
            print(f"  Difference: {abs(original_size - restored_size):.2f} MB")
    
    # 복원된 파일 검증
    print(f"\n📊 Verification - Sample data from restored files:")
    restored_files = list(output_dir.glob("*.pkl"))[:3]  # 처음 3개만
    
    for pkl_file in restored_files:
        try:
            with open(pkl_file, 'rb') as f:
                df = pickle.load(f)
            
            print(f"\n{pkl_file.name}:")
            print(f"  - Shape: {df.shape}")
            print(f"  - Columns: {df.columns.tolist()[:10]}...")  # 처음 10개 컬럼만
            
            if 'Classification' in df.columns:
                classified = df['Classification'].notna().sum()
                print(f"  - Classification: {classified}/{len(df)} labeled")
            
            if 'isView' in df.columns:
                view_count = (df['isView'] == True).sum()
                print(f"  - isView=True: {view_count}/{len(df)}")
                
        except Exception as e:
            print(f"\n{pkl_file.name}: Error loading - {e}")

if __name__ == "__main__":
    main()
