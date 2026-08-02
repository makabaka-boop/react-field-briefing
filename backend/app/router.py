"""URL routing table mapping (method, path) to handler callables.

Paths use ``{name}`` segments for integer path params. The router matches
incoming requests, extracts params, and dispatches to Handlers methods with
a normalized signature.
"""

import re

from .errors import MethodNotAllowedError, NotFoundError


class Route:
    def __init__(self, method, pattern, handler_name, wants_body=False):
        self.method = method
        self.handler_name = handler_name
        self.wants_body = wants_body
        # Convert /projects/{project_id} into a regex with named groups.
        regex = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern)
        self.regex = re.compile("^" + regex + "$")


ROUTES = [
    # projects
    Route("POST", "/projects", "create_project", wants_body=True),
    Route("GET", "/projects", "list_projects"),
    Route("GET", "/projects/{project_id}", "get_project"),
    Route("POST", "/projects/{project_id}/status",
          "transition_project_status", wants_body=True),
    Route("GET", "/projects/{project_id}/site_risk", "project_site_risk"),
    # sites
    Route("POST", "/sites", "create_site", wants_body=True),
    Route("GET", "/sites", "list_sites"),
    Route("GET", "/sites/{site_id}", "get_site"),
    # templates
    Route("POST", "/templates", "create_template", wants_body=True),
    Route("GET", "/templates", "list_templates"),
    Route("GET", "/templates/{template_id}", "get_template"),
    Route("POST", "/templates/{template_id}/create_project",
          "create_project_from_template", wants_body=True),
    # findings
    Route("POST", "/findings", "save_finding_draft", wants_body=True),
    Route("GET", "/findings", "list_findings"),
    Route("GET", "/findings/{finding_id}", "get_finding"),
    Route("PUT", "/findings/{finding_id}", "update_finding_draft",
          wants_body=True),
    Route("POST", "/findings/{finding_id}/submit", "submit_finding",
          wants_body=True),
    Route("POST", "/findings/{finding_id}/status", "transition_finding",
          wants_body=True),
    Route("POST", "/findings/{finding_id}/review", "review_finding",
          wants_body=True),
    Route("GET", "/findings/{finding_id}/timeline", "finding_timeline"),
    # attachments
    Route("POST", "/attachments", "create_attachment", wants_body=True),
    Route("GET", "/attachments", "list_attachments"),
    # audit + overview
    Route("GET", "/audit_events", "list_audit_events"),
    Route("GET", "/risk_overview", "risk_overview"),
    Route("GET", "/consistency_checks", "consistency_checks"),
]

_INT_PARAMS = {"project_id", "site_id", "finding_id", "template_id",
               "attachment_id"}


class Router:
    def __init__(self, handlers):
        self.handlers = handlers

    def dispatch(self, method, path, query, body):
        """Return (status_code, body_dict) for a matched route.

        Raises NotFoundError when no path matches, MethodNotAllowedError when
        the path matches but the method does not.
        """
        path_matched = False
        for route in ROUTES:
            match = route.regex.match(path)
            if not match:
                continue
            path_matched = True
            if route.method != method:
                continue
            params = match.groupdict()
            args = []
            for name, value in params.items():
                if name in _INT_PARAMS:
                    try:
                        args.append(int(value))
                    except ValueError:
                        raise NotFoundError(
                            "Resource id must be an integer.",
                            details={name: value},
                        )
                else:
                    args.append(value)
            handler = getattr(self.handlers, route.handler_name)
            if route.wants_body:
                return handler(*args, body or {})
            if route.method == "GET":
                return handler(*args, query) if _takes_query(
                    route.handler_name) else handler(*args)
            return handler(*args)
        if path_matched:
            raise MethodNotAllowedError(
                "Method not allowed for this path.",
                details={"method": method, "path": path},
            )
        raise NotFoundError(
            "No route matches this path.",
            details={"method": method, "path": path},
        )


# Handlers that accept a query-params dict as their trailing argument.
_QUERY_HANDLERS = {
    "list_projects", "list_sites", "list_templates", "list_findings",
    "list_attachments", "list_audit_events", "risk_overview",
    "consistency_checks",
}


def _takes_query(handler_name):
    return handler_name in _QUERY_HANDLERS
