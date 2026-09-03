"""
데이터베이스 표.

프로토타입은 전체 상태를 localStorage 한 칸에 통째로 넣었습니다.
그러면 여러 명이 동시에 쓸 때 마지막 저장이 앞선 저장을 지웁니다.
그래서 여기서는 '보고 회차 1건 = 표의 한 줄'로 쪼갰습니다.
저장 요청도 그 한 줄만 건드립니다.

PostgreSQL 전용 자료형(JSONB 등)은 쓰지 않습니다.
로컬은 SQLite, 운영은 PostgreSQL 로 돌기 때문입니다.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _now() -> datetime:
    """저장은 UTC 로 합니다. 화면에 보일 때 한국 시간으로 바꿉니다."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------
# 사업
# ---------------------------------------------------------------------
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    agency: Mapped[str] = mapped_column(String(300), default="")
    start: Mapped[date] = mapped_column(Date, nullable=False)
    end: Mapped[date] = mapped_column(Date, nullable=False)

    # 금액은 원 단위 정수입니다. 억 환산은 화면에 표시할 때만 합니다.
    budget: Mapped[int] = mapped_column(BigInteger, default=0)

    cycle: Mapped[str] = mapped_column(String(10), default="주간")   # 주간/격주/월간
    folder_url: Mapped[str] = mapped_column(Text, default="")
    stage: Mapped[int] = mapped_column(Integer, default=0)           # 0~4

    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_by: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_by: Mapped[str] = mapped_column(String(60), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    categories: Mapped[list["ProjectCategory"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        order_by="ProjectCategory.sort_order",
    )
    tasks: Mapped[list["ProjectTask"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        order_by="ProjectTask.sort_order",
    )
    kpis: Mapped[list["ProjectKpi"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        order_by="ProjectKpi.sort_order",
    )
    stage_notes: Mapped[list["ProjectStageNote"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        order_by="ProjectStageNote.stage_index",
    )
    todos: Mapped[list["ProjectTodo"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        order_by="ProjectTodo.sort_order",
    )
    entries: Mapped[list["ReportEntry"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
        order_by="ReportEntry.entry_date",
    )


class ProjectCategory(Base):
    """비목과 배정액. 비목은 사업마다 다릅니다."""

    __tablename__ = "project_categories"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_category_per_project"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # 배정액(원). 0 은 '아직 안 넣음'이라는 뜻이고, 화면에서는 잔액 대신
    # '배정액 입력' 버튼이 나옵니다. 임의로 나눠 채우지 않습니다.
    budget_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped[Project] = relationship(back_populates="categories")


class ProjectTask(Base):
    """추진 과제. 진행률은 (완료 과제 ÷ 전체 과제) 입니다."""

    __tablename__ = "project_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # 이 과제가 어느 단계 것인지 (0 기획 · 1 착수 · 2 진행 · 3 마무리 · 4 완료).
    # 단계별로 몇 건이 끝났는지 보여 주려고 둡니다. 전체 진행률 계산에는
    # 쓰이지 않습니다 — 그것은 예나 지금이나 완료 과제 ÷ 전체 과제입니다.
    stage: Mapped[int] = mapped_column(Integer, default=2)

    project: Mapped[Project] = relationship(back_populates="tasks")


class ProjectKpi(Base):
    """성과지표. 현재값은 모든 회차 실적의 합계입니다."""

    __tablename__ = "project_kpis"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_kpi_per_project"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="건")
    # 소수점을 허용합니다. '만족도 4.5점' 같은 목표가 실제로 있습니다.
    # (프로토타입도 Number() 로 받아 소수점을 허용했습니다)
    target: Mapped[float] = mapped_column(Float, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped[Project] = relationship(back_populates="kpis")


class ProjectStageNote(Base):
    """진행 단계(기획·착수·진행·마무리·완료)별 내용. 사업마다 5줄입니다."""

    __tablename__ = "project_stage_notes"
    __table_args__ = (
        UniqueConstraint("project_id", "stage_index", name="uq_stage_note_per_project"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    stage_index: Mapped[int] = mapped_column(Integer, nullable=False)   # 0~4
    note: Mapped[str] = mapped_column(Text, default="")

    project: Mapped[Project] = relationship(back_populates="stage_notes")


class ProjectTodo(Base):
    __tablename__ = "project_todos"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    due: Mapped[date | None] = mapped_column(Date, nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    created_by: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project] = relationship(back_populates="todos")


# ---------------------------------------------------------------------
# 보고 회차 — 이 서비스의 핵심
# ---------------------------------------------------------------------
class ReportEntry(Base):
    """
    보고 회차 1건.

    (project_id, period_key) 가 유일합니다. 같은 회차를 두 번 만들 수 없고,
    저장은 이 한 줄만 갱신하므로 다른 사업·다른 회차의 입력을 건드리지 않습니다.

    period_key 는 프로토타입과 같은 모양입니다 (W2026-08-24 / B12 / M2026-08).
    격주 사업은 키가 '사업 시작일 기준 몇 번째'인지를 담고 있어서,
    사업 시작일을 바꾸면 기존 회차의 키를 다시 계산해 줘야 합니다.
    """

    __tablename__ = "report_entries"
    __table_args__ = (
        UniqueConstraint("project_id", "period_key", name="uq_entry_per_period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)   # 그 회차의 시작일

    act: Mapped[str] = mapped_column(Text, default="")               # 주요 활동
    issue: Mapped[str] = mapped_column(Text, default="")             # 확인사항
    plan: Mapped[str] = mapped_column(Text, default="")              # 조치 계획
    # 확인사항이 해결됐는지. 미해결 확인사항이 하나라도 있으면 상태가 '점검 필요'가 됩니다.
    issue_done: Mapped[bool] = mapped_column(Boolean, default=False)

    # 누가 언제 입력했는지.
    # 계정을 두지 않기로 해서 입력자는 입력 폼에서 직접 적는 값입니다.
    # 나중에 사내 계정을 붙이면 이 칸이 계정 이름으로 자동으로 채워집니다.
    entered_by: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_by: Mapped[str] = mapped_column(String(60), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    # 동시 저장 충돌을 잡기 위한 번호. 저장할 때마다 1씩 올라갑니다.
    # 화면이 들고 있던 번호와 다르면 그 사이에 다른 사람이 저장한 것입니다.
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    project: Mapped[Project] = relationship(back_populates="entries")
    spends: Mapped[list["EntrySpend"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan",
        order_by="EntrySpend.sort_order",
    )
    kpi_values: Mapped[list["EntryKpiValue"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan",
    )
    # 이력은 회차를 지워도 남겨야 합니다.
    # cascade="all, delete-orphan" 을 주면 SQLAlchemy 가 회차를 지울 때 이력까지
    # 함께 지워 버려서, 데이터베이스에 걸어 둔 ON DELETE SET NULL 이 소용없어집니다.
    # passive_deletes=True 로 두어 데이터베이스가 정한 대로(entry_id 만 비우기) 맡깁니다.
    revisions: Mapped[list["EntryRevision"]] = relationship(
        back_populates="entry",
        order_by="EntryRevision.revision_no",
        passive_deletes=True,
    )


class EntrySpend(Base):
    """
    한 회차의 집행 내역. 한 회차에 여러 건이 들어갑니다.

    비목은 이름을 그대로 적습니다(외래키가 아닙니다).
    사업 등록 화면에서 비목을 지워도 이미 입력한 집행 내역이 사라지면 안 되고,
    프로토타입도 '비목 목록에 없는 비목'을 화면에 함께 보여 주기 때문입니다.
    """

    __tablename__ = "entry_spends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("report_entries.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)   # 원 단위
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    entry: Mapped[ReportEntry] = relationship(back_populates="spends")


class EntryKpiValue(Base):
    """한 회차의 성과지표 실적. 지표 이름으로 적습니다(집행 내역과 같은 이유)."""

    __tablename__ = "entry_kpi_values"
    __table_args__ = (
        UniqueConstraint("entry_id", "kpi_name", name="uq_kpi_value_per_entry"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("report_entries.id", ondelete="CASCADE"), index=True
    )
    kpi_name: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[float] = mapped_column(Float, default=0)   # 목표와 같은 이유로 소수점 허용

    entry: Mapped[ReportEntry] = relationship(back_populates="kpi_values")


class EntryRevision(Base):
    """
    회차가 바뀌거나 지워질 때 그 전 내용을 여기에 남깁니다.

    '누가 언제 무엇을 바꿨는지' 확인하려면 이전 내용이 남아 있어야 합니다.
    프로토타입은 덮어쓰기만 해서 이전 내용을 볼 방법이 없었습니다.

    회차를 삭제해도 이 기록은 남습니다(entry_id 만 비워집니다).
    삭제야말로 '누가 언제 지웠는지'가 가장 중요한 경우인데, 회차와 함께
    지워지면 확인할 방법이 없어집니다. 그래서 사업 id·회차 키를 따로 담아
    회차가 없어져도 어느 회차의 기록인지 알 수 있게 했습니다.
    """

    __tablename__ = "entry_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("report_entries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 회차가 지워져도 어느 사업 · 어느 회차였는지 남습니다
    project_id: Mapped[str] = mapped_column(String(40), index=True)
    period_key: Mapped[str] = mapped_column(String(20))

    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    # update = 고침 / delete = 지움
    action: Mapped[str] = mapped_column(String(10), default="update")
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)   # 바뀌기 전 내용
    changed_by: Mapped[str] = mapped_column(String(60), default="")
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    entry: Mapped[ReportEntry | None] = relationship(back_populates="revisions")


# ---------------------------------------------------------------------
# 공고
# ---------------------------------------------------------------------
class Announcement(Base):
    """
    대외 공고.

    NTIS 통합공고는 전 부처라 건수가 많습니다. 수집 단계에서는 키워드로 버리지 않고
    전량 저장하고, 걸러내기는 화면에서만 합니다.
    """

    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    ministry: Mapped[str] = mapped_column(String(120), default="", index=True)  # 카드 상단 배지
    agency: Mapped[str] = mapped_column(String(200), default="")                # 전문기관
    no: Mapped[str] = mapped_column(String(120), default="")                    # 공고번호
    title: Mapped[str] = mapped_column(Text, nullable=False)
    program: Mapped[str] = mapped_column(String(300), default="")               # 사업명

    posted: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    open_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 마감일은 목록에 없는 경우가 많습니다. 비어 있으면 화면에 '기간 미확인'으로 나옵니다.
    due: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    due_time: Mapped[str] = mapped_column(String(5), default="")                # "18:00"

    amount: Mapped[int] = mapped_column(BigInteger, default=0)                  # 원 단위
    contact: Mapped[str] = mapped_column(String(200), default="")
    url: Mapped[str] = mapped_column(Text, default="", index=True)

    # 어디서 왔는지 (khidi-board, kohi-board, khis-rss, ntis-rss, manual …)
    # 'manual' 은 사람이 직접 등록·수정한 것이라 수집 결과로 덮어쓰지 않습니다.
    source: Mapped[str] = mapped_column(String(30), default="manual", index=True)

    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class AnnouncementFavorite(Base):
    """관심(★) 등록한 공고. 계정이 없으므로 팀 전체가 함께 봅니다."""

    __tablename__ = "announcement_favorites"

    announcement_id: Mapped[str] = mapped_column(
        ForeignKey("announcements.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ---------------------------------------------------------------------
# 그 밖에
# ---------------------------------------------------------------------
class AppSetting(Base):
    """
    화면 설정 한 칸씩. 지금 쓰는 것:
      ann_filter  — 공고 관심 조건 {include, ministries, amount}
      manual_url  — 사업 매뉴얼 문서 주소
    """

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(60), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class CollectorRun(Base):
    """
    공고 수집을 언제 돌렸고 몇 건 걷혔는지.

    수집이 조용히 멈춰 있는데 아무도 모르는 상황이 제일 위험합니다.
    화면 위에 '마지막 수집: 8/27 06:00 · 57건' 을 보여 주려고 남깁니다.
    """

    __tablename__ = "collector_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ok: Mapped[bool] = mapped_column(Boolean, default=False)
    trigger: Mapped[str] = mapped_column(String(20), default="schedule")   # schedule / manual

    added: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    total_seen: Mapped[int] = mapped_column(Integer, default=0)

    # 소스별 결과와 경고(인재원 응답 잘림 등)를 그대로 담습니다.
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
