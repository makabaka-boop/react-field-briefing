from pydantic import BaseModel


class RiskOverview(BaseModel):
    total_projects: int
    total_sites: int
    total_findings: int
    by_risk: dict[str, int]
    by_status: dict[str, int]
    by_region: dict[str, int]


class SiteRiskItem(BaseModel):
    site_id: int
    site_code: str
    site_name: str
    region: str
    total_findings: int
    by_risk: dict[str, int]
    highest_risk: str


class TimelineEvent(BaseModel):
    event_type: str
    event_id: int
    entity_type: str
    entity_id: int
    occurred_at: str
    actor: str
    summary: str
    details: dict


class ConsistencyCheck(BaseModel):
    check_name: str
    description: str
    passed: bool
    issue_count: int
    issues: list[dict]


class ConsistencyReport(BaseModel):
    passed: bool
    total_checks: int
    failed_checks: int
    total_issues: int
    checks: list[ConsistencyCheck]
