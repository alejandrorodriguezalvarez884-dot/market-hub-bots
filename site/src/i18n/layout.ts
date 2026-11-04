// The words every page shares: the top bar, the foot and the offer of the other language.
import { words } from ".";

export const layout = words(
  {
    home: "Bot League, home",
    by: "by The Market Hub",
    board: "Board",
    how: "How it works",
    rules: "Rules",
    yourBot: "Your bot",
    signIn: "Sign in",
    main: "Main",
    shareAlt: "Bot League, by The Market Hub",
    about:
      "Bot League is part of {hub}. Bots of rules, built by talking to Claude or with your own AI agent, and run on paper: no money, no broker, no orders.",
    notAdvice: "Nothing here is investment advice or a recommendation to buy or sell anything. Past returns say nothing about future ones.",
    privacy: "Privacy",
    terms: "Terms",
    language: "Language",
  },
  {
    home: "Bot League, inicio",
    by: "de The Market Hub",
    board: "Clasificación",
    how: "Cómo funciona",
    rules: "Reglas",
    yourBot: "Tu bot",
    signIn: "Entrar",
    main: "Principal",
    shareAlt: "Bot League, de The Market Hub",
    about:
      "Bot League es parte de {hub}. Bots de reglas, construidos hablando con Claude o con tu propio agente de IA, que corren en papel: sin dinero, sin bróker, sin órdenes.",
    notAdvice: "Nada de lo que hay aquí es asesoramiento de inversión ni una recomendación de comprar o vender nada. Las rentabilidades pasadas no dicen nada de las futuras.",
    privacy: "Privacidad",
    terms: "Condiciones",
    language: "Idioma",
  },
);

// The offer of the other language, written in that language (the reader may not read this one).
export const offer = {
  es: { ask: "¿Prefieres ver Bot League en español?", yes: "Ver en español", no: "No, gracias" },
  en: { ask: "Would you rather see Bot League in English?", yes: "See it in English", no: "No, thanks" },
};
