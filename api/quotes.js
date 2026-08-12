// Vercel 서버리스 함수 — 실시간 시세 프록시
//
// 브라우저에서 Yahoo Finance 를 직접 부르면 CORS 에 막힙니다.
// 이 함수가 서버에서 대신 불러다 주기 때문에 페이지를 열 때마다 최신 시세를 받을 수 있습니다.
//
//   GET /api/quotes?t=000660.KS,NVDA,KRW=X
//   → { "ok": true, "at": "...", "quotes": { "000660.KS": {price, prev, chg, ...}, ... } }
//
// 의존성 없음 (Node 18+ 내장 fetch 사용)

const YF = "https://query1.finance.yahoo.com/v8/finance/chart/";
const UA = "Mozilla/5.0 (compatible; stock-dashboard/1.0)";
const MAX_TICKERS = 40;

async function one(sym) {
  const url = YF + encodeURIComponent(sym) + "?range=5d&interval=1d";
  const r = await fetch(url, { headers: { "User-Agent": UA, Accept: "application/json" } });
  if (!r.ok) throw new Error("HTTP " + r.status);
  const j = await r.json();
  const res = j && j.chart && j.chart.result && j.chart.result[0];
  if (!res) throw new Error("no result");
  const m = res.meta || {};
  const price = m.regularMarketPrice;
  const prev = m.chartPreviousClose != null ? m.chartPreviousClose : (m.previousClose != null ? m.previousClose : price);
  if (price == null) throw new Error("no price");
  return {
    price: price,
    prev: prev,
    chg: prev ? +(((price - prev) / prev) * 100).toFixed(2) : null,
    currency: m.currency || null,
    high52: m.fiftyTwoWeekHigh != null ? m.fiftyTwoWeekHigh : null,
    low52: m.fiftyTwoWeekLow != null ? m.fiftyTwoWeekLow : null,
    marketTime: m.regularMarketTime ? m.regularMarketTime * 1000 : null,
    name: m.shortName || m.longName || null,
  };
}

export default async function handler(req, res) {
  const raw = ((req.query && req.query.t) || "").toString();
  const tickers = Array.from(new Set(
    raw.split(",").map(function (s) { return s.trim(); }).filter(Boolean)
  )).slice(0, MAX_TICKERS);

  if (!tickers.length) {
    res.status(400).json({ ok: false, error: "t 파라미터에 티커를 콤마로 구분해 넣어주세요" });
    return;
  }

  const settled = await Promise.allSettled(tickers.map(one));
  const quotes = {};
  const failed = [];
  settled.forEach(function (s, i) {
    if (s.status === "fulfilled") {
      quotes[tickers[i]] = s.value;
    } else {
      failed.push({
        ticker: tickers[i],
        error: String((s.reason && s.reason.message) || s.reason).slice(0, 80),
      });
    }
  });

  // 시세는 잠깐만 캐시해서 새로고침 연타 시 야후를 과하게 부르지 않게 합니다
  res.setHeader("Cache-Control", "public, s-maxage=30, stale-while-revalidate=90");
  res.status(200).json({
    ok: true,
    at: new Date().toISOString(),
    count: Object.keys(quotes).length,
    quotes: quotes,
    failed: failed,
  });
}
