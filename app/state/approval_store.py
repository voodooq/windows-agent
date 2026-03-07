from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from app.schemas.approval import ApprovalRequest


class ApprovalStore:
    def __init__(self, path: str = "data/approvals.json") -> None:
        self.path = Path(path)

    def load_all(self) -> List[ApprovalRequest]:
        if not self.path.exists():
            return []

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            return [ApprovalRequest(**item) for item in data]
        except Exception:
            return []

    def save_all(self, approvals: List[ApprovalRequest]) -> List[ApprovalRequest]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.model_dump() for item in approvals]
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return approvals

    def list_pending(self) -> List[ApprovalRequest]:
        return [item for item in self.load_all() if item.status == "pending"]

    def get(self, approval_id: str) -> Optional[ApprovalRequest]:
        for item in self.load_all():
            if item.id == approval_id:
                return item
        return None

    def create(
        self,
        goal_text: str,
        step_id: str,
        tool: str,
        args: dict,
        expected: str | None,
        risk_level: str,
        reason: str,
        requested_by: str = "executor",
        bad_state: dict | None = None,
        metadata: dict | None = None,
    ) -> ApprovalRequest:
        approvals = self.load_all()

        duplicate = next(
            (
                item
                for item in approvals
                if item.status == "pending"
                and item.goal_text == goal_text
                and item.step_id == step_id
                and item.tool == tool
            ),
            None,
        )
        if duplicate is not None:
            return duplicate

        approval = ApprovalRequest(
            id=str(uuid4()),
            goal_text=goal_text,
            step_id=step_id,
            tool=tool,
            args=args or {},
            expected=expected,
            risk_level=risk_level,
            reason=reason,
            requested_by=requested_by,
            bad_state=bad_state or {},
            metadata=metadata or {},
        )
        approvals.append(approval)
        self.save_all(approvals)
        return approval

    def resolve(
        self,
        approval_id: str,
        approved: bool,
        note: str | None = None,
    ) -> Optional[ApprovalRequest]:
        approvals = self.load_all()
        updated: Optional[ApprovalRequest] = None

        for item in approvals:
            if item.id != approval_id:
                continue
            item.status = "approved" if approved else "rejected"
            item.updated_at = datetime.utcnow().isoformat()
            item.resolved_at = item.updated_at
            item.resolution_note = note
            updated = item
            break

        if updated is None:
            return None

        self.save_all(approvals)
        return updated