// The whole leaderboard (views/Board.astro): every bot over a period, ranked, with the index for
// reference, and the reader's own place when they play.
import { words } from ".";
import type { Period } from "../lib/types";

export const board = words(
  {
    title: "The leaderboard · Bot League",
    description: "Every member's bot, run on paper and ranked over the day, the week, the month, the year and since it started, against the S&P 500.",
    kicker: "The leaderboard",
    h1: "Who's ahead",
    loading: "loading",
    lede: "Every bot plays on the same closes from its first one, under its player's first name. The S&P 500 is there to compare against and is never ranked.",
    // Written by the page's script.
    toClose: (d: string) => `to the close of ${d}`,
    starting: "starting",
    startsNext: "starts next close",
    bot: "Bot",
    sinceStart: "Since start",
    running: "Playing for",
    largest: "Largest holdings",
    joinTitle: "Join the game",
    joinBody: "Tell Claude how you would pick stocks. Your bot plays from the next close.",
    yourPlace: "Your place",
    placeOf: (rank: string, of: number) => `${rank} of ${of}`,
    notPlaced: "Not ranked here yet",
    over: { "1d": "over the day", "1w": "over the week", "1m": "over the month", "1y": "over the year", all: "since it started" } as Record<Period, string>,
    toYourBot: "Your bot →",
    build: "Build your bot",
    moving: "moving the bots on to the last close…",
    unread: "The board could not be read just now. Try again in a minute.",
  },
  {
    title: "La clasificación · Bot League",
    description:
      "Los bots de todos los miembros, ejecutados en papel y clasificados por el día, la semana, el mes, el año y desde que empezaron, frente al S&P 500.",
    kicker: "La clasificación",
    h1: "Quién va delante",
    loading: "cargando",
    lede: "Todos los bots juegan con los mismos cierres desde el primero, con el nombre de pila de su jugador. El S&P 500 está para comparar y nunca ocupa un puesto.",
    toClose: (d: string) => `al cierre del ${d}`,
    starting: "empezando",
    startsNext: "empieza al próximo cierre",
    bot: "Bot",
    sinceStart: "Desde el inicio",
    running: "En juego",
    largest: "Mayores posiciones",
    joinTitle: "Únete al juego",
    joinBody: "Cuéntale a Claude cómo elegirías acciones. Tu bot juega desde el próximo cierre.",
    yourPlace: "Tu puesto",
    placeOf: (rank: string, of: number) => `${rank} de ${of}`,
    notPlaced: "Aún sin puesto aquí",
    over: { "1d": "en el día", "1w": "en la semana", "1m": "en el mes", "1y": "en el año", all: "desde que empezó" },
    toYourBot: "Tu bot →",
    build: "Crea tu bot",
    moving: "llevando los bots hasta el último cierre…",
    unread: "Ahora mismo no se puede leer la clasificación. Inténtalo de nuevo en un minuto.",
  },
);
