export const DEFAULT_HOURLY_WAGE = "20.00";
export const DEFAULT_REPAIR_QUOTE = 400;
export const MAX_HOURLY_WAGE_CENTS = 50_000;

export function wageInputToCents(value: string): number | null {
  const normalized = value.trim();
  if (!/^\d+(?:\.\d{0,2})?$/.test(normalized)) return null;
  const [dollars, fraction = ""] = normalized.split(".");
  const cents = Number(dollars) * 100 + Number(fraction.padEnd(2, "0"));
  if (!Number.isSafeInteger(cents) || cents <= 0 || cents > MAX_HOURLY_WAGE_CENTS) {
    return null;
  }
  return cents;
}

export function wagePreview(hourlyRateCents: number) {
  return {
    grossPerShiftCents: hourlyRateCents * 8,
    grossWeeklyCents: hourlyRateCents * 40,
  };
}

export function formatCurrency(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}
