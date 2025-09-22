#!/usr/bin/env python3
"""
PKL 파일들을 SQLite 데이터베이스로 변환하는 스크립트
각 환자별 테이블 생성 (테이블명 = AlsUnitNo)
"""

import pickle
import sqlite3
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import sys
import traceback

def json_encoder(obj):
    """JSON encoder로 처리할 수 없는 객체들 처리"""
    if isinstance(obj, (pd.Timestamp, datetime)):
        return str(obj)
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    # pd.isna는 단일 값에 대해서만 안전하게 체크
    else:
        try:
            if pd.isna(obj):
                return None
        except:
            pass
        return str(obj)  # 최후의 수단: 문자열로 변환

def serialize_value(value):
    """복잡한 데이터 타입을 JSON 문자열로 직렬화"""
    # None 체크
    if value is None:
        return None
    
    # 리스트나 numpy 배열 체크
    if isinstance(value, (list, np.ndarray)):
        try:
            # json.dumps에 default encoder 사용 - 모든 타입 처리
            if isinstance(value, np.ndarray) and value.size > 100000:
                print(f"    Warning: Large array with {value.size} elements")
                # 큰 배열은 처음 100000개만
                truncated = value.flatten()[:100000]
                return json.dumps(truncated, default=json_encoder)
            else:
                return json.dumps(value, default=json_encoder)
        except Exception as e:
            print(f"    Warning: Failed to serialize array/list: {e}")
            # 최후의 시도: 모든 요소를 문자열로
            try:
                if isinstance(value, np.ndarray):
                    converted = [str(item) for item in value.flatten()[:10000]]
                else:
                    converted = [str(item) for item in value[:10000]]
                return json.dumps(converted)
            except:
                return json.dumps([])
    
    # Timestamp 처리
    elif isinstance(value, (pd.Timestamp, datetime)):
        return str(value)
    
    # Boolean 처리
    elif isinstance(value, (bool, np.bool_)):
        return int(value)
    
    # Numpy 숫자 타입
    elif isinstance(value, (np.integer, np.floating)):
        return value.item()
    
    # pandas NA - try-except로 안전하게
    else:
        try:
            if pd.isna(value):
                return None
        except:
            pass
        return value

def get_sql_type(dtype, column_name):
    """pandas dtype을 SQLite 타입으로 변환"""
    # Boolean 컬럼들
    if column_name in ['Classification', 'isView', 'isSelected']:
        return 'INTEGER'
    
    # Waveform이나 리스트 데이터
    if 'WAVEFORM' in column_name or 'Records' in column_name or column_name == 'Label':
        return 'TEXT'
    
    # dtype 기반 판단
    dtype_str = str(dtype).lower()
    
    if 'datetime' in dtype_str or 'timestamp' in dtype_str:
        return 'TEXT'
    elif 'int' in dtype_str:
        return 'INTEGER'
    elif 'float' in dtype_str or 'double' in dtype_str:
        return 'REAL'
    elif 'bool' in dtype_str:
        return 'INTEGER'
    elif 'object' in dtype_str:
        return 'TEXT'
    else:
        return 'TEXT'

