# Type 2 Diabetes Bio Assistant

2형 당뇨 중심의 교육용 바이오 정보 프로그램입니다.

포함 기능:
- 유전자 입력 후 관련 질병 정보 조회
- FASTA / 서열 입력 후 GC content, 길이, ORF, codon 요약 분석
- 질병 입력 후 관련 약물 및 간단한 작용 기전 확인
- 유전자/서열 정보를 바탕으로 연구 가설 및 추가 실험 추천

## 실행

```bash
python app.py
diabetes-bio-assistant.exe
```

## 데이터 범위

- 현재는 2형 당뇨와 관련된 대표 유전자 및 인접 질환(MODY3, neonatal diabetes)을 소규모 패널로 넣었습니다.
- 로컬 JSON 지식베이스를 사용하므로 네트워크 없이도 시연 가능합니다.
- 공개 출처 링크는 앱 안에 표시됩니다.

## 주요 공개 출처

- NCBI Gene / GTR
- NIDDK
- MedlinePlus
- PubMed

## 주의

- 이 앱은 교육용/프로젝트용입니다.
- 실제 진단, 처방, 유전상담을 대신하지 않습니다.
