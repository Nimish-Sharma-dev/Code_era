# SmartWallet AI

React Native (Expo Router) frontend for SmartWallet AI — a context-aware
financial copilot that combines a personal financial graph, market sentiment
signals, and a behavioral trading analyzer (TradeX) into one dashboard.

This is a **frontend-first build**: there is no FastAPI/Neo4j backend yet.
All "engines" described in the product spec run locally against a
persisted client-side store, and the `services/` layer is shaped to match
the documented API contracts exactly, so wiring up the real backend later
is a drop-in swap rather than a rewrite.

## Requirements

- **Node >= 20.19.4** (check with `node -v`). If you're on an older Node
  (this machine's default `/usr/local/bin/node` was v20.11.1), Expo's CLI
  will crash on startup with `parseEnv is not a function` because it can't
  parse `.env`. Fixes, pick one:
  - Use [nvm](https://github.com/nvm-sh/nvm) / [fnm](https://github.com/Schniz/fnm) and run `nvm use` (this repo ships an `.nvmrc`).
  - Or point at Homebrew's newer node directly: `export PATH="/usr/local/opt/node/bin:$PATH"` (if you have `brew install node` already, check with `brew list --versions node`).
- Xcode + iOS Simulator (optional, only needed for a native dev-client build) or the **Expo Go** app on your phone (easiest path, no native build required).

## Setup

```bash
npm install
cp .env.example .env   # then fill in the keys below
```

Required keys in `.env`:

| Key | Used for |
|---|---|
| `EXPO_PUBLIC_OPENROUTER_API_KEY` | Saras AI chat (OpenRouter chat completions) |
| `EXPO_PUBLIC_NEWSDATA_API_KEY` | Markets news feed (newsdata.io) |
| `EXPO_PUBLIC_OPENROUTER_MODEL` | Optional override, defaults to a free Llama 3.1 8B route |
| `EXPO_PUBLIC_API_BASE_URL` | Leave blank until the real backend exists (see Architecture) |

Without these keys the app still runs — chat falls back to a rule-based
local responder and news falls back to seeded demo headlines — but the
live integrations won't be active.

## Running it

**Easiest: Expo Go on your phone**

```bash
npm start
```

Scan the QR code with the Expo Go app (same Wi-Fi network as your
computer). No native build required.

**Native dev client (iOS simulator / device)**

```bash
npm run ios     # or: npm run android
```

Note: this project builds React Native from source on iOS
(`expo-build-properties` → `buildReactNativeFromSource: true` in
`app.json`) because the prebuilt `React-Core` artifact failed CocoaPods
validation on this Expo SDK/RN version at the time this was built. Building
from source is slower (first build can take 15-20+ minutes — CocoaPods has
to run `glog`'s autoconf `./configure` step) but is reliable. If a future
SDK patch fixes the prebuilt artifact, you can flip that flag back to
`false` for much faster builds.

## Architecture

- **`src/app/`** — Expo Router file-based routes: `(auth)` splash/login/register,
  `(onboarding)` the 4-step income → expenses → loans → wallets flow, `(tabs)`
  the 5-tab dashboard (Home, Markets, Chat, Portfolio, TradeX).
- **`src/store/useFinanceStore.ts`** — the client-side stand-in for the
  Neo4j graph: user, income sources, expenses, loans, wallets, trades, chat
  history. Persisted to `AsyncStorage` via `zustand/middleware`. Computed
  selectors (`freeCashFlow`, `burnRateRisk`, etc.) mirror the Cypher-derived
  values the spec describes.
- **`src/engines/`** — pure functions implementing the three recommendation
  engines (`riskAllocator`, `debtArbitrage`, `sentimentMomentum`) and the
  TradeX `behavioralEngine`, operating on the local store instead of a
  Cypher traversal.
- **`src/services/`** — the API layer. Each function's signature matches
  the documented REST contract (section 5 of the spec) so swapping the body
  for a real `fetch(`${API_BASE_URL}/api/v1/...`)` call is a contained
  change per file:
  - `auth.ts`, `wallet.ts` — local store reads/writes (will become real
    `/auth/*` and `/user/*` endpoint calls).
  - `market.ts` — assembles the unified predictions payload from the local
    engines (will become `/market/predictions` etc.).
  - `chat.ts` — builds the same "contextual subgraph" snapshot the spec
    describes and calls OpenRouter directly from the client for now
    (will become `/chat/message`, proxied server-side).
  - `tradex.ts` — trade journal CSV/JSON parsing + behavioral scoring
    (will become `/tradex/*`).
  - `binance.ts` — a real, no-key-required Binance public WebSocket feed
    for live BTC/ETH prices (mirrors `binance_stream.py` from the spec,
    just running client-side instead of as a backend worker).
  - `newsdata.ts` / `sentiment.ts` — real news from newsdata.io, scored by
    a financial sentiment lexicon as a stand-in for the spec's FinBERT
    pipeline (running an actual HuggingFace model isn't feasible
    on-device). Falls back to seeded headlines on any failure.
- **`src/constants/theme.ts`** — design tokens lifted directly from the
  Stitch design system (`smartwallet_ai_tradex/DESIGN.md`): colors,
  typography, radii, spacing.

## Known limitations / next steps

- No backend yet — everything above runs locally. Section "Architecture"
  lists exactly what to swap when `EXPO_PUBLIC_API_BASE_URL` is set.
- Sentiment scoring is a lexicon heuristic, not the real `ProsusAI/finbert`
  model — good enough for demoing the UI, not for production signal
  quality.
- App icon / splash image are still Expo's defaults — only the in-app
  splash/auth screen is branded.
- No automated test suite yet.