def create_table_dynamic(conn, patient_id, df):
    """DataFrame의 모든 컬럼을 기반으로 동적으로 테이블 생성"""
    # 테이블명은 환자 ID 그대로 사용 (숫자로 시작하는 경우 백틱으로 감싸기)
    table_name = f"`{patient_id}`"
    
    # 테이블 컬럼 정의 생성
    columns = []
    
    for col in df.columns:
        sql_type = get_sql_type(df[col].dtype, col)
        
        # TimeStamp는 UNIQUE 제약 추가
        if col == 'TimeStamp':
            columns.append(f"{col} {sql_type} UNIQUE")
        else:
            columns.append(f"{col} {sql_type}")
    
    # CREATE TABLE 쿼리
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        {', '.join(columns)}
    );
    """
    
    try:
        conn.execute(create_query)
        
        # 인덱스 추가
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{patient_id}_timestamp ON {table_name} (TimeStamp);")
        
        # Classification과 isView에 인덱스 추가 (있는 경우만)
        if 'Classification' in df.columns:
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{patient_id}_classification ON {table_name} (Classification);")
        if 'isView' in df.columns:
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{patient_id}_isview ON {table_name} (isView);")
            
        print(f"  - Created table with {len(df.columns)} columns")
        
    except Exception as e:
        print(f"Error creating table: {e}")
        raise

def convert_pkl_to_sqlite(pkl_file, conn):
    """단일 PKL 파일을 SQLite 테이블로 변환"""
    patient_id = pkl_file.stem
    print(f"Converting {patient_id}.pkl...")
    
    try:
        # PKL 파일 로드
        with open(pkl_file, 'rb') as f:
            df = pickle.load(f)
        
        print(f"  - Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # 중복 제거 (TimeStamp 기준)
        if 'TimeStamp' in df.columns:
            original_len = len(df)
            df = df.drop_duplicates(subset=['TimeStamp'], keep='first')
            if len(df) < original_len:
                print(f"  - Removed {original_len - len(df)} duplicate rows")
        
        # 테이블 생성 (동적으로)
        create_table_dynamic(conn, patient_id, df)
        table_name = f"`{patient_id}`"
        
        # 데이터 삽입
        inserted = 0
        failed = 0
        
        # 문제가 될 수 있는 컬럼들 미리 확인
        problematic_columns = set()
        for col in df.columns:
            sample = df[col].dropna().head(1)
            if len(sample) > 0:
                val = sample.iloc[0]
                if isinstance(val, (list, np.ndarray)):
                    problematic_columns.add(col)
                    print(f"  - Column '{col}' contains array/list data")
        
        for idx, row in df.iterrows():
            values = []
            
            # 모든 컬럼 값 처리
            for col in df.columns:
                value = row[col]
                
                # Boolean 컬럼 특별 처리
                if col in ['Classification', 'isView', 'isSelected']:
                    try:
                        if pd.notna(value):
                            if isinstance(value, (bool, np.bool_)):
                                values.append(1 if value else 0)
                            elif isinstance(value, (int, float, np.integer, np.floating)):
                                values.append(1 if value else 0)
                            else:
                                values.append(None)
                        else:
                            values.append(None)
                    except:
                        values.append(None)
                # 문제가 될 수 있는 컬럼들 특별 처리
                elif col in problematic_columns:
                    try:
                        if value is None or (isinstance(value, float) and np.isnan(value)):
                            values.append(None)
                        else:
                            # json encoder로 안전하게 처리
                            values.append(json.dumps(value, default=json_encoder))
                    except Exception as e:
                        print(f"      Error in problematic column {col}: {e}")
                        values.append(None)
                else:
                    # 일반 값 직렬화
                    values.append(serialize_value(value))
            
            # INSERT 쿼리 생성
            placeholders = ','.join(['?' for _ in range(len(values))])
            column_names = ','.join(df.columns)
            insert_query = f"""
            INSERT OR REPLACE INTO {table_name} ({column_names})
            VALUES ({placeholders})
            """
            
            try:
                conn.execute(insert_query, values)
                inserted += 1
                
                if inserted % 100 == 0:  # 진행 상황 표시
                    print(f"    - Progress: {inserted}/{len(df)} rows...")
                    
            except sqlite3.IntegrityError as e:
                # UNIQUE 제약 위반 (중복 TimeStamp)
                if "UNIQUE constraint failed" in str(e):
                    pass  # 무시
                else:
                    failed += 1
                    if failed <= 5:  # 처음 5개 에러만 출력
                        print(f"    Error inserting row {idx}: {e}")
                        
            except Exception as e:
                failed += 1
                if failed <= 5:  # 처음 5개 에러만 출력
                    print(f"    Error inserting row {idx}: {e}")
        
        conn.commit()
        print(f"  - Successfully inserted {inserted} rows")
        if failed > 0:
            print(f"  - Failed to insert {failed} rows")
        
        return True
        
    except Exception as e:
        print(f"Error converting {pkl_file}: {e}")
        traceback.print_exc()
        return False

def main():
    # DATA 디렉토리 확인
    data_dir = Path("DATA")
    if not data_dir.exists():
        print(f"ERROR: DATA directory not found!")
        return
    
    # SQLite 데이터베이스 생성
    db_path = "sicu_alarms.db"
    
    # 기존 DB가 있으면 백업
    if Path(db_path).exists():
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"Backing up existing database to {backup_path}")
        Path(db_path).rename(backup_path)
    
    print(f"Creating SQLite database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    
    # foreign_keys 활성화 (필요한 경우)
    conn.execute("PRAGMA foreign_keys = ON")
    
    # 모든 PKL 파일 변환
    pkl_files = sorted(data_dir.glob("*.pkl"))
    print(f"Found {len(pkl_files)} PKL files to convert")
    
    success_count = 0
    for i, pkl_file in enumerate(pkl_files, 1):
        print(f"\n[{i}/{len(pkl_files)}] ", end="")
        
        if convert_pkl_to_sqlite(pkl_file, conn):
            success_count += 1
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✅ Conversion complete!")
    print(f"Successfully converted {success_count}/{len(pkl_files)} PKL files")
    print(f"Database saved as: {db_path}")
    
    # 데이터베이스 크기 확인
    db_size = Path(db_path).stat().st_size / (1024*1024)
    print(f"Database size: {db_size:.2f} MB")
    
    # 원본 PKL 파일 크기와 비교
    pkl_size = sum(f.stat().st_size for f in pkl_files) / (1024*1024)
    print(f"Original PKL files size: {pkl_size:.2f} MB")
    print(f"Compression ratio: {(db_size/pkl_size)*100:.1f}%")
    
    # 생성된 테이블 목록 확인
    print(f"\n📊 Created tables:")
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    for table in tables:
        # sqlite_sequence 테이블은 제외하고 표시
        if table[0] != 'sqlite_sequence':
            cursor2 = conn.execute(f"SELECT COUNT(*) FROM `{table[0]}`")
            row_count = cursor2.fetchone()[0]
            print(f"  - {table[0]}: {row_count} rows")
    conn.close()

if __name__ == "__main__":
    main()
