import { Config, hasNewsdata } from '@/constants/config';
import { SEED_NEWS } from '@/data/seed';
import { genId } from '@/utils/id';
import { NewsNode } from '@/types';
import { labelForScore, scoreHeadline } from './sentiment';

// Stands in for app/collectors/news_poller.py (Marketaux, per the spec) —
// the api.txt key on hand is for newsdata.io, so that's the live source
// here. Falls back to the pre-scored seed headlines on any failure so the
// Markets screen never renders empty (mirrors the spec's "demo never
// depends on live quota" mitigation).

const TICKER_QUERY: Record<string, string> = {
  NVDA: 'Nvidia',
  AAPL: 'Apple',
  MSFT: 'Microsoft',
  GOOGL: 'Google OR Alphabet',
  TSLA: 'Tesla',
  META: 'Meta',
  BTC: 'Bitcoin',
  ETH: 'Ethereum',
};

function extractTickers(title: string): string[] {
  const found: string[] = [];
  for (const [ticker, query] of Object.entries(TICKER_QUERY)) {
    const names = query.split(' OR ');
    if (names.some((n) => title.toLowerCase().includes(n.toLowerCase()))) {
      found.push(ticker);
    }
  }
  return found;
}

interface NewsdataArticle {
  article_id: string;
  title: string;
  link: string;
  source_id: string;
  pubDate: string;
}

export async function fetchLiveNews(ticker?: string): Promise<NewsNode[]> {
  if (!hasNewsdata) return SEED_NEWS;

  const query = ticker ? TICKER_QUERY[ticker] ?? ticker : 'stocks OR crypto OR markets';
  const url = `https://newsdata.io/api/1/news?apikey=${Config.newsdataApiKey}&q=${encodeURIComponent(
    query,
  )}&language=en&category=business`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`newsdata HTTP ${res.status}`);
    const json = await res.json();
    const articles: NewsdataArticle[] = json?.results ?? [];
    if (articles.length === 0) return SEED_NEWS;

    return articles.slice(0, 20).map((article) => {
      const score = scoreHeadline(article.title);
      return {
        id: article.article_id || genId('news'),
        headline: article.title,
        source: article.source_id || 'newsdata.io',
        url: article.link,
        publishedAt: article.pubDate ? new Date(article.pubDate).toISOString() : new Date().toISOString(),
        tickers: ticker ? [ticker] : extractTickers(article.title),
        finbertScore: score,
        label: labelForScore(score),
      };
    });
  } catch {
    return SEED_NEWS;
  }
}
