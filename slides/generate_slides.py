#!/usr/bin/env python3
"""Build the Korean 16:9 workshop deck. Dark theme, timing in notes."""

from __future__ import annotations

from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

# Widescreen 16:9
W = Inches(13.333)
H = Inches(7.5)

BG = RGBColor(0x0B, 0x12, 0x20)
CARD = RGBColor(0x15, 0x1F, 0x33)
CARD2 = RGBColor(0x1B, 0x2A, 0x44)
LINE = RGBColor(0x2A, 0x3B, 0x57)
CYAN = RGBColor(0x22, 0xD3, 0xEE)
AMBER = RGBColor(0xFB, 0xC0, 0x2D)
VIOLET = RGBColor(0xA7, 0x8B, 0xFA)
MINT = RGBColor(0x34, 0xD3, 0x99)
ROSE = RGBColor(0xF8, 0x71, 0x71)
WHITE = RGBColor(0xF8, 0xFA, 0xFC)
MUTED = RGBColor(0x94, 0xA3, 0xB8)
SOFT = RGBColor(0xCB, 0xD5, 0xE1)

FONT = "NanumBarunGothic"
FONT_TITLE = "NanumSquare"
OUT = Path(__file__).with_name("예지보전_에이전트_실습.pptx")


def _set_run(run, *, name, size, bold, color):
    run.font.name = name
    run.font.size = size
    run.font.bold = bold
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:latin", "a:ea", "a:cs"):
        node = rPr.find(qn(tag))
        if node is None:
            node = etree.SubElement(rPr, qn(tag))
        node.set("typeface", name)


def _fill(shape, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def _box(slide, l, t, w, h, color=CARD, line=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    try:
        shape.adjustments[0] = 0.08
    except Exception:
        pass
    _fill(shape, color)
    if line is not None:
        shape.line.color.rgb = line
        shape.line.width = Pt(1.25)
    return shape


def _textframe(shape, *, word_wrap=True):
    tf = shape.text_frame
    tf.word_wrap = word_wrap
    tf.clear()
    return tf


def _para(tf, text, *, size=18, bold=False, color=WHITE, align=PP_ALIGN.LEFT, space=6, font=FONT):
    if tf.text == "" and len(tf.paragraphs) == 1 and not tf.paragraphs[0].runs:
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space)
    run = p.add_run()
    run.text = text
    _set_run(run, name=font, size=Pt(size), bold=bold, color=color)
    return p


def _textbox(slide, l, t, w, h, text, **kwargs):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = _textframe(box)
    _para(tf, text, **kwargs)
    return box


def _notes(slide, text: str) -> None:
    notes = slide.notes_slide.notes_text_frame
    notes.text = text
    for p in notes.paragraphs:
        for run in p.runs:
            run.font.size = Pt(12)
            run.font.name = FONT


def _bg(slide) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = BG
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, Inches(0.08))
    _fill(bar, CYAN)
    foot = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, H - Inches(0.38), W, Inches(0.38))
    _fill(foot, RGBColor(0x08, 0x0D, 0x18))


def _footer(slide, page: int, total: int) -> None:
    _textbox(
        slide,
        Inches(0.45),
        H - Inches(0.34),
        Inches(9.5),
        Inches(0.28),
        "예지보전 에이전트 실습  ·  100분  ·  AI 엔지니어 진행",
        size=11,
        color=MUTED,
        space=0,
    )
    _textbox(
        slide,
        Inches(11.4),
        H - Inches(0.34),
        Inches(1.5),
        Inches(0.28),
        f"{page} / {total}",
        size=11,
        color=MUTED,
        align=PP_ALIGN.RIGHT,
        space=0,
    )


def _kicker(slide, text: str, color=CYAN) -> None:
    _textbox(slide, Inches(0.55), Inches(0.22), Inches(12), Inches(0.32), text, size=12, bold=True, color=color, space=0)


def _title(slide, text: str, top=0.48) -> None:
    _textbox(
        slide,
        Inches(0.55),
        Inches(top),
        Inches(12.2),
        Inches(0.7),
        text,
        size=28,
        bold=True,
        color=WHITE,
        font=FONT_TITLE,
        space=0,
    )


def _subtitle(slide, text: str, top=1.12) -> None:
    _textbox(slide, Inches(0.55), Inches(top), Inches(12.2), Inches(0.4), text, size=16, color=SOFT, space=0)


def _bullets(slide, items, l=0.55, t=1.7, w=12.2, h=5.0, size=18):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = _textframe(box)
    for i, item in enumerate(items):
        p = _para(tf, item, size=size, color=WHITE, space=10)
        p.level = 0
        if i == 0 and tf.paragraphs[0] is p:
            pass
    return box


def _card(slide, l, t, w, h, eyebrow, title, body, accent=CYAN):
    shape = _box(slide, Inches(l), Inches(t), Inches(w), Inches(h), CARD, LINE)
    stripe = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(0.09), Inches(h)
    )
    _fill(stripe, accent)
    _textbox(slide, Inches(l + 0.28), Inches(t + 0.14), Inches(w - 0.45), Inches(0.28), eyebrow, size=11, bold=True, color=accent, space=0)
    _textbox(slide, Inches(l + 0.28), Inches(t + 0.42), Inches(w - 0.45), Inches(0.4), title, size=18, bold=True, color=WHITE, font=FONT_TITLE, space=0)
    _textbox(slide, Inches(l + 0.28), Inches(t + 0.9), Inches(w - 0.45), Inches(h - 1.1), body, size=14, color=SOFT, space=0)
    return shape


