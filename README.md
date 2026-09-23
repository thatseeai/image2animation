# image2animation

정지 일러스트 한 장(`source/chuseok.webp`)을 레이어로 분리해, 한복 입은 로봇이 전을 집어 먹는 8초 루프 애니메이션 SVG로 만든다.

## 결과물

- `chuseok-robot.svg` — 이미지가 모두 내장된 애니메이션 SVG
- `index.html` — SVG를 화면 가운데에 띄우는 페이지
- `chusok-robot.html` — SVG까지 인라인한 단일 파일 버전

## 빌드

[uv](https://docs.astral.sh/uv/)가 필요하다.

```bash
./build.sh
```

1. `build/layers.py` — 원본에서 팔·전·눈 등을 잘라내고 빈 배경을 복원해 `build/layers/`에 저장
2. `build/build_svg.py` — 레이어를 조합하고 키프레임을 붙여 `chuseok-robot.svg` 생성
