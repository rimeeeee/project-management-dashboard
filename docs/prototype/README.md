# 프로토타입 원본

`사업관리_대시보드_4.html` 은 이 서비스의 **요구사항 명세서**입니다.
화면 구성·계산 규칙·용어가 실무 검토를 여러 차례 거쳐 확정된 상태이고,
코드 안 한글 주석에 "왜 그렇게 정했는지"가 적혀 있습니다.

`공고수집_v9.py` 는 공고 수집 스크립트 원본입니다. 실제 운영 데이터로
약 57건 검증을 마친 것이라, 파싱 로직은 그대로 씁니다.

## 화면 비교하기

계산 규칙은 `scripts/verify/run.py` 가 이 원본을 실행해 자동으로 대조합니다.

    .venv/bin/python scripts/verify/run.py

화면을 눈으로 나란히 비교하고 싶으면, 이 파일을 개발 중에만 잠깐
`frontend/public/` 로 복사해서 http://localhost:5173/prototype.html 로 엽니다.
비교가 끝나면 지워 주세요. `public/` 에 있는 파일은 빌드에 그대로 포함되어
배포되기 때문입니다 (192KB, 로그인 없이 누구나 볼 수 있게 됩니다).

    cp docs/prototype/사업관리_대시보드_4.html frontend/public/prototype.html
    # ... 비교 후 ...
    rm frontend/public/prototype.html

프로토타입은 브라우저 localStorage 를 쓰므로 이 서비스의 데이터에는
영향을 주지 않습니다. (화면 테마 설정만 같은 값을 공유합니다.)
