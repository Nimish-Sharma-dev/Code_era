// Central place every service reads API config from. Values come from
// EXPO_PUBLIC_* env vars (see .env.example) which Expo inlines at build
// time — no extra babel plugin needed on SDK 56+.

export const Config = {
  openRouterApiKey: process.env.EXPO_PUBLIC_OPENROUTER_API_KEY ?? '',
  openRouterModel:
    process.env.EXPO_PUBLIC_OPENROUTER_MODEL ?? 'meta-llama/llama-3.1-8b-instruct:free',
  newsdataApiKey: process.env.EXPO_PUBLIC_NEWSDATA_API_KEY ?? '',
  apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL ?? '',
} as const;

export const hasOpenRouter = Config.openRouterApiKey.length > 0;
export const hasNewsdata = Config.newsdataApiKey.length > 0;
export const hasBackend = Config.apiBaseUrl.length > 0;
