"""
Enterprise Policy-Driven RBAC Engine.

Implements declarative scoped authorization without spaghetti if-else checks:
- Scopes: GLOBAL, ORGANIZATION, DEPARTMENT, RESOURCE, OWN, CUSTOM
- Role Hierarchy:
  - Admin: GLOBAL full access
  - HR: ORGANIZATION access for employee/HR resources
  - Manager: DEPARTMENT access (Engineering Manager -> engineering, Finance Manager -> finance, HR Manager -> hr)
  - Employee: RESOURCE / OWN (Cannot upload documents; full LLM & RAG query access scoped to permitted resources)
"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any
from fastapi import Depends, HTTPException, status
from app.auth.models import UserInDB, Role


class AccessScope(str, Enum):
    GLOBAL = "GLOBAL"
    ORGANIZATION = "ORGANIZATION"
    DEPARTMENT = "DEPARTMENT"
    RESOURCE = "RESOURCE"
    OWN = "OWN"
    CUSTOM = "CUSTOM"


class Action(str, Enum):
    DOCUMENT_READ = "documents:read"
    DOCUMENT_UPLOAD = "documents:upload"
    DOCUMENT_DELETE = "documents:delete"
    DOCUMENT_REINDEX = "documents:reindex"
    LLM_CHAT = "llm:chat"
    LLM_RAG_SEARCH = "llm:rag_search"
    LLM_STREAM = "llm:stream"
    ANALYTICS_READ = "analytics:read"
    USER_MANAGE = "users:manage"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    scope: Optional[AccessScope]
    reason: str


class PolicyEngine:
    """
    Declarative Policy-Driven RBAC Evaluator.
    Maps (Role, Action) -> AccessScope and evaluates permission requests dynamically.
    """

    POLICY_MATRIX: dict[str, dict[Action, Optional[AccessScope]]] = {
        Role.ADMIN.value: {
            Action.DOCUMENT_READ: AccessScope.GLOBAL,
            Action.DOCUMENT_UPLOAD: AccessScope.GLOBAL,
            Action.DOCUMENT_DELETE: AccessScope.GLOBAL,
            Action.DOCUMENT_REINDEX: AccessScope.GLOBAL,
            Action.LLM_CHAT: AccessScope.GLOBAL,
            Action.LLM_RAG_SEARCH: AccessScope.GLOBAL,
            Action.LLM_STREAM: AccessScope.GLOBAL,
            Action.ANALYTICS_READ: AccessScope.GLOBAL,
            Action.USER_MANAGE: AccessScope.GLOBAL,
        },
        Role.HR.value: {
            Action.DOCUMENT_READ: AccessScope.ORGANIZATION,    # Org-wide employee/HR resources
            Action.DOCUMENT_UPLOAD: AccessScope.ORGANIZATION,  # Upload HR & employee resources
            Action.DOCUMENT_DELETE: AccessScope.OWN,
            Action.DOCUMENT_REINDEX: AccessScope.ORGANIZATION,
            Action.LLM_CHAT: AccessScope.ORGANIZATION,
            Action.LLM_RAG_SEARCH: AccessScope.ORGANIZATION,
            Action.LLM_STREAM: AccessScope.ORGANIZATION,
            Action.ANALYTICS_READ: AccessScope.ORGANIZATION,
            Action.USER_MANAGE: AccessScope.ORGANIZATION,      # Employee directory access
        },
        Role.MANAGER.value: {
            Action.DOCUMENT_READ: AccessScope.DEPARTMENT,      # Department-scoped (Engineering, Finance, HR)
            Action.DOCUMENT_UPLOAD: AccessScope.DEPARTMENT,    # Upload within department
            Action.DOCUMENT_DELETE: AccessScope.OWN,
            Action.DOCUMENT_REINDEX: AccessScope.DEPARTMENT,
            Action.LLM_CHAT: AccessScope.DEPARTMENT,
            Action.LLM_RAG_SEARCH: AccessScope.DEPARTMENT,
            Action.LLM_STREAM: AccessScope.DEPARTMENT,
            Action.ANALYTICS_READ: AccessScope.DEPARTMENT,
            Action.USER_MANAGE: AccessScope.DEPARTMENT,
        },
        Role.EMPLOYEE.value: {
            Action.DOCUMENT_READ: AccessScope.DEPARTMENT,      # View general & department docs
            Action.DOCUMENT_UPLOAD: None,                      # CANNOT UPLOAD DOCUMENTS!
            Action.DOCUMENT_DELETE: AccessScope.OWN,
            Action.DOCUMENT_REINDEX: None,
            Action.LLM_CHAT: AccessScope.DEPARTMENT,           # FULL LLM Chat access
            Action.LLM_RAG_SEARCH: AccessScope.DEPARTMENT,     # FULL LLM RAG Search access
            Action.LLM_STREAM: AccessScope.DEPARTMENT,         # FULL LLM Streaming access
            Action.ANALYTICS_READ: None,
            Action.USER_MANAGE: None,
        },
    }

    @classmethod
    def evaluate(
        cls,
        user: UserInDB,
        action: Action,
        resource: Optional[dict[str, Any]] = None,
    ) -> PolicyDecision:
        role_policies = cls.POLICY_MATRIX.get(user.role, {})
        scope = role_policies.get(action)

        if scope is None:
            return PolicyDecision(
                allowed=False,
                scope=None,
                reason=f"Action '{action.value}' is restricted for role '{user.role}'."
            )

        # Global scope bypass
        if scope == AccessScope.GLOBAL:
            return PolicyDecision(allowed=True, scope=scope, reason="Granted global organization access.")

        # Organization scope
        if scope == AccessScope.ORGANIZATION:
            return PolicyDecision(allowed=True, scope=scope, reason="Granted organization-level access.")

        # Department scope evaluation
        if scope == AccessScope.DEPARTMENT:
            if resource and "department" in resource:
                req_dept = str(resource.get("department")).lower()
                user_dept = str(user.department).lower()
                if req_dept and req_dept not in [user_dept, "general"]:
                    return PolicyDecision(
                        allowed=False,
                        scope=scope,
                        reason=f"Department scope mismatch: resource is '{req_dept}', user department is '{user_dept}'."
                    )
            return PolicyDecision(allowed=True, scope=scope, reason="Granted department-scoped access.")

        # Resource / Owner scope evaluation
        if scope in (AccessScope.OWN, AccessScope.RESOURCE):
            if resource and "uploaded_by" in resource:
                if str(resource.get("uploaded_by")) != str(user.id):
                    return PolicyDecision(
                        allowed=False,
                        scope=scope,
                        reason="Resource is restricted to owner access."
                    )
            return PolicyDecision(allowed=True, scope=scope, reason="Granted resource owner access.")

        return PolicyDecision(allowed=True, scope=scope, reason="Granted access.")

    @classmethod
    def get_permitted_departments(cls, user: UserInDB) -> list[str]:
        """Returns permitted department list for RAG retrieval filter."""
        if user.role in [Role.ADMIN.value, Role.HR.value]:
            return ["all"]
        return [user.department.lower(), "general"]


def require_permission(action: Action):
    """
    FastAPI Security Dependency Factory.
    Evaluates policy matrix for current_user and action without if-else bloat.
    """
    from app.auth.dependencies import get_current_user

    async def _dependency(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        decision = PolicyEngine.evaluate(current_user, action)
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: {decision.reason} [Scope: {decision.scope or 'NONE'}]",
            )
        return current_user

    return _dependency
