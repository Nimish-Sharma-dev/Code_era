import { Config, hasOpenRouter } from '@/constants/config';

// Thin client for OpenRouter's chat completions endpoint. This stands in
// for the spec's Groq/Mistral/Sarvam calls — see README for the swap plan
// once the FastAPI backend (and its own LLM provider) is live.

export interface ChatTurn {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export async function openRouterChat(messages: ChatTurn[], opts?: { temperature?: number }): Promise<string> {
  if (!hasOpenRouter) {
    throw new Error('OPENROUTER_NOT_CONFIGURED');
  }

  const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${Config.openRouterApiKey}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': 'https://smartwallet.ai',
      'X-Title': 'SmartWallet AI',
    },
    body: JSON.stringify({
      model: Config.openRouterModel,
      messages,
      temperature: opts?.temperature ?? 0.4,
    }),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(`OPENROUTER_HTTP_${response.status}: ${text}`);
  }

  const json = await response.json();
  const content = json?.choices?.[0]?.message?.content;
  if (typeof content !== 'string') {
    throw new Error('OPENROUTER_EMPTY_RESPONSE');
  }
  return content;
}
