// The welcome card (components/Welcome.astro): what a first visit sees on the leaderboard and on a
// bot's page, the pages a link brings people to without the home page. The same three steps as the
// iPhone app's welcome (market-hub-bots-mobile, src/lib/words.ts): change them together.
import { words } from ".";

export const welcome = words(
  {
    label: "Bot League in three steps",
    head: "New here? Bot League in three steps",
    close: "Close",
    steps: [
      ["A free game: you build a bot, it picks the stocks.",
        "Tell Claude how you would pick stocks and it builds your bot: a set of rules, no code. From the next close it plays on paper against everyone else's, and the leaderboard keeps score."],
      ["No real money. No broker. No advice.",
        "Nothing to deposit and nothing to win: every bot plays on paper, with the same prices and costs. Bot League describes what bots did; it never tells anyone to buy or sell anything."],
      ["Build your bot, or just look around.",
        "Sign in with your account on The Market Hub and tell Claude your idea. Or start with the leaderboard: who's ahead over the day, week, month, year and since start."],
    ] as [string, string][],
    build: "Build your bot with Claude",
    gotIt: "Got it",
    how: "How to play →",
  },
  {
    label: "Bot League en tres pasos",
    head: "¿Primera vez aquí? Bot League en tres pasos",
    close: "Cerrar",
    steps: [
      ["Un juego gratis: tú creas un bot y él elige las acciones.",
        "Cuéntale a Claude cómo elegirías acciones y él crea tu bot: un conjunto de reglas, sin programar. Desde el próximo cierre juega en papel contra los de los demás, y la clasificación lleva la cuenta."],
      ["Sin dinero real. Sin bróker. Sin consejos.",
        "Nada que depositar y nada que ganar: todos los bots juegan en papel, con los mismos precios y costes. Bot League describe lo que han hecho los bots; nunca le dice a nadie que compre ni que venda nada."],
      ["Crea tu bot o, de momento, solo mira.",
        "Entra con tu cuenta de The Market Hub y cuéntale a Claude tu idea. O empieza por la clasificación: quién va delante en el día, la semana, el mes, el año y desde el inicio."],
    ],
    build: "Crea tu bot con Claude",
    gotIt: "Entendido",
    how: "Cómo se juega →",
  },
);
