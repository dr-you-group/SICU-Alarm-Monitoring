
# import openpyxl
# import csv

# wb = openpyxl.load_workbook('data_processing/nursingrecord_marked.xlsx', data_only=True)
# ws = wb.active

# cols = [0, 2, 4, 6, 8, 9]  # A, C, E, G, I, J

# with open('output.tsv', 'w', newline='', encoding='utf-8') as f:
#     writer = csv.writer(f, delimiter='\t')
    
#     # 첫 줄(헤더) 무조건 추가
#     header = list(ws.iter_rows(min_row=1, max_row=1))[0]
#     writer.writerow([header[i].value for i in cols])
    
#     # 2번째 줄부터 검사
#     for row in ws.iter_rows(min_row=2):
#         if any(row[i].fill.start_color.index not in [None, '00000000', 'FFFFFFFF'] 
#                for i in cols):
#             writer.writerow([row[i].value for i in cols])

nre = open('data_processing/nursing_record_eng.csv', 'r', encoding='utf-8')
g = nre.readline().strip().split(',')

f = "10,신촌병원,11572411,165284917,2024-09-04,2024-09-05 00:00:00,2024-09-12 00:00:00,ICUC,ICUC 병동,131,131병동,ND000148,Risk for Injury(상해의 위험),NI000197,Seizure Management(발작 관리 ),NA000482,Seizure를 관찰함(Seizure를 관찰함),NT000373,Seizure 양상,Seizure를 관찰함 : Seizure 양상,Clonic,1,Day,,ICUC 병동,2024-09-09 12:50:00".split(',')
for gg, ff in zip(g, f):
    print(gg, ff)
