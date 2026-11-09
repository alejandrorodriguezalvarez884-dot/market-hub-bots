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
  spark: number[]; stand_in?: boolean; wins?: number; // weeks won, on the board's lines
};

// Weekly prizes (league.py): the week being played as it stands, every week's winners, newest first,
// and the bots that have won the most weeks. A winner that is no longer playing comes as { gone }.
export type Who = { slug: string; name: string; handle: string; you: boolean };
export type Winner = Who | { gone: true };
export type Week = { week: string; from: string; to: string; sessions: number; return: number; index: number | null; entrants: number };
export type Weekly = {
  current: (Omit<Week, "return"> & { standing: (Who & { place: number; return: number })[] }) | null;
  winners: (Week & { bots: Winner[] })[];
  ranking: (Who & { wins: number; last: string })[];
};

export type Board = {
  sample: boolean; as_of: string | null; stale: boolean; periods: { key: Period; label: string }[];
  visible: boolean; signed_in: boolean; rows: Line[]; entrants: number;
  benchmark: { ticker: string; returns: Returns | null }; index: { date: string; value: number }[];
  rules: { cost: number; universe: number; hold: number }; weekly: Weekly;
};

// A rebalance, as a bot's page lists it.
export type Move = {
  date: string; turnover: number; cost: number; after: Record<string, number>;
  bought: { ticker: string; weight: number }[]; sold: { ticker: string; weight: number }[];
  raised: { ticker: string; before: number; after: number }[]; cut: { ticker: string; before: number; after: number }[];
};
export type Version = { from: string; what: string[] };
export type Preview = { as_of: string; weights: Record<string, number> } | null;

export type BotPage = Line & {
  curve: { date: string; bot: number; index: number | null }[]; entrants: number;
  rules?: string[]; bot?: Bot; universe?: number;
  log: Move[]; versions: Version[]; paused: boolean; starts: string | null; preview: Preview;
  wins: (Omit<Week, "sessions"> & { shared: boolean })[]; // the weeks it won, newest first
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
// How the player's bot did since the close their device last showed, or over the last close (league.summary).
export type Summary = {
  name: string; slug: string | null; paused: boolean; pending: { what: string[]; applies: string } | null; started: boolean; starts?: string | null;
  as_of?: string; from?: string | null; since_visit?: boolean; from_start?: boolean; sessions?: number;
  bot?: number | null; index?: number | null; ticker?: string;
  place?: { now: number | null; of: number; then: number | null; of_then: number | null };
  moves?: Move[]; moved?: number; changed?: Version[];
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
