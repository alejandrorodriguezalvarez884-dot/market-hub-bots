// The rules of the competition and the format of a bot (views/Rules.astro). The seven figures'
// explanations come from the service (/api/bot/spec), in the page's language.
import { words } from ".";

// A word of the format, as it is written in the file. The paragraphs of the format are markup
// built only from these constants (set:html), never from anything a reader sends.
const c = (s: string) => `<span class="num text-ink">${s}</span>`;

export const rules = words(
  {
    title: "Rules and format · Bot League",
    description:
      "The rules of Bot League and the format of a bot: the companies, the seven figures a bot can use, costs, ranking and what others see.",
    kicker: "Rules and format",
    h1: "The same closes, the same costs and the same start for every bot.",
    rules: [
      ["A bot is a file of rules", "Not code. The format is markethub-bot/1, below and in the kit's SPEC.md. Claude writes it with you on your page, or your own agent with the kit; the service checks every field and refuses anything it does not describe."],
      ["Paper only", "Bot League runs every bot with no money, no broker and no orders. On the sessions a bot looks again, it decides at the close and trades at that close."],
      ["The 500 largest US companies", "A bot chooses among them, funds left out, from the list of the day it is sent in. It holds 1 to 50 of them, long only: no short sales and no borrowing."],
      ["Costs and returns", "Each rebalance pays 0.10% of what changes hands. Returns are on price, dividends left out, and cash earns nothing."],
      ["Ranked from the next close", "A bot's record starts at the first close after it is sent in. Nothing before counts: a backtest is a simulation of the past, for its owner alone."],
      ["Day, week, month, year and since start", "Over the last 1, 5, 21 and 252 sessions, and since each bot started, each ranked among the bots that have run that long. The S&P 500 (SPY) is on the board for reference, never ranked."],
      ["One bot per member", "Sending in another one replaces it and starts its record again. Withdrawing it removes it and its record."],
      ["What everyone sees", "The board is public: anyone, signed in or not, sees the name you show under, the bot's name and idea, its returns, its curve and what it holds. Its rules are yours alone."],
      ["Your key", "The kit carries a key that lets your agent check, backtest and send in your bot, nothing else. Only its fingerprint is kept. A new key replaces the old one; you can take it back at any time."],
    ] as [string, string][],
    formatKicker: "The format",
    formatTitle: "What a bot can say",
    format: [
      `${c("universe")} · ${c(`{"largest": 20–500}`)} or a list of 2 to 100 tickers among the largest, and an ${c("exclude")} list.`,
      `${c("filters")} · up to 8 figures, each with a ${c("min")}, a ${c("max")} or both: a company outside them is left out.`,
      `${c("score")} · 1 to 8 figures, each with a ${c("weight")} from −5 to 5 (below 0 prefers the lowest). Each figure is turned into a z-score across the companies left, capped at ±3, and the weighted sum ranks them.`,
      `${c("hold")} · how many of the best it holds, 1 to 50. ${c("weighting")} · equal, inverse_volatility or score. ${c("max_weight")} · the most one stock can be, 2% to 100%.`,
      `${c("rebalance")} · daily, weekly (the first close of each week) or monthly (the first close of each month).`,
      `${c("market")} · a figure of the S&P 500 with its bounds, and the share to hold in cash when it is outside them.`,
    ],
    seven: "The seven figures",
    fromCloses: "all from daily closes",
    // Written by the page's script.
    byDefault: (v: number) => `(default ${v})`,
    unread: "The figures could not be read just now.",
  },
  {
    title: "Reglas y formato · Bot League",
    description:
      "Las reglas de Bot League y el formato de un bot: las empresas, las siete cifras que puede usar un bot, los costes, la clasificación y lo que ven los demás.",
    kicker: "Reglas y formato",
    h1: "Los mismos cierres, los mismos costes y el mismo comienzo para todos los bots.",
    rules: [
      ["Un bot es un archivo de reglas", "No es código. El formato es markethub-bot/1, aquí abajo y en el SPEC.md del kit. Claude lo escribe contigo en tu página, o tu propio agente con el kit; el servicio comprueba cada campo y rechaza todo lo que el formato no describe."],
      ["Solo en papel", "Bot League ejecuta todos los bots sin dinero, sin bróker y sin órdenes. En las sesiones en las que un bot revisa la cartera, decide al cierre y opera a ese mismo cierre."],
      ["Las 500 mayores empresas de EE. UU.", "Un bot elige entre ellas, sin fondos, de la lista del día en que se envía. Tiene de 1 a 50, solo posiciones largas: sin ventas en corto y sin préstamos."],
      ["Costes y rentabilidades", "Cada rebalanceo paga el 0,10 % de lo que cambia de manos. Las rentabilidades son de precio, sin dividendos, y la liquidez no rinde nada."],
      ["Clasificado desde el próximo cierre", "El historial de un bot empieza en el primer cierre tras su envío. Lo anterior no cuenta: un backtest es una simulación del pasado, solo para su dueño."],
      ["Día, semana, mes, año y desde el inicio", "En las últimas 1, 5, 21 y 252 sesiones, y desde que empezó cada bot, cada periodo clasificado entre los bots que llevan ese tiempo. El S&P 500 (SPY) está en la clasificación como referencia y nunca ocupa un puesto."],
      ["Un bot por miembro", "Enviar otro lo sustituye y su historial empieza de cero. Retirarlo lo borra junto con su historial."],
      ["Lo que ve todo el mundo", "La clasificación es pública: cualquiera, haya entrado o no, ve el nombre con el que sales, el nombre y la idea del bot, sus rentabilidades, su curva y lo que tiene. Sus reglas son solo tuyas."],
      ["Tu clave", "El kit lleva una clave que deja a tu agente comprobar tu bot, hacer su backtest y enviarlo, y nada más. Solo se guarda su huella. Una clave nueva sustituye a la anterior; puedes retirarla cuando quieras."],
    ],
    formatKicker: "El formato",
    formatTitle: "Lo que puede decir un bot",
    format: [
      `${c("universe")} · ${c(`{"largest": 20–500}`)} o una lista de 2 a 100 tickers entre las mayores, y una lista ${c("exclude")}.`,
      `${c("filters")} · hasta 8 cifras, cada una con un ${c("min")}, un ${c("max")} o los dos: una empresa fuera de ellos queda excluida.`,
      `${c("score")} · de 1 a 8 cifras, cada una con un ${c("weight")} de −5 a 5 (por debajo de 0 prefiere las más bajas). Cada cifra se convierte en una puntuación z entre las empresas que quedan, limitada a ±3, y la suma ponderada las ordena.`,
      `${c("hold")} · cuántas de las mejores tiene, de 1 a 50. ${c("weighting")} · equal, inverse_volatility o score. ${c("max_weight")} · lo máximo que puede pesar una acción, del 2 % al 100 %.`,
      `${c("rebalance")} · daily, weekly (el primer cierre de cada semana) o monthly (el primer cierre de cada mes).`,
      `${c("market")} · una cifra del S&P 500 con sus límites, y la parte que mantiene en liquidez cuando está fuera de ellos.`,
    ],
    seven: "Las siete cifras",
    fromCloses: "todas con los cierres diarios",
    byDefault: (v: number) => `(por defecto ${v})`,
    unread: "Ahora mismo no se pueden leer las cifras.",
  },
);
