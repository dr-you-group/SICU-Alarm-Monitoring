import json
import os


for i in [i for  i in os.listdir('DATA_origin') if i.endswith('.json')]:

    # 파일 읽기
    with open(f'DATA_origin/{i}', 'r', encoding='utf-8') as f:
        origin_data = json.load(f)

    with open(f'DATA/{i}', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # nursing_records 필드 덮어쓰기
    data['nursing_records'] = origin_data['nursing_records']

    # 수정된 내용을 DATA/123.json에 저장
    with open(f'DATA/{i}', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("완료: nursing_records 필드가 성공적으로 덮어쓰기 되었습니다.")