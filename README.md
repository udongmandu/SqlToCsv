유지보수 중에 데이터 이관하는 작업에서 양이 얼마 안되는 줄 알고 그냥 SQL로 받아서 INSERT 문 돌릴 생각을 했는데, 
생각보다 그 양이 엄청나서 (450MB) 데이터를 insert 하는 데만 예상 소요시간이 24시간을 넘었다. (데스크 탑이 아니라 노트북인 이유도 있는 듯)

아무튼 그래서 이 프로그램을 제작했다.

toad 에서 export 하여서 나온 

INSERT INTO EMP (EMP_ID, EMP_NAME, HIRE_DATE) 
VALUES (1, 'KIM', TO_DATE('20250101','YYYYMMDD'));
INSERT INTO EMP (EMP_ID, EMP_NAME, HIRE_DATE) 
VALUES (1, 'KIM', TO_DATE('20250102','YYYYMMDD'));
...

위와 같은 sql 문 형태를 가지고 있어야 사용이 가능하다.

###사용방법
실행만 하면 됨 그냥.
<img width="574" height="379" alt="image" src="https://github.com/user-attachments/assets/db8df1ff-198f-459b-97a5-50bd43780a2e" />
해당 py 파일이 있는 곳 우클릭 -> 터미널에서 열기 -> python .\sql2csv.py 입력

<img width="1332" height="435" alt="image" src="https://github.com/user-attachments/assets/3a4233ce-7c60-4cfd-ba7b-9c28948f8368" />
테이블 명 입력 후 -> 파일 드래그 앤 드랍 (드래그 드랍 하면 해당 파일 절대경로가 입력됨)

<img width="970" height="353" alt="image" src="https://github.com/user-attachments/assets/3465f757-634e-464e-b23c-97c40be893ba" />
그러면 이렇게 왼료 되고, 바로 import 할 수 있도록 csv 파일이 완성 됨.

위 설명에서 있던 INSERT 양식 대로의 쿼리 문 이라면, 컬럼 명도 입력이 자동으로 되니, 양식을 꼭 지키고 사용하도록 하자.
