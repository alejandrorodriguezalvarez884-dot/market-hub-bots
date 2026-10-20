// What the API answers (src/botleague/league.py and engine.py).
export type Period = "1d" | "1w" | "1m" | "1y" | "all";
export type Returns = Record<Period, number | null>;
export type Holding = { ticker: string; weight: number }; // weight as a fraction

// A line of the board: a member's bot, or a house bot (house: true, never ranked).
export type Line = {
  slug: string; house: boolean; you: boolean; handle: string; name: string; about: string; since: string | null; as_of: string | null;
  sessions: number; returns: Returns; ranks: Partial<Record<Period, number>>; holdings: Holding[]; holding: number; cash: number | null;
  spark: number[]; stand_in?: boolean;
};

export type Board = {
  sample: boolean; as_of: string | null; stale: boolean; periods: { key: Period; label: string }[];
  visible: boolean; signed_in: boolean; rows: Line[]; house: Line[]; entrants: number;
  benchmark: { ticker: string; returns: Returns | null }; index: { date: string; value: number }[];
  rules: { cost: number; universe: number; hold: number };
};

export type BotPage = Line & {
  curve: { date: string; bot: number; index: number | null }[]; entrants: number;
  rules?: string[]; bot?: Record<string, unknown>; universe?: number;
};

export type Me = { user: { name: string; picture: string } | null; signin: string | null; hub: string | null; local: boolean };

export type MyBot = {
  handle: string; name: string; about: string; submitted_utc: string; since: string | null; as_of: string | null; sessions: number;
  returns: Returns | null; ranks: Partial<Record<Period, number>>; entrants: number; holdings: Holding[]; cash: number | null;
  rules: string[]; universe: number; curve: { date: string; value: number }[];
};
export type Key = { created_utc: string; used_utc: string | null };
export type Overview = { you: MyBot | null; key: Key | null; name: string; stale: boolean };

export type Spec = {
  format: string; cost: number; hold: { min: number; max: number }; universe: { largest: { min: number; max: number } };
  factors: Record<string, { settings: Record<string, { min: number; max: number; default?: number }>; means: string }>;
  rebalance: string[]; weighting: string[]; backtest_years: { min: number; max: number };
};

export const PERIODS: { key: Period; label: string; long: string }[] = [
  { key: "1d", label: "Day", long: "the last session" },
  { key: "1w", label: "Week", long: "the last 5 sessions" },
  { key: "1m", label: "Month", long: "the last 21 sessions" },
  { key: "1y", label: "Year", long: "the last 252 sessions" },
  { key: "all", label: "Since start", long: "since each bot started" },
];
export const digits = (p: Period) => (p === "1d" ? 2 : 1);
