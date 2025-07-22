"""알람 필터링 시스템

이 모듈은 SICU 알람 모니터링 시스템에서 알람을 필터링하는 기능을 제공합니다.
주요 기능:
- 간호기록이 없는 알람 필터링: 알람 시간 기준 ±30분(설정 가능) 범위 내에 간호기록이 없는 알람을 제거
- 기술적 알람 필터링: Filtered_AlarmLabelList.txt에 있는 기술적/장비 오류 알람을 제거
- 필터 활성화/비활성화: UI에서 실시간으로 필터를 켜고 끌 수 있음
- 시간 범위 조정: 간호기록 확인 시간 범위를 동적으로 변경 가능

사용 예:
    # 기본 필터 사용 (30분 범위)
    filtered_alarms = default_alarm_filter.filter_alarms_with_nursing_records(
        patient_id, date_str, raw_alarms
    )
    
    # 기술적 알람 필터링
    filtered_alarms = default_alarm_filter.filter_technical_alarms(raw_alarms)
    
    # 필터 설정 변경
    AlarmFilterConfig.enable_nursing_record_filter(False)  # 필터 비활성화
    AlarmFilterConfig.enable_technical_alarm_filter(True)  # 기술적 알람 필터 활성화
    default_alarm_filter.set_time_window(60)  # 60분 범위로 변경
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from data_structure import patient_data


class AlarmFilter:
    """알람 필터링 기능을 제공하는 클래스"""
    
    def __init__(self, time_window_minutes=30, technical_alarm_file="Filtered_AlarmLabelList.txt"):
        """
        Args:
            time_window_minutes: 간호기록 확인 시간 범위 (분 단위, 기본값: 30분)
            technical_alarm_file: 기술적 알람 목록 파일 경로
        """
        self.time_window_minutes = time_window_minutes
        self.technical_alarm_file = technical_alarm_file
        self.technical_alarms = set()  # 정규화된 기술적 알람 목록
        self.load_technical_alarms()
    
    def normalize_alarm_label(self, label):
        """
        알람 라벨을 비교를 위해 정규화
        - 소문자 변환
        - 앞뒤 공백 제거
        - 모든 공백 제거
        
        Args:
            label: 원본 알람 라벨
            
        Returns:
            정규화된 알람 라벨
        """
        if not label:
            return ""
        return label.lower().strip().replace(" ", "")
    
    def load_technical_alarms(self):
        """
        기술적 알람 목록을 파일에서 로드
        슬래시("/")로 구분된 여러 라벨들을 처리
        """
        self.technical_alarms.clear()
        
        # 파일 경로 확인
        file_path = Path(self.technical_alarm_file)
        if not file_path.is_absolute():
            # 상대 경로라면 현재 디렉토리 기준으로 해석
            current_dir = Path(__file__).parent.parent  # components 폴더의 부모 디렉토리
            file_path = current_dir / self.technical_alarm_file
        
        try:
            if not file_path.exists():
                print(f"경고: 기술적 알람 파일을 찾을 수 없습니다: {file_path}")
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line:  # 빈 줄 건너뛰기
                    continue
                
                # 슬래시로 구분된 여러 라벨 처리
                if "/" in line:
                    labels = [label.strip() for label in line.split("/")]
                else:
                    labels = [line]
                
                # 각 라벨을 정규화하여 저장
                for label in labels:
                    if label:  # 빈 문자열이 아닌 경우만
                        normalized_label = self.normalize_alarm_label(label)
                        if normalized_label:
                            self.technical_alarms.add(normalized_label)
            
            print(f"기술적 알람 목록 로드 완료: {len(self.technical_alarms)}개 라벨")
            print(f"예시: {list(self.technical_alarms)[:5]}...")
            
        except Exception as e:
            print(f"기술적 알람 목록 로드 오류: {e}")
    
    def is_technical_alarm(self, alarm_label):
        """
        주어진 알람 라벨이 기술적 알람인지 확인
        
        Args:
            alarm_label: 확인할 알람 라벨
            
        Returns:
            bool: 기술적 알람이면 True, 아니면 False
        """
        if not alarm_label:
            return False
        
        normalized_label = self.normalize_alarm_label(alarm_label)
        return normalized_label in self.technical_alarms
    
    def filter_technical_alarms(self, patient_id, date_str, alarms):
        """
        기술적 알람을 제거하여 필터링된 알람 목록 반환
        알람에 여러 라벨이 있는 경우, 모든 라벨이 기술적 알람일 때만 제거
        
        Args:
            patient_id: 환자 ID
            date_str: 날짜 문자열 (YYYY-MM-DD 형식)
            alarms: 원본 알람 목록
            
        Returns:
            기술적 알람이 제거된 필터링된 목록
        """
        if not self.technical_alarms:
            print("기술적 알람 목록이 비어있음 - 필터링하지 않음")
            return alarms
        
        print(f"\n=== 기술적 알람 필터링 시작 ===")
        print(f"로드된 기술적 알람 수: {len(self.technical_alarms)}")
        print(f"예시 정규화된 기술적 알람: {list(self.technical_alarms)[:10]}")
        
        filtered_alarms = []
        filtered_out_count = 0
        
        for alarm in alarms:
            # 알람 타임스탬프 생성
            alarm_time = alarm["time"]
            timestamp = f"{date_str} {alarm_time}"
            
            # 파형 데이터에서 AlarmLabel 가져오기
            waveform_data = patient_data.get_waveform_data(patient_id, timestamp)
            alarm_labels = []  # 모든 라벨들을 리스트로 수집
            
            print(f"\n--- 알람 분석: {alarm.get('color', 'Unknown')} ({alarm.get('time', 'Unknown')}) ---")
            
            if waveform_data and "AlarmLabel" in waveform_data:
                raw_alarm_label = waveform_data["AlarmLabel"]
                print(f"원본 AlarmLabel: {raw_alarm_label} (타입: {type(raw_alarm_label)})")
                
                # AlarmLabel 데이터 처리 - 다양한 형식 지원
                if isinstance(raw_alarm_label, (list, tuple)):
                    print(f"리스트/튜플 형식 처리: {len(raw_alarm_label)}개 요소")
                    # 리스트/튜플 형식: 각 요소를 개별로 처리
                    for i, item in enumerate(raw_alarm_label):
                        print(f"  [{i}]: '{item}' (타입: {type(item)})")
                        if item and str(item).strip():
                            label = str(item).strip()
                            if label and label != "None" and label != "[]":
                                alarm_labels.append(label)
                elif isinstance(raw_alarm_label, str):
                    print(f"문자열 형식 처리: '{raw_alarm_label}'")
                    # 문자열에 슬래시가 포함되어 있는지 확인
                    if " / " in raw_alarm_label:
                        # 슬래시로 구분된 여러 라벨 처리
                        labels = [label.strip() for label in raw_alarm_label.split(" / ")]
                        print(f"슬래시 구분 처리: {labels}")
                        for label in labels:
                            if label and label != "None" and label != "[]":
                                alarm_labels.append(label)
                    elif "/" in raw_alarm_label:
                        # 공백 없는 슬래시로 구분된 경우
                        labels = [label.strip() for label in raw_alarm_label.split("/")]
                        print(f"슬래시 구분 처리(공백없음): {labels}")
                        for label in labels:
                            if label and label != "None" and label != "[]":
                                alarm_labels.append(label)
                    elif raw_alarm_label.strip():
                        # 단일 문자엱 라벨
                        label = raw_alarm_label.strip()
                        if label and label != "None" and label != "[]":
                            alarm_labels.append(label)
                elif raw_alarm_label is not None:
                    print(f"기타 형식 처리: '{raw_alarm_label}' (타입: {type(raw_alarm_label)})")
                    # 기타 형식: 문자열로 변환 후 처리
                    converted = str(raw_alarm_label).strip()
                    if converted and converted != "[]" and converted != "None":
                        alarm_labels.append(converted)
            else:
                print("파형 데이터에 AlarmLabel 없음")
            
            print(f"추출된 라벨들: {alarm_labels}")
            
            # 알람 라벨 분석 및 필터링 결정
            if not alarm_labels:
                # AlarmLabel이 없는 경우 - 알람 유지
                filtered_alarms.append(alarm)
                print("결과: 알람 통과 (라벨 없음)")
            else:
                # 모든 라벨이 기술적 알람인지 확인
                technical_count = 0
                clinical_count = 0
                technical_labels = []
                clinical_labels = []
                
                print("라벨별 분석:")
                for label in alarm_labels:
                    normalized_label = self.normalize_alarm_label(label)
                    is_technical = self.is_technical_alarm(label)
                    print(f"  '{label}' → 정규화: '{normalized_label}' → 기술적: {is_technical}")
                    
                    if is_technical:
                        technical_count += 1
                        technical_labels.append(label)
                    else:
                        clinical_count += 1
                        clinical_labels.append(label)
                
                print(f"분석 결과: 기술적 {technical_count}개, 임상적 {clinical_count}개")
                
                # 필터링 결정: 모든 라벨이 기술적일 때만 제거
                if clinical_count == 0 and technical_count > 0:
                    # 모든 라벨이 기술적 알람인 경우 - 알람 제거
                    filtered_out_count += 1
                    print(f"결과: 기술적 알람 필터링됨 - 모든 라벨이 기술적 [{', '.join(technical_labels)}]")
                else:
                    # 하나라도 임상적 알람이 있는 경우 - 알람 유지
                    filtered_alarms.append(alarm)
                    if clinical_count > 0:
                        print(f"결과: 알람 통과 (임상적 라벨 포함) - 임상적[{', '.join(clinical_labels)}], 기술적[{', '.join(technical_labels)}]")
                    else:
                        # 이론적으로 도달할 수 없는 케이스지만 안전을 위해 추가
                        print(f"결과: 알람 통과 (예상치 못한 경우) - 라벨: [{', '.join(alarm_labels)}]")
        
        print(f"\n=== 기술적 알람 필터링 완료: 원본 {len(alarms)}개 → 통과 {len(filtered_alarms)}개, 제거 {filtered_out_count}개 ===")
        return filtered_alarms
    
    def filter_alarms_with_nursing_records(self, patient_id, date_str, alarms):
        """
        간호기록이 있는 알람만 필터링하여 반환
        
        Args:
            patient_id: 환자 ID
            date_str: 날짜 문자열 (YYYY-MM-DD 형식)
            alarms: 원본 알람 목록
            
        Returns:
            간호기록이 있는 알람들만 포함된 필터링된 목록
        """
        filtered_alarms = []
        filtered_out_count = 0
        
        for alarm in alarms:
            # 알람 타임스탬프 생성
            alarm_time = alarm["time"]
            timestamp = f"{date_str} {alarm_time}"
            
            # 해당 알람 시간에 간호기록이 있는지 확인
            if self.has_nursing_records_for_alarm(patient_id, timestamp):
                nursing_count = self.get_nursing_records_count_for_alarm(patient_id, timestamp)
                filtered_alarms.append(alarm)
                print(f"알람 통과: {alarm['color']} ({timestamp}) - 간호기록 {nursing_count}개")
            else:
                filtered_out_count += 1
                print(f"알람 필터링됨: {alarm['color']} ({timestamp}) - 간호기록 없음 (±{self.time_window_minutes}분 범위)")
        
        print(f"알람 필터링 완료: 원본 {len(alarms)}개 → 통과 {len(filtered_alarms)}개, 제거 {filtered_out_count}개")
        return filtered_alarms
    
    def has_nursing_records_for_alarm(self, patient_id, timestamp_str):
        """
        특정 알람 시간에 간호기록이 있는지 확인
        
        Args:
            patient_id: 환자 ID
            timestamp_str: 알람 타임스탬프 문자열 ("YYYY-MM-DD HH:MM:SS" 형식)
            
        Returns:
            bool: 간호기록이 있으면 True, 없으면 False
        """
        try:
            # 알람 타임스탬프 파싱
            alarm_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            
            # 시간 범위 정의 (±time_window_minutes)
            start_time = alarm_time - timedelta(minutes=self.time_window_minutes)
            end_time = alarm_time + timedelta(minutes=self.time_window_minutes)
            
            # 환자 데이터 로드
            patient_info = patient_data._load_patient_data(patient_id)
            if not patient_info:
                return False
            
            # 간호기록 확인
            nursing_records = patient_info.get("nursing_records", {})
            
            for record_time_str, records in nursing_records.items():
                try:
                    record_time = datetime.strptime(record_time_str, "%Y-%m-%d %H:%M:%S")
                    
                    # 시간 범위 내에 있는지 확인
                    if start_time <= record_time <= end_time:
                        # 기록이 있는지 확인 (배열 또는 단일 객체 모두 지원)
                        if isinstance(records, list) and len(records) > 0:
                            return True
                        elif isinstance(records, dict):
                            return True
                except ValueError:
                    # 타임스탬프 파싱 실패 시 건너뛰기
                    continue
            
            return False
            
        except Exception as e:
            print(f"간호기록 확인 오류 ({timestamp_str}): {e}")
            return False
    
    def get_nursing_records_count_for_alarm(self, patient_id, timestamp_str):
        """
        특정 알람 시간의 간호기록 개수 반환 (디버깅/정보 제공용)
        
        Args:
            patient_id: 환자 ID
            timestamp_str: 알람 타임스탬프 문자열
            
        Returns:
            int: 해당 시간 범위의 간호기록 개수
        """
        try:
            # 알람 타임스탬프 파싱
            alarm_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            
            # 시간 범위 정의
            start_time = alarm_time - timedelta(minutes=self.time_window_minutes)
            end_time = alarm_time + timedelta(minutes=self.time_window_minutes)
            
            # 환자 데이터 로드
            patient_info = patient_data._load_patient_data(patient_id)
            if not patient_info:
                return 0
            
            count = 0
            nursing_records = patient_info.get("nursing_records", {})
            
            for record_time_str, records in nursing_records.items():
                try:
                    record_time = datetime.strptime(record_time_str, "%Y-%m-%d %H:%M:%S")
                    
                    if start_time <= record_time <= end_time:
                        if isinstance(records, list):
                            count += len(records)
                        elif isinstance(records, dict):
                            count += 1
                except ValueError:
                    continue
            
            return count
            
        except Exception as e:
            print(f"간호기록 개수 조회 오류 ({timestamp_str}): {e}")
            return 0
    
    def set_time_window(self, minutes):
        """
        시간 범위 설정
        
        Args:
            minutes: 새로운 시간 범위 (분 단위)
        """
        self.time_window_minutes = minutes
        print(f"알람 필터 시간 범위 변경: ±{minutes}분")
    
    def get_time_window(self):
        """
        현재 시간 범위 반환
        
        Returns:
            int: 현재 시간 범위 (분 단위)
        """
        return self.time_window_minutes


# 전역 필터 인스턴스 (기본 30분 범위)
default_alarm_filter = AlarmFilter(time_window_minutes=30)


class AlarmFilterConfig:
    """알람 필터 설정을 관리하는 클래스"""
    
    # 간호기록 필터 활성화 여부
    ENABLE_NURSING_RECORD_FILTER = True
    
    # 기술적 알람 필터 활성화 여부
    ENABLE_TECHNICAL_ALARM_FILTER = False
    
    # 기본 시간 범위 (분 단위)
    DEFAULT_TIME_WINDOW_MINUTES = 30
    
    @classmethod
    def enable_nursing_record_filter(cls, enabled=True):
        """간호기록 필터 활성화/비활성화"""
        cls.ENABLE_NURSING_RECORD_FILTER = enabled
        print(f"간호기록 필터: {'활성화' if enabled else '비활성화'}")
    
    @classmethod
    def enable_technical_alarm_filter(cls, enabled=True):
        """기술적 알람 필터 활성화/비활성화"""
        cls.ENABLE_TECHNICAL_ALARM_FILTER = enabled
        print(f"기술적 알람 필터: {'활성화' if enabled else '비활성화'}")
    
    @classmethod
    def set_default_time_window(cls, minutes):
        """기본 시간 범위 설정"""
        cls.DEFAULT_TIME_WINDOW_MINUTES = minutes
        print(f"기본 시간 범위 설정: ±{minutes}분")
    
    @classmethod
    def is_nursing_record_filter_enabled(cls):
        """간호기록 필터 활성화 여부 반환"""
        return cls.ENABLE_NURSING_RECORD_FILTER
    
    @classmethod
    def is_technical_alarm_filter_enabled(cls):
        """기술적 알람 필터 활성화 여부 반환"""
        return cls.ENABLE_TECHNICAL_ALARM_FILTER
    
    @classmethod
    def get_enabled_filters_summary(cls):
        """활성화된 필터 요약 반환"""
        filters = []
        if cls.ENABLE_NURSING_RECORD_FILTER:
            filters.append(f"간호기록 필터(±{cls.DEFAULT_TIME_WINDOW_MINUTES}분)")
        if cls.ENABLE_TECHNICAL_ALARM_FILTER:
            filters.append("기술적 알람 필터")
        
        if not filters:
            return "모든 필터 비활성화"
        return f"활성화된 필터: {', '.join(filters)}"
