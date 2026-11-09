// What the API answers (src/botleague/league.py and engine.py).
import { lang } from "../i18n";
import { common } from "../i18n/common";

export type Period = "1d" | "1w" | "1m" | "1y" | "all";
export type Returns = Record<Period, number | null>;
export type Holding = { ticker: string; weight: number }; // weight as a fraction

// A line of the board: a member's bot, shown under the first name of its owner's account.
export type Line = {
  slug: string; id: string | null; you: boolean; handle: string; name: string; about: string; since: string | null; as_of: string | null;
  sessions: number; returns: Returns; ranks: Partial<Record<Period, number>>; holdings: Holding[]; holding: number; cash: number | null;
  spark: number[]; stand_in?: boolean;
};

export type Board = {
  sample: boolean; as_of: string | null; stale: boolean; periods: { key: Period; label: string }[];
  visible: boolean; signed_in: boolean; rows: Line[]; entrants: number;
  benchmark: { ticker: string; returns: Returns | null }; index: { date: string; value: number }[];
  rules: { cost: number; universe: number; hold: number };
};

// A rebalance, as a bot's page lists it.
export type Move = {
  date: string; turnover: number; cost: number; after: Record<string, number>;
  bought: { ticker: string; weight: number }[]; sold: { ticker: string; weight: number }[];
  raised: { ticker: string; before: number; after: number }[]; cut: { ticker: string; before: number; after: number }[];
  reasons?: Reasons;
};
// Why a rebalance moved what it moved, in words written by the service (botleague/why.py): for the
// move, and for each stock it bought, sold, raised or cut. "full" is its owner's view, with the
// figures its rules read; everyone else gets what the rules did without what they are. Moves
// logged before 2026-11-10, and all but its latest 60, have none.
export type Reasons = { full: boolean; lines: string[]; names: Record<string, { why: string; figures?: string[] }> };
export type Version = { from: string; what: string[] };
export type Preview = { as_of: string; weights: Record<string, number> } | null;

export type BotPage = Line & {
  curve: { date: string; bot: number; index: number | null }[]; entrants: number;
  rules?: string[]; bot?: Bot; universe?: number;
  log: Move[]; versions: Version[]; paused: boolean; starts: string | null; preview: Preview;
};

// A bot's rules, in the markethub-bot/1 format.
// A company it always holds, with the least share of the portfolio it keeps (0 for none).
export type Pin = { ticker: string; min_weight: number };
export type Factor = { factor: string; [setting: string]: number | string | undefined; min?: number; max?: number; weight?: number; cash?: number };
export type Bot = {
  format: string; name: string; about: string; universe: { largest?: number; tickers?: string[]; exclude: string[] }; always?: Pin[];
  rebalance: string; filters: Factor[]; score: Factor[]; hold: number; weighting: string; max_weight: number; market?: Factor;
};

export type Me = { user: { name: string; picture: string } | null; signin: string | null; hub: string | null; local: boolean };

export type MyBot = {
  handle: string; id: string | null; name: string; about: string; submitted_utc: string; since: string | null; as_of: string | null; sessions: number;
  returns: Returns | null; ranks: Partial<Record<Period, number>>; entrants: number; holdings: Holding[]; cash: number | null;
  rules: string[]; universe: number; curve: { date: string; value: number }[];
  bot: Bot; paused: boolean; exclude: string[]; always: Pin[]; preview: Preview; rules_changed_utc: string | null; log: Move[];
  versions: (Version & { changed_utc: string })[];
  pending: { changed_utc: string; what: string[]; paused: boolean; rules: string[]; bot: Bot; exclude: string[]; always: Pin[] } | null;
};
export type Checked = { ok: boolean; bot: Bot; universe: number; rules: string[]; holds: Preview };
export type ChatAnswer = { reply: string; proposal: Bot | null; rules?: string[]; problems?: string[]; left?: number };
export type ChatStatus = { on: boolean; per_member_per_day: number; left?: number };
// Building a bot on the page: Claude's answer with the proposal's rules in words and what it would hold.
export type DraftAnswer = ChatAnswer & { holds?: Preview };
// A backtest, for the owner of a draft: a simulation of the past (engine.Bots.backtest).
export type Side = { total_return: number; annual_return: number | null; volatility: number | null; max_drawdown: number };
export type Backtest = {
  start: string; end: string; sessions: number; universe: number; rules: string[]; bot: Side; benchmark: Side & { ticker: string };
  months: { month: string; return: number; benchmark: number }[]; turnover_per_year: number; costs_per_year: number;
  holdings: Holding[]; cash: number; curve: { date: string; bot: number; benchmark: number }[]; notes: string[];
};
export type Key = { created_utc: string; used_utc: string | null };
export type Overview = { you: MyBot | null; key: Key | null; name: string; stale: boolean };

export type Spec = {
  format: string; cost: number; hold: { min: number; max: number }; universe: { largest: { min: number; max: number } };
  factors: Record<string, { settings: Record<string, { min: number; max: number; default?: number }>; means: string }>;
  rebalance: string[]; weighting: string[]; backtest_years: { min: number; max: number };
};

// The periods of the board. Their words are read when used, so they follow the page's language
// (i18n/common.ts); the shape stays { key, label, long }.
const period = (key: Period) => ({
  key,
  get label(): string {
    return common[lang()].periods[key].label;
  },
  get long(): string {
    return common[lang()].periods[key].long;
  },
});
export const PERIODS: { key: Period; readonly label: string; readonly long: string }[] = (["1d", "1w", "1m", "1y", "all"] as Period[]).map(period);
export const digits = (p: Period) => (p === "1d" ? 2 : 1);
