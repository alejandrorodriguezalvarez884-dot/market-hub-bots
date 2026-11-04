// The whole board (views/Board.astro): every bot over a period, ranked, with the index for reference.
import { words } from ".";

export const board = words(
  {
    title: "The board · Bot League",
    description: "Every member's bot, run on paper and ranked over the day, the week, the month, the year and since it started, against the S&P 500.",
    kicker: "The board",
    h1: "Every bot, ranked from its first close",
    loading: "loading",
    lede: "A bot shows in a period once it has run that long, under the first name of its player. The S&P 500 is on the board for reference and is never ranked.",
    // Written by the page's script.
    toClose: (d: string) => `to the close of ${d}`,
    starting: "starting",
    startsNext: "starts next close",
    bot: "Bot",
    sinceStart: "Since start",
    running: "Running",
    largest: "Largest holdings",
    joinTitle: "Your bot could be on this board",
    joinBody: "Tell Claude how you would pick stocks. It runs from the next close.",
    build: "Build your bot",
    moving: "moving the bots on to the last close…",
    unread: "The board could not be read just now. Try again in a minute.",
  },
  {
    title: "La clasificación · Bot League",
    description:
      "Los bots de todos los miembros, ejecutados en papel y clasificados por el día, la semana, el mes, el año y desde que empezaron, frente al S&P 500.",
    kicker: "La clasificación",
    h1: "Todos los bots, clasificados desde su primer cierre",
    loading: "cargando",
    lede: "Un bot aparece en un periodo cuando lleva ese tiempo en marcha, con el nombre de pila de su jugador. El S&P 500 está en la clasificación como referencia y nunca ocupa un puesto.",
    toClose: (d: string) => `al cierre del ${d}`,
    starting: "empezando",
    startsNext: "empieza al próximo cierre",
    bot: "Bot",
    sinceStart: "Desde el inicio",
    running: "En marcha",
    largest: "Mayores posiciones",
    joinTitle: "Tu bot podría estar en esta clasificación",
    joinBody: "Cuéntale a Claude cómo elegirías acciones. Compite desde el próximo cierre.",
    build: "Crea tu bot",
    moving: "llevando los bots hasta el último cierre…",
    unread: "Ahora mismo no se puede leer la clasificación. Inténtalo de nuevo en un minuto.",
  },
);
