from enum import Enum


class RoleName(str, Enum):
    ADMIN = "ADMIN"
    DRILLING_ENGINEER = "DRILLING_ENGINEER"
    VIEWER = "VIEWER"


class Permission(str, Enum):
    # Dashboard
    DASHBOARD_VIEW = "dashboard:view"

    # Wells
    WELLS_VIEW = "wells:view"
    WELLS_CREATE = "wells:create"
    WELLS_EDIT = "wells:edit"
    WELLS_DELETE = "wells:delete"

    # Drilling Data & Parameters
    DRILLING_DATA_VIEW = "drilling_data:view"
    DRILLING_DATA_WRITE = "drilling_data:write"
    DRILLING_DATA_DELETE = "drilling_data:delete"

    # Historical Records & Reports
    HISTORICAL_RECORDS_VIEW = "historical_records:view"
    HISTORICAL_RECORDS_UPLOAD = "historical_records:upload"
    HISTORICAL_RECORDS_DELETE = "historical_records:delete"

    # Well Comparison
    COMPARISON_VIEW = "comparison:view"
    COMPARISON_ANALYZE = "comparison:analyze"

    # Risk Analysis
    RISK_VIEW = "risk:view"
    RISK_ANALYZE = "risk:analyze"

    # Alerts
    ALERTS_VIEW = "alerts:view"
    ALERTS_ACKNOWLEDGE = "alerts:acknowledge"
    ALERTS_MANAGE = "alerts:manage"

    # Evidence Search
    EVIDENCE_VIEW = "evidence:view"
    EVIDENCE_SEARCH = "evidence:search"

    # Engineering Review
    REVIEWS_VIEW = "reviews:view"
    REVIEWS_CREATE = "reviews:create"
    REVIEWS_EDIT = "reviews:edit"
    REVIEWS_DELETE = "reviews:delete"

    # AI Insights
    AI_INSIGHTS_VIEW = "ai:view"
    AI_INSIGHTS_ASK = "ai:ask"

    # Reports & Exports
    REPORTS_VIEW = "reports:view"
    REPORTS_EXPORT = "reports:export"

    # Data Import
    DATA_IMPORT = "data:import"

    # Administration
    USERS_MANAGE = "users:manage"
    ROLES_MANAGE = "roles:manage"
    SYSTEM_MANAGE = "system:manage"
    API_CONFIG_MANAGE = "api_config:manage"
    AUDIT_LOGS_VIEW = "audit_logs:view"
    PERMANENT_DELETE = "permanent:delete"


# Scalable Role to Permissions Matrix
ROLE_PERMISSIONS: dict[str, set[str]] = {
    RoleName.ADMIN.value: {
        # Full unrestricted access to all permissions
        Permission.DASHBOARD_VIEW.value,
        Permission.WELLS_VIEW.value,
        Permission.WELLS_CREATE.value,
        Permission.WELLS_EDIT.value,
        Permission.WELLS_DELETE.value,
        Permission.DRILLING_DATA_VIEW.value,
        Permission.DRILLING_DATA_WRITE.value,
        Permission.DRILLING_DATA_DELETE.value,
        Permission.HISTORICAL_RECORDS_VIEW.value,
        Permission.HISTORICAL_RECORDS_UPLOAD.value,
        Permission.HISTORICAL_RECORDS_DELETE.value,
        Permission.COMPARISON_VIEW.value,
        Permission.COMPARISON_ANALYZE.value,
        Permission.RISK_VIEW.value,
        Permission.RISK_ANALYZE.value,
        Permission.ALERTS_VIEW.value,
        Permission.ALERTS_ACKNOWLEDGE.value,
        Permission.ALERTS_MANAGE.value,
        Permission.EVIDENCE_VIEW.value,
        Permission.EVIDENCE_SEARCH.value,
        Permission.REVIEWS_VIEW.value,
        Permission.REVIEWS_CREATE.value,
        Permission.REVIEWS_EDIT.value,
        Permission.REVIEWS_DELETE.value,
        Permission.AI_INSIGHTS_VIEW.value,
        Permission.AI_INSIGHTS_ASK.value,
        Permission.REPORTS_VIEW.value,
        Permission.REPORTS_EXPORT.value,
        Permission.DATA_IMPORT.value,
        Permission.USERS_MANAGE.value,
        Permission.ROLES_MANAGE.value,
        Permission.SYSTEM_MANAGE.value,
        Permission.API_CONFIG_MANAGE.value,
        Permission.AUDIT_LOGS_VIEW.value,
        Permission.PERMANENT_DELETE.value,
    },
    RoleName.DRILLING_ENGINEER.value: {
        # Technical & Operational Engineering Access
        Permission.DASHBOARD_VIEW.value,
        Permission.WELLS_VIEW.value,
        Permission.WELLS_CREATE.value,
        Permission.WELLS_EDIT.value,
        Permission.DRILLING_DATA_VIEW.value,
        Permission.DRILLING_DATA_WRITE.value,
        Permission.HISTORICAL_RECORDS_VIEW.value,
        Permission.HISTORICAL_RECORDS_UPLOAD.value,
        Permission.COMPARISON_VIEW.value,
        Permission.COMPARISON_ANALYZE.value,
        Permission.RISK_VIEW.value,
        Permission.RISK_ANALYZE.value,
        Permission.ALERTS_VIEW.value,
        Permission.ALERTS_ACKNOWLEDGE.value,
        Permission.EVIDENCE_VIEW.value,
        Permission.EVIDENCE_SEARCH.value,
        Permission.REVIEWS_VIEW.value,
        Permission.REVIEWS_CREATE.value,
        Permission.REVIEWS_EDIT.value,
        Permission.AI_INSIGHTS_VIEW.value,
        Permission.AI_INSIGHTS_ASK.value,
        Permission.REPORTS_VIEW.value,
        Permission.REPORTS_EXPORT.value,
        Permission.DATA_IMPORT.value,
        Permission.AUDIT_LOGS_VIEW.value,
    },
    RoleName.VIEWER.value: {
        # Strictly Read-Only Access
        Permission.DASHBOARD_VIEW.value,
        Permission.WELLS_VIEW.value,
        Permission.DRILLING_DATA_VIEW.value,
        Permission.HISTORICAL_RECORDS_VIEW.value,
        Permission.COMPARISON_VIEW.value,
        Permission.RISK_VIEW.value,
        Permission.ALERTS_VIEW.value,
        Permission.EVIDENCE_VIEW.value,
        Permission.EVIDENCE_SEARCH.value,
        Permission.REVIEWS_VIEW.value,
        Permission.AI_INSIGHTS_VIEW.value,
        Permission.REPORTS_VIEW.value,
        Permission.REPORTS_EXPORT.value,
    },
}


def has_permission(role: str | None, permission: str | Permission) -> bool:
    if not role:
        return False
    perm_val = permission.value if isinstance(permission, Permission) else permission
    perms = ROLE_PERMISSIONS.get(role.upper(), set())
    return perm_val in perms


def get_role_permissions(role: str | None) -> list[str]:
    if not role:
        return []
    return sorted(list(ROLE_PERMISSIONS.get(role.upper(), set())))