def new_slide(prs) -> object:
    layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(layout)
    _bg(slide)
    return slide


def build() -> Path:
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    slides_meta: list[tuple[object, str]] = []

    def add(slide, notes: str):
        slides_meta.append((slide, notes))

    # 1 Title
    s = new_slide(prs)
    _kicker(s, "SENSOR AGENT TUTORIAL  ·  OPEN WEBUI × MCP × MARKDOWN SKILLS")
    _textbox(s, Inches(0.55), Inches(1.6), Inches(12), Inches(1.2), "예지보전, 챗봇으로 열기", size=40, bold=True, color=WHITE, font=FONT_TITLE, space=0)
    _textbox(
        s,
        Inches(0.55),
        Inches(2.85),
        Inches(11.5),
        Inches(0.8),
        "비개발자를 위한 100분 실습  ·  이론 50 + 실습 50\n진행: AI 엔지니어  ·  진동 전문 강의가 아닙니다",
        size=18,
        color=SOFT,
        space=4,
    )
    _card(s, 0.55, 4.3, 3.7, 1.85, "01 이론", "설계가 본게임", "조회 vs 변경, Skill.\n에이전트가 과한 때를 가른다.", CYAN)
    _card(s, 4.55, 4.3, 3.7, 1.85, "02 경로", "더미 공장 → SQLite", "MCP :8000  →  Open WebUI :8080\nMQTT 없음.", AMBER)
    _card(s, 8.55, 4.3, 3.7, 1.85, "03 한계", "학습용 더미", "실제 정비 절차가 아닙니다.\n무료 한도와 관리자 비용을 같이 봅니다.", ROSE)
    add(s, "0–1분. 제목만. ‘예지보전 전문 강의가 아님’을 첫 문장으로. 진행자는 AI 엔지니어다.")

    # 2 Map
    s = new_slide(prs)
    _kicker(s, "AGENDA")
    _title(s, "오늘 100분의 지도")
    rows = [
        ("0–8분", "이론 1", "예지보전 개요", "사후 / 예방 / 예지, 감지→판단→사람"),
        ("8–18분", "이론 2", "센서 이상 시나리오", "펌프 A · 팬 B, RMS, 수업용 임계값"),
        ("18–33분", "이론 3", "챗봇 + MCP + Skills", "LLM은 현장에 없다. 도구와 플레이북"),
        ("33–50분", "이론 4", "설계 원칙 (가장 깊게)", "에이전트 vs 과함, 더미 변경 vs 실설비"),
        ("50–100분", "실습", "uv + Open WebUI", "더미 공장 → SQLite → MCP → 챗봇"),
    ]
    y = 1.45
    for tmin, blk, title, body in rows:
        _box(s, Inches(0.55), Inches(y), Inches(12.2), Inches(0.88), CARD, LINE)
        _textbox(s, Inches(0.75), Inches(y + 0.22), Inches(1.7), Inches(0.45), tmin, size=14, bold=True, color=CYAN, space=0)
        _textbox(s, Inches(2.5), Inches(y + 0.12), Inches(3.2), Inches(0.32), blk, size=12, bold=True, color=AMBER, space=0)
        _textbox(s, Inches(2.5), Inches(y + 0.42), Inches(4.0), Inches(0.36), title, size=16, bold=True, color=WHITE, space=0)
        _textbox(s, Inches(7.0), Inches(y + 0.28), Inches(5.4), Inches(0.4), body, size=14, color=SOFT, space=0)
        y += 0.98
    add(s, "1–2분. 표를 손가락으로 가리키며 이론4가 가장 길다고 미리 선언. 실습은 uv.")

    # 3 Audience
    s = new_slide(prs)
    _kicker(s, "WHO THIS IS FOR")
    _title(s, "코드를 업으로 하지 않는 분을 위한 시간")
    _card(s, 0.55, 1.55, 6.0, 2.4, "맞는 분", "현장 언어는 안다", "보전·품질·설비·기획.\nLLM을 설비에 붙일 때 뭐가 깨지는지\n한 번에 보고 싶다.", MINT)
    _card(s, 6.8, 1.55, 6.0, 2.4, "아닌 분", "오늘 FFT는 없습니다", "결함주파수, ISO 20816, 엔벨로프는\n범위 밖. 질문이면 ‘다음에’로 받습니다.", ROSE)
    _card(s, 0.55, 4.15, 6.0, 2.15, "진행자", "AI 엔지니어", "진동 권위를 빌리지 않습니다.\n권위는 도구와 문장 설계에 둡니다.", CYAN)
    _card(s, 6.8, 4.15, 6.0, 2.15, "데이터", "전부 더미", "펌프가 정말 아픈 것이 아닙니다.\n10초마다 스파이크를 넣었습니다.", AMBER)
    add(s, "2분. 청중이 안도하게. ‘질문해도 진동 시험이 아니다’.")

    # 4 Goals
    s = new_slide(prs)
    _kicker(s, "LEARNING GOALS")
    _title(s, "100분 뒤, 이 네 문장을 말할 수 있으면 됩니다")
    goals = [
        ("1", "예지보전은 루프다", "AI가 설비를 고치는 마법이 아니라 감지 → 판단 → 사람 조치."),
        ("2", "챗봇은 센서가 아니다", "지금 값은 MCP 도구에서 온다. 모델 기억에서 오지 않는다."),
        ("3", "Skill은 Markdown이다", "파이썬 함수가 아니라 절차서다. 문장이 모델 행동을 고정한다."),
        ("4", "에이전트는 가려 쓴다", "한 숫자 조회는 과할 수 있다. 도구를 이을 때 맞다. 실설비 변경은 위험."),
    ]
    y = 1.5
    for num, title, body in goals:
        _box(s, Inches(0.55), Inches(y), Inches(12.2), Inches(1.15), CARD, LINE)
        circ = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.8), Inches(y + 0.28), Inches(0.55), Inches(0.55))
        _fill(circ, CYAN)
        _textbox(s, Inches(0.8), Inches(y + 0.36), Inches(0.55), Inches(0.4), num, size=16, bold=True, color=BG, align=PP_ALIGN.CENTER, space=0)
        _textbox(s, Inches(1.6), Inches(y + 0.18), Inches(10.8), Inches(0.4), title, size=18, bold=True, color=WHITE, space=0)
        _textbox(s, Inches(1.6), Inches(y + 0.58), Inches(10.8), Inches(0.42), body, size=15, color=SOFT, space=0)
        y += 1.25
    add(s, "2분. 네 문장을 천천히. 실습 채점 기준이 이 슬라이드다.")

    # 5 Section theory 1
    s = new_slide(prs)
    _kicker(s, "THEORY 1  ·  약 8분")
    _textbox(s, Inches(0.55), Inches(2.2), Inches(12), Inches(1.2), "예지보전 개요", size=44, bold=True, color=WHITE, font=FONT_TITLE, space=0)
    _textbox(s, Inches(0.55), Inches(3.5), Inches(11), Inches(1.0), "고장이 나기 전에, 상태 신호를 보고,\n사람이 개입할 시간을 버는 일.", size=22, color=CYAN, space=4)
    add(s, "이론1 시작(약 8분). 한 문장만 읽는다. 공식을 쓰지 않는다.")

    # 6 Three modes
    s = new_slide(prs)
    _kicker(s, "THEORY 1  ·  보전의 세 가지")
    _title(s, "언제 고치러 가는가")
    _card(s, 0.55, 1.55, 3.9, 4.7, "사후", "멈춘 뒤", "단순하다.\n이미 생산이 멈춘 뒤에 비용을 치른다.\n\n‘고장 = 신호’.", ROSE)
    _card(s, 4.7, 1.55, 3.9, 4.7, "예방", "달력으로", "주기 교환.\n과보전(아직 괜찮은 부품)과\n미보전(그 사이에 죽음)이 같이 생긴다.", AMBER)
    _card(s, 8.85, 1.55, 3.9, 4.7, "예지", "상태로", "신호가 나빠지면 간다.\n신호와 판단 규칙이 필요하다.\n오늘 수업의 위치.", CYAN)
    add(s, "3분. 세 칸만. ‘예지는 데이터가 있으면 공짜’가 아니라고 강조.")

    # 7 Why now
    s = new_slide(prs)
    _kicker(s, "THEORY 1  ·  왜 지금")
    _title(s, "센서는 싸졌고, 모델은 말을 하게 됐습니다")
    items = [
        "진동·전류·온도를 올리는 비용이 예전에 비해 낮아졌습니다.",
        "남는 것은 ‘값을 누구에게 어떤 말로 전달할 것인가’입니다.",
        "LLM은 그 말을 싸게 만들어 줍니다. 값을 만들어 주지는 않습니다.",
        "그래서 예지보전 + 챗봇은 매력적이고, 동시에 거짓말하기 쉽습니다.",
    ]
    _box(s, Inches(0.55), Inches(1.55), Inches(12.2), Inches(4.7), CARD, LINE)
    _textbox(s, Inches(0.9), Inches(1.8), Inches(11.5), Inches(4.2), "\n\n".join("▸  " + x for x in items), size=18, color=WHITE, space=8)
    add(s, "2분. ‘모델이 예지보전을 발명한 게 아니다’.")

    # 8 Loop
    s = new_slide(prs)
    _kicker(s, "THEORY 1  ·  루프")
    _title(s, "AI는 루프의 한가운데가 아닙니다")
    steps = [
        ("1 감지", "센서", "진동 RMS"),
        ("2 기록", "SQLite", "파일 DB"),
        ("3 조회", "MCP", "읽기 도구"),
        ("4 설명", "챗봇", "현장 언어"),
        ("5 조치", "더미/사람", "on·fail·replace"),
    ]
    x = 0.55
    for i, (title, mid, body) in enumerate(steps):
        _card(s, x, 1.7, 2.3, 3.4, f"STEP {i+1}", title, f"{mid}\n\n{body}", CYAN if i < 4 else AMBER)
        x += 2.5
    _textbox(s, Inches(0.55), Inches(5.35), Inches(12.2), Inches(0.7), "챗봇은 4번입니다. 5번의 실설비 기동/정지를 챗봇에게 주면 설계가 실패한 것입니다.", size=16, color=AMBER, space=0)
    add(s, "2분. 손가락으로 5칸. 이론1 종료.")

    # 9 Section theory 2
    s = new_slide(prs)
    _kicker(s, "THEORY 2  ·  약 10분")
    _textbox(s, Inches(0.55), Inches(2.2), Inches(12), Inches(1.2), "센서 이상 시나리오", size=40, bold=True, color=WHITE, font=FONT_TITLE, space=0)
    _textbox(s, Inches(0.55), Inches(3.5), Inches(11), Inches(1.0), "공식이 아니라 스토리입니다.\n주인공은 냉각수 펌프 A의 구동측 베어링.", size=20, color=CYAN, space=4)
    add(s, "이론2 시작(약 10분). FFT 질문 받으면 주차.")

    # 10 Vibration intuition
    s = new_slide(prs)
    _kicker(s, "THEORY 2  ·  진동")
    _title(s, "진동은 ‘건강 신호’입니다")
    _card(s, 0.55, 1.55, 6.0, 4.7, "오늘 쓰는 숫자", "RMS mm/s", "한 구간 동안 진동이 얼마나 큰지.\n크면 ‘덜덜거림이 커졌다’ 정도만.\n\n주파수 분해는 하지 않습니다.", CYAN)
    _card(s, 6.8, 1.55, 6.0, 4.7, "오늘 안 하는 것", "진단 공학", "결함주파수, 엔벨로프, 궤도.\nISO 등급으로 설비를 판정하지 않습니다.\n\n진행자도 그 시험을 보지 않습니다.", VIOLET)
    add(s, "3분. RMS를 ‘크기’로만. 잘난 척 금지.")

    # 11 Plant
    s = new_slide(prs)
    _kicker(s, "THEORY 2  ·  가상 플랜트")
    _title(s, "오늘은 설비 9대, 센서 10개의 가상 공장입니다")
    table = [
        ("펌프실", "pump-a-de / pump-a-nde", "주인공 · 주기적 스파이크"),
        ("압축기실", "compressor-c / blower-f", "유틸리티"),
        ("생산 라인", "conveyor · mixer · press", "배경 설비 4점"),
        ("공조·냉각탑", "fan-b-motor / cooling-tower-fan", "대조군"),
    ]
    y = 1.5
    _box(s, Inches(0.55), Inches(y), Inches(12.2), Inches(0.55), CARD2)
    for i, h in enumerate(["구역", "sensor_id", "역할"]):
        _textbox(s, Inches(0.7 + i * 4.0), Inches(y + 0.12), Inches(3.8), Inches(0.35), h, size=13, bold=True, color=CYAN, space=0)
    y = 2.15
    for row in table:
        _box(s, Inches(0.55), Inches(y), Inches(12.2), Inches(0.72), CARD, LINE)
        for i, cell in enumerate(row):
            _textbox(s, Inches(0.7 + i * 4.0), Inches(y + 0.18), Inches(3.8), Inches(0.45), cell, size=15, color=WHITE, space=0)
        y += 0.80
    _textbox(s, Inches(0.55), Inches(5.4), Inches(12.2), Inches(0.7), "지도는 http://localhost:8000 . 외울 ID는 pump-a-de 하나면 됩니다.", size=15, color=MUTED, space=0)
    add(s, "3분. pump-a-de만 기억하게. 10개는 지도로 보여 준다.")

    # 12 Anomaly language
    s = new_slide(prs)
    _kicker(s, "THEORY 2  ·  이상")
    _title(s, "현업 언어로 말하는 anomaly")
    _card(s, 0.55, 1.55, 4.0, 4.7, "normal", "지금은 평온", "수업용 기준 아래.\n‘안전 인증’이 아닙니다.", MINT)
    _card(s, 4.75, 1.55, 4.0, 4.7, "warning", "눈을 더 주자", "주의 구간.\n오늘 추세 도구는 없습니다.", AMBER)
    _card(s, 8.95, 1.55, 4.0, 4.7, "anomaly", "값이 튀었다", "RMS가 임계를 넘음.\n더미 스파이크일 수 있습니다.", ROSE)
    add(s, "2분. 단어 세 개만 합의.")

    # 13 Thresholds
    s = new_slide(prs)
    _kicker(s, "THEORY 2  ·  규칙")
    _title(s, "오늘은 딥러닝이 아니라 임계값입니다")
    _box(s, Inches(0.55), Inches(1.55), Inches(12.2), Inches(4.7), CARD, LINE)
    lines = [
        "warning  ≥  4.5 mm/s     anomaly  ≥  7.0 mm/s",
        "",
        "이 숫자는 수업용입니다. 현장 기준이 아닙니다.",
        "더미 센서는 약 10초마다 이상을 한 번 스파이크합니다.",
        "데모가 ‘아무 이상 없음’으로 죽지 않게 하려고요.",
        "탐지 지능을 모델에게 맡기지 않은 것은 의도입니다.",
    ]
    _textbox(s, Inches(0.9), Inches(1.85), Inches(11.5), Inches(4.1), "\n".join(lines), size=18, color=WHITE, space=6)
    add(s, "2분. 이론2 종료. ‘모델은 설명자’.")

    # 14 Section theory 3
    s = new_slide(prs)
    _kicker(s, "THEORY 3  ·  약 15분")
    _textbox(s, Inches(0.55), Inches(2.2), Inches(12), Inches(1.2), "챗봇 + MCP + Skills", size=40, bold=True, color=WHITE, font=FONT_TITLE, space=0)
    _textbox(s, Inches(0.55), Inches(3.5), Inches(11), Inches(1.0), "세 층이 같이 있어야 현장 숫자에 대해 말할 수 있습니다.", size=20, color=CYAN, space=4)
    add(s, "이론3 시작(약 15분). UI 클릭은 실습으로 미룬다.")

    # 15 Why chatbot
    s = new_slide(prs)
    _kicker(s, "THEORY 3  ·  왜 챗봇")
    _title(s, "대시보드만 있으면 번역이 남습니다")
    items = [
        "현장은 ‘RMS 8.2’보다 ‘펌프 A가 평소보다 덜덜 큰가’를 묻습니다.",
        "챗봇은 그 번역을 싸게 합니다. 교대·비전문가·원격에 유리합니다.",
        "다만 번역기가 원문을 모르면, 유창한 거짓말이 됩니다.",
        "그래서 연결(MCP)과 절차서(Skill)를 같이 둡니다.",
    ]
    _box(s, Inches(0.55), Inches(1.55), Inches(12.2), Inches(4.7), CARD, LINE)
    _textbox(s, Inches(0.9), Inches(1.85), Inches(11.5), Inches(4.2), "\n\n".join("▸  " + x for x in items), size=18, color=WHITE, space=8)
    add(s, "3분.")

    # 16 LLM limits
    s = new_slide(prs)
    _kicker(s, "THEORY 3  ·  LLM")
    _title(s, "모델 혼자서는 지금 펌프 값을 모릅니다")
    _card(s, 0.55, 1.55, 4.0, 4.7, "알고 있는 것", "일반 지식", "펌프가 뭔지, RMS가 크기라는 것.\n어제까지 읽은 텍스트.", MUTED)
    _card(s, 4.75, 1.55, 4.0, 4.7, "모르는 것", "이 플랜트", "지금 mm/s, 지금 시각,\n우리 센서 ID.", ROSE)
    _card(s, 8.95, 1.55, 4.0, 4.7, "잘하는 위험", "그럴듯함", "없는 값을 채워도\n문장은 자연스럽습니다.", AMBER)
    add(s, "4분. 핵심 한 장.")

    # 17 MCP
    s = new_slide(prs)
    _kicker(s, "THEORY 3  ·  MCP")
    _title(s, "MCP는 도구를 부르는 표준 계약입니다")
    _card(s, 0.55, 1.5, 6.0, 2.2, "무엇인가", "Model Context Protocol", "챗봇 호스트가 외부 도구를\n같은 방식으로 발견·호출하게.", CYAN)
    _card(s, 6.8, 1.5, 6.0, 2.2, "오늘 전송", "Streamable HTTP", "Open WebUI 네이티브 MCP는 SSE/stdio가 아닙니다.\nURL은 /mcp .", VIOLET)
    _card(s, 0.55, 3.9, 3.9, 2.4, "조회", "list / get", "assets · sensors · events", MINT)
    _card(s, 4.7, 3.9, 3.9, 2.4, "변경(더미)", "power / fail", "set_asset_power, fail_asset", AMBER)
    _card(s, 8.85, 3.9, 3.9, 2.4, "교체(더미)", "replace_asset", "고장난 인스턴스만.", ROSE)
    add(s, "5분. 조회와 변경을 갈라서. 실설비 변경이 아님을 한 번 더.")

    # 18 Skills
    s = new_slide(prs)
    _kicker(s, "THEORY 3  ·  SKILLS")
    _title(s, "Skill은 코드가 아니라 Markdown 절차서입니다")
    items = [
        "역할: 너는 누구이며 누구가 아닌가",
        "언제: 이 문서를 꺼내야 하는 질문",
        "절차: 도구를 어떤 순서로 부를지",
        "출력: 요약 / 근거 / 해석 / 권고 / 한계",
        "금지: 숫자 발명, 없는 ID, 실설비를 더미처럼",
    ]
    _box(s, Inches(0.55), Inches(1.5), Inches(7.3), Inches(4.8), CARD, LINE)
    _textbox(s, Inches(0.85), Inches(1.75), Inches(6.8), Inches(4.3), "\n\n".join("▸  " + x for x in items), size=17, color=WHITE, space=6)
    _card(s, 8.1, 1.5, 4.7, 4.8, "오늘 규칙", "Markdown only", "Open WebUI Python Function으로\n도구를 만들지 않습니다.\n\n운영팀이 파이썬을 안 고쳐도\n문장을 고치면 행동이 바뀝니다.", AMBER)
    add(s, "3분. Skill 파일을 나중에 화면으로 연다.")

    # 19 Path
    s = new_slide(prs)
    _kicker(s, "THEORY 3  ·  데이터 경로")
    _title(s, "한 장으로 외우는 오늘 아키텍처")
    boxes = [
        ("더미 공장", "생성기\n+ SQLite"),
        ("MCP", "조회·변경\n:8000/mcp"),
        ("지도", "top-down\n:8000/"),
        ("Open WebUI", "챗봇\n:8080"),
        ("LLM", "무료 티어\nOpenAI 호환"),
    ]
    x = 0.4
    for i, (title, body) in enumerate(boxes):
        _box(s, Inches(x), Inches(2.0), Inches(2.2), Inches(2.4), CARD, CYAN)
        _textbox(s, Inches(x + 0.1), Inches(2.2), Inches(2.0), Inches(0.7), title, size=16, bold=True, color=CYAN, align=PP_ALIGN.CENTER, space=0)
        _textbox(s, Inches(x + 0.1), Inches(2.95), Inches(2.0), Inches(1.2), body, size=14, color=SOFT, align=PP_ALIGN.CENTER, space=0)
        if i < len(boxes) - 1:
            _textbox(s, Inches(x + 2.05), Inches(2.85), Inches(0.4), Inches(0.4), "→", size=20, bold=True, color=AMBER, align=PP_ALIGN.CENTER, space=0)
        x += 2.55
    _textbox(s, Inches(0.55), Inches(4.7), Inches(12.2), Inches(1.3), "Skill Markdown은 Open WebUI 쪽에 붙습니다.\n센서 경로와 모델 경로가 분리되어 있어야, 모델이 죽어도 JSON으로 수업을 이어 갑니다.", size=16, color=SOFT, space=4)
    add(s, "3분. 이론3 종료. 화살표를 따라 손가락.")

    # 20 Section theory 4
    s = new_slide(prs)
    _kicker(s, "THEORY 4  ·  약 17분  ·  가장 깊게")
    _textbox(s, Inches(0.55), Inches(2.1), Inches(12), Inches(1.2), "Skill / MCP 설계 원칙", size=40, bold=True, color=WHITE, font=FONT_TITLE, space=0)
    _textbox(s, Inches(0.55), Inches(3.4), Inches(11.5), Inches(1.2), "도구를 많이 만드는 시간이 아닙니다.\n모델이 현장을 다치지 않게 하는 시간입니다.", size=20, color=AMBER, space=4)
    add(s, "이론4 시작. 절대 빨리 넘기지 말 것. 오늘 이론의 무게 중심.")

    # 21 Skill design
    s = new_slide(prs)
    _kicker(s, "THEORY 4  ·  SKILL")
    _title(s, "Skill 한 장은 이 네 칸이면 충분합니다")
    _card(s, 0.55, 1.55, 6.0, 2.35, "1 역할", "누구이며 누구가 아닌가", "현장 어시스턴트.\n진동 박사도, 정비 팀장도 아님.", CYAN)
    _card(s, 6.8, 1.55, 6.0, 2.35, "2 언제", "트리거 문장", "목록 / 최신 값 / 이상 / 정지할까.", VIOLET)
    _card(s, 0.55, 4.1, 6.0, 2.2, "3 절차", "도구 순서", "모르면 list → 한 점이면 get → 이상이면 anomalies.", AMBER)
    _card(s, 6.8, 4.1, 6.0, 2.2, "4 출력", "형식 고정", "요약 · 근거 · 해석 · 권고 · 한계.", MINT)
    add(s, "4분. ‘친절한 전문가’ 한 줄은 Skill이 아니다.")

    # 22 Tool design
    s = new_slide(prs)
    _kicker(s, "THEORY 4  ·  MCP TOOLS")
    _title(s, "도구는 작고, 이름이 동사+명사여야 합니다")
    _card(s, 0.55, 1.55, 6.0, 4.7, "조회", "list / get / events", "list_assets\nlist_sensors\nget_vibration_reading\nget_recent_events", MINT)
    _card(s, 6.8, 1.55, 6.0, 4.7, "변경 (더미만)", "request / power / fail / replace", "request_fix  → 화면 수락\nset_asset_power\nfail_asset\nreplace_asset\n\n에이전트는 공구를 잡지 않는다.", ROSE)
    add(s, "4분. 조회와 변경을 갈라 둔 것이 설계다. 실설비 버튼이 아님.")

    # 23 Grounding
    s = new_slide(prs)
    _kicker(s, "THEORY 4  ·  GROUNDING")
    _title(s, "숫자는 발명하지 않습니다")
    items = [
        "도구 호출 전에 RMS를 말하지 말 것.",
        "도구가 실패하면 ‘지금은 값을 못 읽었다’가 정답.",
        "그럴듯한 2.3 mm/s 는 오답입니다. 유창할수록 위험합니다.",
        "실습에서 챗봇 답과 curl /demo/sensors 를 대조합니다.",
        "둘이 전혀 다르면 — 그게 오늘 찾은 버그입니다.",
    ]
    _box(s, Inches(0.55), Inches(1.5), Inches(12.2), Inches(4.8), CARD, ROSE)
    _textbox(s, Inches(0.9), Inches(1.8), Inches(11.5), Inches(4.3), "\n\n".join("▸  " + x for x in items), size=18, color=WHITE, space=8)
    add(s, "3분. curl을 이론에서 예고.")

    # 24 Human
    s = new_slide(prs)
    _kicker(s, "THEORY 4  ·  AGENT VS OVERKILL")
    _title(s, "에이전트는 언제 쓰고, 언제 과한가")
    _card(s, 0.55, 1.55, 6.0, 4.7, "맞다", "도구를 잇는 일", "목록 → 값 → 고장 → 교체.\n지도만으로 안 끝나는 순서.\nSkill이 변경을 묶어 준다.", CYAN)
    _card(s, 6.8, 1.55, 6.0, 4.7, "과하다", "한 눈이면 되는 일", "지금 RMS만 보기.\n새로고침.\n실설비 기동/정지를 모델에게.\n그건 계산기지 비서가 아니다.", ROSE)
    add(s, "3분. 오늘 이론의 한 장. 더미 버튼은 체감용, 실설비는 과함.")

    # 25 Anti-patterns
    s = new_slide(prs)
    _kicker(s, "THEORY 4  ·  ANTI-PATTERNS")
    _title(s, "이 여섯 개는 실습에서 일부러 피합니다")
    antis = [
        ("만능 도구", "analyze_everything 하나"),
        ("비밀을 프롬프트에", "API 키를 Skill에 붙여 넣기"),
        ("Python Skill", "오늘 범위 밖 Function"),
        ("빈 Bearer", "MCP 인증 None이 정답"),
        ("모델에게 승인", "정비를 챗봇이 결재"),
        ("더미를 현장으로", "이 JSON으로 펌프 정지"),
    ]
    positions = [(0.55, 1.5), (4.7, 1.5), (8.85, 1.5), (0.55, 4.0), (4.7, 4.0), (8.85, 4.0)]
    for (title, body), (x, y) in zip(antis, positions):
        _card(s, x, y, 3.9, 2.25, "DON'T", title, body, ROSE)
    add(s, "3분. 시간이 밀리면 이 장만 빠르게. 우선순위는 앞 장이 더 높다.")

    # 26 Recap theory
    s = new_slide(prs)
    _kicker(s, "THEORY  ·  CHECKPOINT")
    _title(s, "이론 체크 — 실습 들어가기 전에")
    checks = [
        "예지보전 = 루프. AI는 조치자가 아니다.",
        "이상은 수업용 임계값이다. 진단서가 아니다.",
        "조회와 변경은 다른 층이다.",
        "한 숫자 보기에는 에이전트가 과할 수 있다.",
        "실설비 기동/정지를 모델에게 주면 위험하다.",
    ]
    _box(s, Inches(0.55), Inches(1.5), Inches(12.2), Inches(4.8), CARD, CYAN)
    _textbox(s, Inches(0.9), Inches(1.8), Inches(11.5), Inches(4.3), "\n\n".join("☐  " + x for x in checks), size=18, color=WHITE, space=8)
    add(s, "2분. 손 들어 질문. 이론 종료(50분). 5분 휴식 가능.")

    # 27 Lab section
    s = new_slide(prs)
    _kicker(s, "LAB  ·  50분")
    _textbox(s, Inches(0.55), Inches(2.2), Inches(12), Inches(1.2), "실습: uv와 Open WebUI", size=36, bold=True, color=WHITE, font=FONT_TITLE, space=0)
    _textbox(s, Inches(0.55), Inches(3.5), Inches(11.5), Inches(1.2), "코딩하지 않습니다. 스택을 켜고, 도구를 붙이고, 답을 대조합니다.", size=20, color=CYAN, space=4)
    add(s, "실습 시작. 수강생 가이드 docs/STUDENT.md 와 같은 순서.")

    # 28 Bring up
    s = new_slide(prs)
    _kicker(s, "LAB  ·  기동")
    _title(s, "uv로 공장과 챗봇")
    _box(s, Inches(0.55), Inches(1.5), Inches(12.2), Inches(3.3), RGBColor(0x0A, 0x16, 0x28), CYAN)
    cmd = "cd playground\ncopy .env.example .env     # 키만 붙이기\nuv run plant\nuv run open-webui"
    _textbox(s, Inches(0.85), Inches(1.7), Inches(11.6), Inches(2.9), cmd, size=16, color=MINT, space=6, font="NanumGothicCoding")
    _textbox(s, Inches(0.55), Inches(5.0), Inches(12.2), Inches(1.2), "성공: 공장 :8000 (지도+SQLite+MCP) · Open WebUI :8080\n설치·키·실행은 README. Docker 없음.", size=15, color=SOFT, space=4)
    add(s, "15분 블록의 기동. 디버깅에 10분을 쓰지 말 것.")

    # 29 Free LLM
    s = new_slide(prs)
    _kicker(s, "LAB  ·  LLM")
    _title(s, "무료 티어는 OpenAI 호환 URL만 맞으면 됩니다")
    _card(s, 0.55, 1.55, 4.0, 4.7, "Groq", "예시 기본값", "BASE https://api.groq.com/openai/v1\n모델은 .env.example 주석.", CYAN)
    _card(s, 4.75, 1.55, 4.0, 4.7, "그 외", "OpenRouter · Gemini", "형식이 OpenAI면 됩니다.\n키는 저장소에 없습니다.", VIOLET)
    _card(s, 8.95, 1.55, 4.0, 4.7, "키 없음", "JSON으로 진행", "공장+MCP는 키가 없어도 뜹니다.\n챗봇만 비어 있습니다.", AMBER)
    add(s, "5분. 키를 공유하지 말 것(한도).")

    # 30 Connect
    s = new_slide(prs)
    _kicker(s, "LAB  ·  연결")
    _title(s, "MCP는 Streamable HTTP, Skill은 붙여 넣기")
    items = [
        "Admin → Integrations → Add Server",
        "타입: MCP (Streamable HTTP)  ← OpenAPI 아님",
        "URL: http://127.0.0.1:8000/mcp",
        "Auth: None  (빈 Bearer 금지)",
        "채팅에서 MCP 토글 ON",
        "skills/vibration-pdm.md 전체를 Skills 또는 Prompts에 복사",
    ]
    _box(s, Inches(0.55), Inches(1.5), Inches(12.2), Inches(4.8), CARD, LINE)
    _textbox(s, Inches(0.9), Inches(1.75), Inches(11.5), Inches(4.3), "\n".join(f"{i+1}.  {x}" for i, x in enumerate(items)), size=18, color=WHITE, space=8)
    add(s, "15분. 화면을 천천히. 타입이 Streamable HTTP인지 확인.")

    # 31 Questions
    s = new_slide(prs)
    _kicker(s, "LAB  ·  질문 3개")
    _title(s, "직접 타이핑하세요")
    qs = [
        ("Q1", "지금 플랜트에 진동 센서가 뭐가 있나요? 도구로 확인한 뒤 ID와 상태만 표로."),
        ("Q2", "pump-a-de 최신 값. RMS와 시각을 지어내지 말고 도구 결과 그대로."),
        ("Q3", "최근 이벤트 인용. 이상만이 아니라 power/fail도 될 수 있음."),
    ]
    y = 1.5
    for tag, body in qs:
        _box(s, Inches(0.55), Inches(y), Inches(12.2), Inches(1.4), CARD, LINE)
        _textbox(s, Inches(0.8), Inches(y + 0.18), Inches(1.2), Inches(0.4), tag, size=16, bold=True, color=CYAN, space=0)
        _textbox(s, Inches(2.1), Inches(y + 0.35), Inches(10.3), Inches(0.8), body, size=16, color=WHITE, space=0)
        y += 1.55
    add(s, "10분. 채점 기준: 센서 10개 중 실명, 숫자 대조, 명령조 정지 없음.")

    # 32 Interpret
    s = new_slide(prs)
    _kicker(s, "LAB  ·  해석")
    _title(s, "답을 현장 언어로 다시 읽습니다")
    _card(s, 0.55, 1.55, 4.0, 4.7, "대조", "curl이 정답지", "GET /demo/sensors\nGET /demo/anomalies\n챗봇과 다르면 추측.", CYAN)
    _card(s, 4.75, 1.55, 4.0, 4.7, "상태", "세 단어만", "normal 평온\nwarning 추세 도구 없음\nanomaly 더미일 수 있음", AMBER)
    _card(s, 8.95, 1.55, 4.0, 4.7, "금지", "과잉 해석", "잔여수명 %\n내일 고장\n즉시 분해", ROSE)
    add(s, "5분.")

    # 33 Risks
    s = new_slide(prs)
    _kicker(s, "LAB  ·  RISKS")
    _title(s, "오늘 반드시 경험으로 말할 두 가지")
    _card(s, 0.55, 1.55, 6.0, 4.7, "1", "무료 티어 속도 제한", "429, 빈 답, ‘잠시 후’.\n창피하지 않습니다.\ncurl JSON으로 수업을 잇습니다.\n공유 키 하나는 더 빨리 죽습니다.", AMBER)
    _card(s, 6.8, 1.55, 6.0, 4.7, "2", "Open WebUI 관리자 부담", "MCP 추가는 관리자 메뉴.\n첫 가입자=관리자, 비밀번호 분실.\n워크숍은 WEBUI_AUTH=false.\n사내 개방망에 그대로 두지 말 것.", ROSE)
    add(s, "5분. 사내 도입 시 이 두 개가 본게임이라고 말하며 실습 닫기.")

    # 34 Close
    s = new_slide(prs)
    _kicker(s, "CLOSE  ·  Q&A")
    _title(s, "가져갈 세 문장")
    lines = [
        "1. 챗봇은 센서가 아니다. MCP 도구가 센서다.",
        "2. 도구가 있어도 모델은 거짓말한다. Markdown Skill이 절차를 고정한다.",
        "3. 한 숫자 조회는 과할 수 있다. 실설비 변경은 위험하다.",
    ]
    _box(s, Inches(0.55), Inches(1.45), Inches(12.2), Inches(2.6), CARD, CYAN)
    _textbox(s, Inches(0.85), Inches(1.7), Inches(11.6), Inches(2.2), "\n\n".join(lines), size=18, color=WHITE, space=6)
    _card(s, 0.55, 4.25, 4.0, 2.05, "슬라이드", "PPTX · PDF", "slides/", MINT)
    _card(s, 4.75, 4.25, 4.0, 2.05, "가이드", "진행자 · 수강생", "docs/", CYAN)
    _card(s, 8.95, 4.25, 4.0, 2.05, "스택", "uv", "playground/", AMBER)
    add(s, "5분. 한 문장 회고: ‘우리 팀 챗봇에 시키지 않을 도구는 ○○’. 보너스 데모로 끝내지 말 것. Q&A.")

    total = len(slides_meta)
    for i, (slide, notes) in enumerate(slides_meta, start=1):
        _footer(slide, i, total)
        _notes(slide, f"[슬라이드 {i}/{total}]\n{notes}")

    prs.save(str(OUT))
    print(f"wrote {OUT} ({total} slides)")
    return OUT


if __name__ == "__main__":
    build()
