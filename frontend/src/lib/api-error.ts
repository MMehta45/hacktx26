type ValidationIssue = {
  loc?: unknown;
  msg?: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function backendErrorMessage(body: unknown, status: number): string {
  if (!isRecord(body) || !("detail" in body)) {
    return `Backend returned ${status}`;
  }

  const detail = body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const issues = detail
      .filter(isRecord)
      .map((issue: ValidationIssue) => {
        const location = Array.isArray(issue.loc)
          ? issue.loc.filter((part) => part !== "body").map(String).join(".")
          : "request";
        const message = typeof issue.msg === "string" ? issue.msg : "Invalid value";
        return `${location || "request"}: ${message}`;
      });
    if (issues.length) return issues.join("; ");
  }

  return `Backend returned ${status}`;
}
