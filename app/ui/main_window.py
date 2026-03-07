from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.controller import AgentController
from app.ui.i18n import TRANSLATIONS, get_language_names, translate


class SectionFrame(QFrame):
    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sectionFrame")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(10)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        self.layout.addWidget(self.title_label)


class AgentSidebarWindow(QMainWindow):
    def __init__(self, controller: AgentController) -> None:
        super().__init__()
        self.controller = controller
        self.current_language = "zh-CN"
        self.example_buttons: list[QPushButton] = []

        self.setMinimumSize(1280, 860)
        self.resize(1480, 960)

        self._build_ui()
        self._apply_styles()
        self._dock_to_center()
        self._apply_translations()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_dashboard)
        self.refresh_timer.start(1500)

        self.refresh_dashboard()

    def _t(self, *keys: str, default: str = "") -> Any:
        return translate(self.current_language, *keys, default=default)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        self.header_frame = QFrame()
        self.header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(18, 16, 18, 16)
        header_layout.setSpacing(12)

        header_title_layout = QVBoxLayout()
        header_title_layout.setSpacing(4)
        self.app_title_label = QLabel("")
        self.app_title_label.setObjectName("appTitle")
        self.app_subtitle_label = QLabel("")
        self.app_subtitle_label.setObjectName("appSubtitle")
        self.app_subtitle_label.setWordWrap(True)
        header_title_layout.addWidget(self.app_title_label)
        header_title_layout.addWidget(self.app_subtitle_label)
        header_layout.addLayout(header_title_layout, 1)

        header_right_layout = QHBoxLayout()
        header_right_layout.setSpacing(8)
        self.language_label = QLabel("")
        self.language_combo = QComboBox()
        self.language_codes: list[str] = list(TRANSLATIONS.keys())
        language_names = get_language_names()
        for code in self.language_codes:
            self.language_combo.addItem(language_names.get(code, code), code)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)

        self.start_button = QPushButton()
        self.start_button.clicked.connect(self.start_daemon)
        self.stop_button = QPushButton()
        self.stop_button.clicked.connect(self.stop_daemon)
        self.pause_button = QPushButton()
        self.pause_button.clicked.connect(self.pause_auto_goals)
        self.resume_button = QPushButton()
        self.resume_button.clicked.connect(self.resume_auto_goals)
        self.refresh_button = QPushButton()
        self.refresh_button.clicked.connect(self.refresh_dashboard)

        header_right_layout.addWidget(self.language_label)
        header_right_layout.addWidget(self.language_combo)
        header_right_layout.addWidget(self.start_button)
        header_right_layout.addWidget(self.stop_button)
        header_right_layout.addWidget(self.pause_button)
        header_right_layout.addWidget(self.resume_button)
        header_right_layout.addWidget(self.refresh_button)
        header_layout.addLayout(header_right_layout)

        root_layout.addWidget(self.header_frame)

        self.main_splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(self.main_splitter, 1)

        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setFrameShape(QFrame.NoFrame)
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 6, 0)
        self.left_layout.setSpacing(12)
        self.left_scroll.setWidget(self.left_container)
        self.main_splitter.addWidget(self.left_scroll)

        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setFrameShape(QFrame.NoFrame)
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(6, 0, 0, 0)
        self.right_layout.setSpacing(12)
        self.right_scroll.setWidget(self.right_container)
        self.main_splitter.addWidget(self.right_scroll)
        self.main_splitter.setSizes([760, 700])

        self.status_frame = SectionFrame()
        self.status_summary_label = QLabel("")
        self.status_summary_label.setWordWrap(True)
        self.status_summary_label.setObjectName("statusHero")
        self.status_details_label = QLabel("")
        self.status_details_label.setWordWrap(True)
        self.status_frame.layout.addWidget(self.status_summary_label)
        self.status_frame.layout.addWidget(self.status_details_label)
        self.left_layout.addWidget(self.status_frame)

        self.command_frame = SectionFrame()
        self.input_title_label = QLabel("")
        self.input_title_label.setObjectName("subHeadline")
        self.input_title_label.setWordWrap(True)

        self.command_input = QTextEdit()
        self.command_input.setAcceptRichText(False)
        self.command_input.setMinimumHeight(140)
        self.command_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        command_buttons = QHBoxLayout()
        command_buttons.setSpacing(8)
        self.send_button = QPushButton()
        self.send_button.clicked.connect(self.submit_goal)
        self.queue_button = QPushButton()
        self.queue_button.clicked.connect(self.submit_goal)
        self.clear_button = QPushButton()
        self.clear_button.clicked.connect(self.command_input.clear)
        command_buttons.addWidget(self.send_button)
        command_buttons.addWidget(self.queue_button)
        command_buttons.addWidget(self.clear_button)
        command_buttons.addStretch(1)

        self.command_frame.layout.addWidget(self.input_title_label)
        self.command_frame.layout.addWidget(self.command_input)
        self.command_frame.layout.addLayout(command_buttons)
        self.left_layout.addWidget(self.command_frame)

        self.quick_start_frame = SectionFrame()
        self.how_to_use_label = QLabel("")
        self.how_to_use_label.setWordWrap(True)
        self.desktop_hint_label = QLabel("")
        self.desktop_hint_label.setWordWrap(True)
        self.desktop_hint_label.setObjectName("hintLabel")

        self.examples_title_label = QLabel("")
        self.examples_title_label.setObjectName("miniTitle")
        self.examples_grid = QGridLayout()
        self.examples_grid.setHorizontalSpacing(8)
        self.examples_grid.setVerticalSpacing(8)

        for index in range(4):
            button = QPushButton("")
            button.setObjectName("exampleButton")
            button.setMinimumHeight(56)
            button.clicked.connect(lambda _checked=False, i=index: self._use_example(i))
            self.example_buttons.append(button)
            self.examples_grid.addWidget(button, index // 2, index % 2)

        self.quick_start_frame.layout.addWidget(self.how_to_use_label)
        self.quick_start_frame.layout.addWidget(self.desktop_hint_label)
        self.quick_start_frame.layout.addWidget(self.examples_title_label)
        self.quick_start_frame.layout.addLayout(self.examples_grid)
        self.left_layout.addWidget(self.quick_start_frame)

        self.current_goal_frame = SectionFrame()
        self.current_goal_label = QLabel("")
        self.current_goal_label.setWordWrap(True)
        self.current_goal_frame.layout.addWidget(self.current_goal_label)
        self.left_layout.addWidget(self.current_goal_frame)

        self.reasoning_frame = SectionFrame()
        self.reasoning_text = QPlainTextEdit()
        self.reasoning_text.setReadOnly(True)
        self.reasoning_text.setMinimumHeight(140)
        self.reasoning_frame.layout.addWidget(self.reasoning_text)
        self.left_layout.addWidget(self.reasoning_frame)

        self.plan_frame = SectionFrame()
        self.plan_list = QListWidget()
        self.plan_frame.layout.addWidget(self.plan_list)
        self.left_layout.addWidget(self.plan_frame)

        self.approvals_frame = SectionFrame()
        self.approvals_list = QListWidget()
        approval_buttons = QHBoxLayout()
        approval_buttons.setSpacing(8)
        self.approve_button = QPushButton()
        self.approve_button.clicked.connect(self.approve_selected_approval)
        self.reject_button = QPushButton()
        self.reject_button.clicked.connect(self.reject_selected_approval)
        approval_buttons.addWidget(self.approve_button)
        approval_buttons.addWidget(self.reject_button)
        approval_buttons.addStretch(1)
        self.approvals_frame.layout.addWidget(self.approvals_list)
        self.approvals_frame.layout.addLayout(approval_buttons)
        self.left_layout.addWidget(self.approvals_frame)
        self.left_layout.addStretch(1)

        self.allowed_roots_frame = SectionFrame()
        self.allowed_roots_text = QPlainTextEdit()
        self.allowed_roots_text.setReadOnly(True)
        self.allowed_roots_text.setMinimumHeight(110)
        self.allowed_roots_frame.layout.addWidget(self.allowed_roots_text)
        self.right_layout.addWidget(self.allowed_roots_frame)

        self.capabilities_frame = SectionFrame()
        self.capabilities_text = QPlainTextEdit()
        self.capabilities_text.setReadOnly(True)
        self.capabilities_text.setMinimumHeight(120)
        self.capabilities_frame.layout.addWidget(self.capabilities_text)
        self.right_layout.addWidget(self.capabilities_frame)

        self.self_improvement_frame = SectionFrame()
        self.self_improvement_text = QPlainTextEdit()
        self.self_improvement_text.setReadOnly(True)
        self.self_improvement_text.setMinimumHeight(120)
        self.self_improvement_frame.layout.addWidget(self.self_improvement_text)
        self.right_layout.addWidget(self.self_improvement_frame)

        self.recent_goals_frame = SectionFrame()
        self.goals_list = QListWidget()
        self.recent_goals_frame.layout.addWidget(self.goals_list)
        self.right_layout.addWidget(self.recent_goals_frame)

        self.recent_tools_frame = SectionFrame()
        self.tools_list = QListWidget()
        self.recent_tools_frame.layout.addWidget(self.tools_list)
        self.right_layout.addWidget(self.recent_tools_frame)

        self.recent_failures_frame = SectionFrame()
        self.failures_list = QListWidget()
        self.recent_failures_frame.layout.addWidget(self.failures_list)
        self.right_layout.addWidget(self.recent_failures_frame)

        self.recent_events_frame = SectionFrame()
        self.events_list = QListWidget()
        self.recent_events_frame.layout.addWidget(self.events_list)
        self.right_layout.addWidget(self.recent_events_frame)

        self.recent_logs_frame = SectionFrame()
        self.logs_list = QListWidget()
        self.recent_logs_frame.layout.addWidget(self.logs_list)
        self.right_layout.addWidget(self.recent_logs_frame)

        self.right_layout.addStretch(1)

    def _apply_translations(self) -> None:
        self.setWindowTitle(str(self._t("meta", "app_title", default="Windows Agent")))

        self.app_title_label.setText(str(self._t("meta", "app_title", default="Windows Agent")))
        self.app_subtitle_label.setText(
            str(self._t("labels", "how_to_use_body", default=""))
        )

        self.language_label.setText(str(self._t("meta", "language_label", default="Language")))
        combo_index = self.language_codes.index(self.current_language)
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(combo_index)
        self.language_combo.blockSignals(False)

        self.status_frame.title_label.setText(str(self._t("sections", "status", default="Status")))
        self.command_frame.title_label.setText(
            str(self._t("sections", "command_center", default="Command Center"))
        )
        self.quick_start_frame.title_label.setText(
            str(self._t("sections", "quick_start", default="Quick Start"))
        )
        self.current_goal_frame.title_label.setText(
            str(self._t("sections", "current_goal", default="Current Goal"))
        )
        self.reasoning_frame.title_label.setText(
            str(self._t("sections", "reasoning", default="Reasoning"))
        )
        self.plan_frame.title_label.setText(
            str(self._t("sections", "plan_steps", default="Plan Steps"))
        )
        self.approvals_frame.title_label.setText(
            str(self._t("sections", "approvals", default="Pending Approvals"))
        )
        self.allowed_roots_frame.title_label.setText(
            str(self._t("labels", "allowed_roots_title", default="Allowed roots"))
        )
        self.capabilities_frame.title_label.setText(
            str(self._t("sections", "capabilities", default="Capabilities"))
        )
        self.self_improvement_frame.title_label.setText(
            str(self._t("sections", "self_improvement", default="Self Improvement"))
        )
        self.recent_goals_frame.title_label.setText(
            str(self._t("sections", "recent_goals", default="Recent Goals"))
        )
        self.recent_tools_frame.title_label.setText(
            str(self._t("sections", "recent_tools", default="Recent Tools"))
        )
        self.recent_failures_frame.title_label.setText(
            str(self._t("sections", "recent_failures", default="Recent Failures"))
        )
        self.recent_events_frame.title_label.setText(
            str(self._t("sections", "recent_events", default="Recent Events"))
        )
        self.recent_logs_frame.title_label.setText(
            str(self._t("sections", "recent_logs", default="Recent Logs"))
        )

        self.input_title_label.setText(
            str(self._t("labels", "input_title", default="Describe your task"))
        )
        self.command_input.setPlaceholderText(
            str(self._t("labels", "input_hint", default="Describe your task"))
        )
        self.how_to_use_label.setText(
            f"<b>{self._t('labels', 'how_to_use_title', default='How to use')}</b><br><br>"
            f"{self._t('labels', 'how_to_use_body', default='')}".replace("\n", "<br>")
        )
        self.desktop_hint_label.setText(str(self._t("labels", "desktop_hint", default="")))
        self.examples_title_label.setText(
            str(self._t("labels", "examples_title", default="Examples"))
        )

        examples = self._t("examples", default=[])
        if not isinstance(examples, list):
            examples = []
        for index, button in enumerate(self.example_buttons):
            button.setText(examples[index] if index < len(examples) else f"Example {index + 1}")

        self.send_button.setText(str(self._t("buttons", "send", default="Run")))
        self.queue_button.setText(str(self._t("buttons", "queue", default="Queue")))
        self.clear_button.setText(str(self._t("buttons", "clear", default="Clear")))
        self.start_button.setText(str(self._t("buttons", "start", default="Start")))
        self.stop_button.setText(str(self._t("buttons", "stop", default="Stop")))
        self.pause_button.setText(str(self._t("buttons", "pause", default="Pause")))
        self.resume_button.setText(str(self._t("buttons", "resume", default="Resume")))
        self.refresh_button.setText(str(self._t("buttons", "refresh", default="Refresh")))
        self.approve_button.setText(str(self._t("buttons", "approve", default="Approve")))
        self.reject_button.setText(str(self._t("buttons", "reject", default="Reject")))

        self.capabilities_text.setPlainText(
            str(self._t("labels", "capabilities_body", default=""))
        )
        self.self_improvement_text.setPlainText(
            str(self._t("labels", "self_improvement_body", default=""))
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #0B1220;
                color: #E5E7EB;
                font-size: 13px;
            }
            QFrame#headerFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #111827, stop: 1 #172554
                );
                border: 1px solid #22304A;
                border-radius: 14px;
            }
            QLabel#appTitle {
                font-size: 24px;
                font-weight: 800;
                color: #F8FAFC;
            }
            QLabel#appSubtitle {
                color: #CBD5E1;
                font-size: 13px;
            }
            QFrame#sectionFrame {
                background-color: #111827;
                border: 1px solid #243041;
                border-radius: 14px;
            }
            QLabel#sectionTitle {
                color: #93C5FD;
                font-size: 15px;
                font-weight: 800;
            }
            QLabel#statusHero {
                color: #F8FAFC;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#subHeadline {
                color: #F8FAFC;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#miniTitle {
                color: #BFDBFE;
                font-size: 13px;
                font-weight: 700;
                margin-top: 4px;
            }
            QLabel#hintLabel {
                color: #FBBF24;
                background-color: #1E293B;
                border: 1px solid #3F4D63;
                border-radius: 10px;
                padding: 10px;
            }
            QTextEdit, QPlainTextEdit, QListWidget, QComboBox {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 10px;
                color: #F8FAFC;
                padding: 8px;
                selection-background-color: #2563EB;
            }
            QTextEdit {
                padding: 12px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #2563EB;
                border: none;
                border-radius: 10px;
                padding: 10px 14px;
                color: white;
                font-weight: 700;
                min-height: 18px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton#exampleButton {
                text-align: left;
                padding: 12px;
                background-color: #1D4ED8;
            }
            QPushButton#exampleButton:hover {
                background-color: #1E40AF;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QSplitter::handle {
                background-color: #22304A;
                width: 8px;
            }
            """
        )

    def _dock_to_center(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return

        geometry = screen.availableGeometry()
        width = min(1500, max(1280, geometry.width() - 80))
        height = min(980, max(860, geometry.height() - 60))
        x = geometry.x() + max(20, (geometry.width() - width) // 2)
        y = geometry.y() + max(20, (geometry.height() - height) // 2)
        self.setGeometry(x, y, width, height)

    def _on_language_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.language_codes):
            return
        self.current_language = self.language_codes[index]
        self._apply_translations()
        self.refresh_dashboard()

    def _use_example(self, index: int) -> None:
        examples = self._t("examples", default=[])
        if not isinstance(examples, list) or index >= len(examples):
            return
        self.command_input.setPlainText(str(examples[index]))
        self.command_input.setFocus()

    def start_daemon(self) -> None:
        started = self.controller.start_daemon()
        if not started:
            self._show_info(str(self._t("messages", "already_running", default="Already running")))
        self.refresh_dashboard()

    def stop_daemon(self) -> None:
        stopped = self.controller.stop_daemon()
        if not stopped:
            self._show_info(str(self._t("messages", "not_running", default="Not running")))
        self.refresh_dashboard()

    def pause_auto_goals(self) -> None:
        self.controller.pause_auto_goals()
        self.refresh_dashboard()

    def resume_auto_goals(self) -> None:
        self.controller.resume_auto_goals()
        self.refresh_dashboard()

    def submit_goal(self) -> None:
        text = self.command_input.toPlainText().strip()
        if not text:
            self._show_warning(str(self._t("messages", "empty_goal", default="Please enter a task")))
            return

        try:
            self.controller.add_goal(text)
        except Exception as exc:
            self._show_error(
                f"{self._t('messages', 'goal_create_failed', default='Failed to create goal')}: {exc}"
            )
            return

        self.command_input.clear()
        self._show_info(str(self._t("messages", "submit_success", default="Task submitted")))
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        try:
            data = self.controller.get_dashboard_data()
        except Exception as exc:
            self.status_summary_label.setText(
                f"{self._t('messages', 'refresh_failed', default='Refresh failed')}: {exc}"
            )
            return

        self._render_status(data.get("status", {}))
        self._render_active_goal(data.get("active_goal"))
        self._render_latest_task(data.get("latest_task"))
        self._render_goals(data.get("recent_goals", []))
        self._render_approvals(data.get("pending_approvals", []))
        self._render_events(data.get("recent_events", []))
        self._render_logs(data.get("recent_logs", []))
        self._render_tools(data.get("recent_tools", []))
        self._render_failures(data.get("recent_failures", []))
        self._render_allowed_roots(data.get("allowed_roots", []))

    def _render_status(self, status: dict[str, Any]) -> None:
        running = self._t("status", "online", default="Online")
        if not status.get("running"):
            running = self._t("status", "stopped", default="Stopped")

        paused = (
            self._t("status", "paused", default="Paused")
            if status.get("auto_goals_paused")
            else self._t("status", "auto", default="Auto")
        )

        bad_state = status.get("bad_state") or {}
        bad_label = (
            self._t("status", "bad", default="Bad")
            if bad_state
            else self._t("status", "normal", default="Normal")
        )

        mode = status.get("mode", self._t("status", "unknown", default="Unknown"))
        severity = status.get("bad_state_severity", self._t("status", "normal", default="Normal"))

        self.status_summary_label.setText(
            f"● {running}   "
            f"{self._t('status', 'mode', default='Mode')}: {mode}   "
            f"{self._t('status', 'auto_mode', default='Auto')}: {paused}   "
            f"{self._t('status', 'state', default='State')}: {bad_label}/{severity}"
        )

        last_tool = status.get("last_tool") or "-"
        last_tool_ok = status.get("last_tool_ok")
        last_tool_text = (
            self._t("status", "ok", default="OK")
            if last_tool_ok is True
            else self._t("status", "failed", default="Failed")
            if last_tool_ok is False
            else self._t("status", "unknown", default="Unknown")
        )
        last_error = status.get("last_error") or "-"
        open_goals = status.get("open_goal_count", 0)
        watched_paths = len(status.get("watched_paths") or [])
        pending_approvals = status.get("pending_approval_count", 0)
        autonomy_mode = status.get("autonomy_mode", self._t("status", "unknown", default="Unknown"))
        recommended_action = bad_state.get("recommended_action") or "-"

        lines = [
            f"{self._t('status', 'open_goals', default='Open goals')}: {open_goals}",
            f"{self._t('status', 'watched_paths', default='Watched paths')}: {watched_paths}",
            f"{self._t('status', 'pending_approvals', default='Pending approvals')}: {pending_approvals}",
            f"{self._t('status', 'autonomy_mode', default='Autonomy mode')}: {autonomy_mode}",
            f"{self._t('status', 'recommended_action', default='Recommended action')}: {recommended_action}",
            f"{self._t('status', 'last_tool', default='Last tool')}: {last_tool} ({last_tool_text})",
            f"{self._t('status', 'last_error', default='Last error')}: {last_error}",
        ]
        self.status_details_label.setText("\n".join(lines))

    def _render_active_goal(self, active_goal: dict[str, Any] | None) -> None:
        if not active_goal:
            self.current_goal_label.setText(str(self._t("labels", "goal_empty", default="No active goal")))
            return

        self.current_goal_label.setText(
            "\n".join(
                [
                    active_goal.get("text", "-"),
                    f"status: {active_goal.get('status', '-')}",
                    f"priority: {active_goal.get('priority', '-')}",
                    f"retry_count: {active_goal.get('retry_count', 0)}",
                    f"progress: {active_goal.get('progress_note') or '-'}",
                ]
            )
        )

    def _render_latest_task(self, latest_task: dict[str, Any] | None) -> None:
        if not latest_task:
            self.reasoning_text.setPlainText(
                str(
                    self._t(
                        "labels",
                        "reasoning_empty",
                        default="No reasoning summary available yet.",
                    )
                )
            )
            self.plan_list.clear()
            self.plan_list.addItem(
                QListWidgetItem(str(self._t("labels", "plan_empty", default="No plan steps")))
            )
            return

        plan = latest_task.get("plan") or {}
        result = latest_task.get("result") or {}
        reasoning = result.get("reasoning_summary") or plan.get("reasoning_summary")
        if isinstance(reasoning, list):
            reasoning_text = "\n".join(str(item) for item in reasoning)
        else:
            reasoning_text = str(
                reasoning
                or self._t("labels", "reasoning_empty", default="No reasoning summary available yet.")
            )
        self.reasoning_text.setPlainText(reasoning_text)

        self.plan_list.clear()
        steps = plan.get("steps") or []
        if not steps:
            self.plan_list.addItem(
                QListWidgetItem(str(self._t("labels", "plan_empty", default="No plan steps")))
            )
            return

        step_results = result.get("steps") or []
        for index, step in enumerate(steps, start=1):
            verify_reason = "-"
            step_ok = None
            if index - 1 < len(step_results):
                verify = (step_results[index - 1].get("verification") or {})
                verify_reason = verify.get("reason") or "-"
                step_ok = step_results[index - 1].get("ok")

            state_text = (
                self._t("status", "ok", default="OK")
                if step_ok is True
                else self._t("status", "failed", default="Failed")
                if step_ok is False
                else self._t("status", "unknown", default="Unknown")
            )
            text = (
                f"{index}. {step.get('description', step.get('tool', '-'))}\n"
                f"tool={step.get('tool', '-')}, args={step.get('args', {})}\n"
                f"verify={state_text}, reason={verify_reason}"
            )
            self.plan_list.addItem(QListWidgetItem(text))

    def _render_goals(self, goals: list[dict[str, Any]]) -> None:
        self.goals_list.clear()
        if not goals:
            self.goals_list.addItem(
                QListWidgetItem(str(self._t("labels", "recent_goals_empty", default="No recent goals")))
            )
            return

        for goal in goals:
            text = (
                f"[{goal.get('status', '-')}] {goal.get('text', '-')}\n"
                f"priority={goal.get('priority', '-')}, updated={goal.get('updated_at', '-')}"
            )
            self.goals_list.addItem(QListWidgetItem(text))

    def _render_approvals(self, approvals: list[dict[str, Any]]) -> None:
        selected_item = self.approvals_list.currentItem()
        selected_approval_id = selected_item.data(Qt.UserRole) if selected_item is not None else None

        self.approvals_list.clear()
        if not approvals:
            self.approvals_list.addItem(
                QListWidgetItem(str(self._t("labels", "approvals_empty", default="No approvals")))
            )
            return

        item_to_select: QListWidgetItem | None = None
        for approval in approvals:
            approval_id = approval.get("id")
            text = (
                f"[{approval.get('risk_level', '-')}] {approval.get('tool', '-')}\n"
                f"goal={approval.get('goal_text', '-')}\n"
                f"reason={approval.get('reason', '-')}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, approval_id)
            self.approvals_list.addItem(item)
            if selected_approval_id is not None and approval_id == selected_approval_id:
                item_to_select = item

        if item_to_select is not None:
            self.approvals_list.setCurrentItem(item_to_select)

    def _render_events(self, events: list[dict[str, Any]]) -> None:
        self.events_list.clear()
        if not events:
            self.events_list.addItem(
                QListWidgetItem(str(self._t("labels", "recent_events_empty", default="No events")))
            )
            return

        for event in events:
            payload = event.get("payload") or {}
            path = payload.get("path", "")
            action = payload.get("action", "")
            decision = event.get("decision", "-")
            reason = event.get("reason") or event.get("ignored_reason") or "-"
            text = (
                f"{event.get('type', '-')}: {action} {path}\n"
                f"decision={decision}, reason={reason}"
            )
            self.events_list.addItem(QListWidgetItem(text))

    def _render_logs(self, logs: list[dict[str, Any]]) -> None:
        self.logs_list.clear()
        if not logs:
            self.logs_list.addItem(
                QListWidgetItem(str(self._t("labels", "recent_logs_empty", default="No logs")))
            )
            return

        for record in logs:
            if "raw" in record:
                text = record["raw"]
            else:
                payload = record.get("payload") or {}
                payload_summary = payload.get("path") or payload.get("action") or "-"
                accepted = record.get("accepted")
                accepted_text = (
                    "accepted" if accepted is True else "ignored" if accepted is False else "unknown"
                )
                text = (
                    f"{record.get('type', '-')}: {payload_summary}\n"
                    f"{accepted_text} | source={record.get('source', '-')}"
                )
            self.logs_list.addItem(QListWidgetItem(text))

    def _render_tools(self, tools: list[dict[str, Any]]) -> None:
        self.tools_list.clear()
        if not tools:
            self.tools_list.addItem(
                QListWidgetItem(str(self._t("labels", "tools_empty", default="No recent tools")))
            )
            return

        for tool in tools:
            text = (
                f"{tool.get('tool_name', '-')}\n"
                f"ok={tool.get('ok', '-')}, error={tool.get('error') or '-'}\n"
                f"failure_code={tool.get('failure_code') or '-'}"
            )
            self.tools_list.addItem(QListWidgetItem(text))

    def _render_failures(self, failures: list[dict[str, Any]]) -> None:
        self.failures_list.clear()
        if not failures:
            self.failures_list.addItem(
                QListWidgetItem(str(self._t("labels", "failures_empty", default="No recent failures")))
            )
            return

        for failure in failures:
            context = failure.get("context") or {}
            recovery_mode = context.get("recovery_mode") or "-"
            tool = context.get("tool") or "-"
            text = (
                f"{failure.get('message', '-')}\n"
                f"tool={tool}, recovery_mode={recovery_mode}\n"
                f"failure_code={failure.get('failure_code') or '-'}"
            )
            self.failures_list.addItem(QListWidgetItem(text))

    def _render_allowed_roots(self, roots: list[str]) -> None:
        if not roots:
            self.allowed_roots_text.setPlainText(
                str(self._t("labels", "allowed_roots_empty", default="No paths available"))
            )
            return
        self.allowed_roots_text.setPlainText("\n".join(str(root) for root in roots))

    def approve_selected_approval(self) -> None:
        item = self.approvals_list.currentItem()
        if item is None or item.data(Qt.UserRole) is None:
            self._show_warning(str(self._t("messages", "select_approval", default="Select approval")))
            return

        approval_id = item.data(Qt.UserRole)
        try:
            self.controller.approve_approval(str(approval_id), note="approved from workspace ui")
        except Exception as exc:
            self._show_error(
                f"{self._t('messages', 'approve_failed', default='Approve failed')}: {exc}"
            )
            return

        self.refresh_dashboard()

    def reject_selected_approval(self) -> None:
        item = self.approvals_list.currentItem()
        if item is None or item.data(Qt.UserRole) is None:
            self._show_warning(str(self._t("messages", "select_approval", default="Select approval")))
            return

        approval_id = item.data(Qt.UserRole)
        try:
            self.controller.reject_approval(str(approval_id), note="rejected from workspace ui")
        except Exception as exc:
            self._show_error(
                f"{self._t('messages', 'reject_failed', default='Reject failed')}: {exc}"
            )
            return

        self.refresh_dashboard()

    def _show_info(self, message: str) -> None:
        QMessageBox.information(self, str(self._t("meta", "app_title", default="Windows Agent")), message)

    def _show_warning(self, message: str) -> None:
        QMessageBox.warning(self, str(self._t("meta", "app_title", default="Windows Agent")), message)

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, str(self._t("meta", "app_title", default="Windows Agent")), message)


def run_sidebar(config_path: str = "configs/default.yaml") -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    controller = AgentController(config_path=config_path)
    window = AgentSidebarWindow(controller)
    window.show()
    return app.exec()