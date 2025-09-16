#!/usr/bin/env python3
"""
간호기록 TSV 파일과 비교하여 알람의 True/False를 자동 판정하는 모듈
"""

import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

class AlarmValidator:
    def __init__(self, tsv_file_path: str = "data_processing/nr_alarm_true_list.tsv"):
        """
        Args:
            tsv_file_path: True 알람 판정을 위한 간호기록 TSV 파일 경로
        """
        self.tsv_file_path = tsv_file_path
        self.true_alarm_records = []
        self.load_true_alarm_records()
    
    def load_true_alarm_records(self):
        """TSV 파일에서 True 알람 판정용 간호기록 로드"""
        self.true_alarm_records = []
        
        if not os.path.exists(self.tsv_file_path):
            print(f"TSV 파일을 찾을 수 없습니다: {self.tsv_file_path}")
            return
        
        try:
            with open(self.tsv_file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                
                for row in reader:
                    # 5개 컬럼만 저장 (간호속성명칭 제외)
                    record = {
                        "간호진단프로토콜(코드명)": row.get("간호진단프로토콜(코드명)", "").strip(),
                        "간호중재(코드명)": row.get("간호중재(코드명) ", row.get("간호중재(코드명)", "")).strip(),  # 공백 있는 버전도 체크
                        "간호활동(코드명)": row.get("간호활동(코드명) ", row.get("간호활동(코드명)", "")).strip(),  # 공백 있는 버전도 체크
                        "간호속성코드(코드명)": row.get("간호속성코드(코드명)", "").strip(),
                        "속성": row.get("속성", "").strip()
                    }
                    self.true_alarm_records.append(record)
            
            print(f"True 알람 판정 기록 로드 완료: {len(self.true_alarm_records)}개")
            
        except Exception as e:
            print(f"TSV 파일 로드 오류: {e}")
    
    def normalize_string(self, s: str) -> str:
        """문자열 정규화 (비교를 위해 공백 제거 및 소문자 변환)"""
        if s is None:
            return ""
        s = str(s)
        # 공백 제거, 소문자 변환, 특수문자 정규화
        return s.strip().lower().replace(" ", "").replace("(", "").replace(")", "")
    
    def compare_records(self, nursing_record: Dict, true_alarm_record: Dict) -> bool:
        """
        두 기록이 일치하는지 비교 (5개 컬럼)
        
        Args:
            nursing_record: 실제 간호기록
            true_alarm_record: TSV 파일의 True 알람 기록
            
        Returns:
            모든 5개 컬럼이 일치하면 True, 아니면 False
        """
        # 비교할 컬럼들 (간호속성명칭 제외)
        columns_to_compare = [
            "간호진단프로토콜(코드명)",
            "간호중재(코드명)",
            "간호활동(코드명)",
            "간호속성코드(코드명)",
            "속성"
        ]
        
        for column in columns_to_compare:
            # 정규화된 값으로 비교
            nursing_value = self.normalize_string(nursing_record.get(column, ""))
            true_alarm_value = self.normalize_string(true_alarm_record.get(column, ""))
            
            # 하나라도 다르면 False
            if nursing_value != true_alarm_value:
                return False
        
        # 모든 컬럼이 일치하면 True
        return True
    
    def validate_alarm(self, nursing_records: List[Dict]) -> Tuple[bool, Optional[Dict]]:
        """
        알람 시간 기준 ±30분 간호기록을 검사하여 True/False 판정
        
        Args:
            nursing_records: 알람 시간 ±30분 내의 간호기록 리스트
            
        Returns:
            (is_true_alarm, matched_record): True 알람 여부와 매칭된 기록
        """
        # 간호기록이 없으면 False
        if not nursing_records:
            return False, None
        
        # 각 간호기록을 TSV 파일의 기록들과 비교
        for nursing_record in nursing_records:
            for true_alarm_record in self.true_alarm_records:
                if self.compare_records(nursing_record, true_alarm_record):
                    # 일치하는 기록을 찾으면 True 알람
                    return True, nursing_record
        
        # 일치하는 기록이 없으면 False 알람
        return False, None
    
    def validate_and_save_alarm(self, patient_id: str, admission_id: str, 
                               alarm_timestamp: str, nursing_records: List[Dict]) -> bool:
        """
        알람을 검증하고 결과를 JSON에 저장
        
        Args:
            patient_id: 환자 ID
            admission_id: 입원 기간 ID
            alarm_timestamp: 알람 발생 시간 (YYYY-MM-DD HH:MM:SS)
            nursing_records: 알람 시간 ±30분 내의 간호기록
            
        Returns:
            True 알람 여부
        """
        # 알람 검증
        is_true_alarm, matched_record = self.validate_alarm(nursing_records)
        
        # 날짜와 시간 분리
        try:
            dt = datetime.strptime(alarm_timestamp, "%Y-%m-%d %H:%M:%S")
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
            
            # 코멘트는 빈 공간으로
            comment = ""
            
            # JSON에 직접 저장
            from data_structure import patient_data
            success = patient_data.set_alarm_annotation(
                patient_id, admission_id, date_str, time_str, is_true_alarm, comment
            )
            
            if not success:
                print(f"알람 저장 실패: {patient_id}-{date_str}-{time_str}")
                return False
            
        except Exception as e:
            print(f"알람 저장 오류: {e}")
            return False
        
        return is_true_alarm
    
    def process_all_alarms(self, patient_data_json):
        """
        모든 환자의 모든 알람에 대해 자동 판정 수행 (JSON 저장 방식)
        
        Args:
            patient_data_json: PatientDataJson 인스턴스
        """
        processed_count = 0
        true_alarm_count = 0
        
        # 모든 환자 ID 가져오기
        patient_ids = patient_data_json.get_all_patient_ids()
        total_patients = len(patient_ids)
        
        for idx, patient_id in enumerate(patient_ids):
            print(f"\n환자 {patient_id} 처리 중... ({idx+1}/{total_patients})")
            
            # 입원 기간들 가져오기
            admission_periods = patient_data_json.get_admission_periods(patient_id)
            
            for admission in admission_periods:
                admission_id = admission['id']
                
                # 해당 입원 기간의 날짜들 가져오기
                dates = patient_data_json.get_available_dates(patient_id, admission_id)
                
                for date_str in dates:
                    # 해당 날짜의 알람들 가져오기
                    alarms = patient_data_json.get_alarms_for_date(patient_id, admission_id, date_str)
                    
                    for alarm in alarms:
                        # 알람 타임스탬프 생성
                        alarm_timestamp = f"{date_str} {alarm['time']}"
                        
                        # 이미 저장된 annotation이 있는지 확인
                        existing_annotation = patient_data_json.get_alarm_annotation(
                            patient_id, admission_id, date_str, alarm['time']
                        )
                        if existing_annotation['classification'] is not None:
                            # 이미 라벨링된 경우 건너뛰기
                            continue
                        
                        # 간호기록 가져오기
                        nursing_records = patient_data_json.get_nursing_records_for_alarm(
                            patient_id, alarm_timestamp
                        )
                        
                        # 자동 판정 및 저장
                        is_true = self.validate_and_save_alarm(
                            patient_id, admission_id, alarm_timestamp, nursing_records
                        )
                        
                        processed_count += 1
                        if is_true:
                            true_alarm_count += 1
                        
                        # 진행 상황 출력 (100개마다)
                        if processed_count % 100 == 0:
                            print(f"  진행중... {processed_count}개 처리 (True: {true_alarm_count})")
        
        print(f"\n자동 판정 완료:")
        print(f"  처리된 알람: {processed_count}개")
        print(f"  True 알람: {true_alarm_count}개")
        print(f"  False 알람: {processed_count - true_alarm_count}개")
        
        return processed_count, true_alarm_count


# 독립 실행용 스크립트
if __name__ == "__main__":
    from data_structure import PatientDataJson
    
    # 인스턴스 생성
    validator = AlarmValidator("data_processing/nr_alarm_true_list.tsv")
    patient_data = PatientDataJson()
    
    # 모든 알람 자동 판정 (JSON 저장 방식)
    print("알람 자동 판정을 시작합니다... (JSON 저장)")
    validator.process_all_alarms(patient_data)
    print("완료!")
