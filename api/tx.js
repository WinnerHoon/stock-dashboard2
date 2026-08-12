// Vercel 서버리스 함수 — 거래 저장 (GitHub 자동 커밋)
//
// POST /api/tx   { password, tx: {...} }
//   → transactions.json 에 거래 한 건을 추가하고 커밋합니다.
// GET  /api/tx   → 최근 거래 목록 (비밀번호 불필요, 조회만)
//
// Vercel 환경변수 3개가 필요합니다 (Settings → Environment Variables)
//   GITHUB_TOKEN  : Fine-grained PAT, 이 저장소의 Contents = Read and write
//   GITHUB_REPO   : WinnerHoon/stock-dashboard2
//   TX_PASSWORD   : 아무 비밀번호 (저장 시 확인용)
//
// 토큰은 서버에만 있고 브라우저로 내려가지 않습니다.

const FILE = "transactions.json";
const API = "https://api.github.com";

function gh(path, token, init) {
  return fetch(API + path, {
    ...init,
    headers: {
      Authorization: "Bearer " + token,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      ...(init && init.headers),
    },
  });
}

async function readFile(repo, token) {
  const r = await gh(`/repos/${repo}/contents/${FILE}`, token, { method: "GET" });
  if (!r.ok) throw new Error("파일 읽기 실패 " + r.status);
  const j = await r.json();
  const text = Buffer.from(j.content, "base64").toString("utf-8");
  return { doc: JSON.parse(text), sha: j.sha };
}

const VALID = ["open", "buy", "sell", "deposit", "withdraw", "fx", "dividend", "fee"];

function validate(tx) {
  if (!tx || typeof tx !== "object") return "거래 데이터가 없습니다";
  if (!VALID.includes(tx.type)) return "거래유형이 올바르지 않습니다: " + tx.type;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(tx.date || "")) return "날짜 형식이 올바르지 않습니다";
  if (!tx.broker) return "증권사를 선택해 주세요";

  if (["open", "buy", "sell"].includes(tx.type)) {
    if (!tx.ticker) return "종목코드를 입력해 주세요";
    if (!(Number(tx.shares) > 0)) return "수량은 0보다 커야 합니다";
    if (!(Number(tx.price) > 0)) return "가격은 0보다 커야 합니다";
    if (!["KR", "US"].includes(tx.market)) return "시장은 KR 또는 US 여야 합니다";
  } else if (tx.type === "fx") {
    if (!(Number(tx.amount) > 0)) return "환전 금액을 입력해 주세요";
    if (!(Number(tx.rate) > 0)) return "환율을 입력해 주세요";
    if (tx.from === tx.to) return "같은 통화끼리는 환전할 수 없습니다";
  } else {
    if (!(Number(tx.amount) > 0)) return "금액을 입력해 주세요";
    if (!["KRW", "USD"].includes(tx.currency)) return "통화를 선택해 주세요";
  }
  return null;
}

export default async function handler(req, res) {
  const token = process.env.GITHUB_TOKEN;
  const repo = process.env.GITHUB_REPO;
  const pw = process.env.TX_PASSWORD;

  if (req.method === "GET") {
    if (!token || !repo) {
      res.status(503).json({ ok: false, error: "서버 환경변수가 설정되지 않았습니다" });
      return;
    }
    try {
      const { doc } = await readFile(repo, token);
      const all = doc.transactions || [];
      res.setHeader("Cache-Control", "no-store");
      res.status(200).json({ ok: true, count: all.length, recent: all.slice(-30).reverse() });
    } catch (e) {
      res.status(500).json({ ok: false, error: String(e.message).slice(0, 120) });
    }
    return;
  }

  if (req.method !== "POST") {
    res.status(405).json({ ok: false, error: "POST 로 보내주세요" });
    return;
  }
  if (!token || !repo || !pw) {
    res.status(503).json({
      ok: false,
      error: "서버 환경변수(GITHUB_TOKEN, GITHUB_REPO, TX_PASSWORD)가 설정되지 않았습니다",
    });
    return;
  }

  const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : (req.body || {});
  if (body.password !== pw) {
    res.status(401).json({ ok: false, error: "비밀번호가 맞지 않습니다" });
    return;
  }

  const tx = body.tx || {};
  const bad = validate(tx);
  if (bad) {
    res.status(400).json({ ok: false, error: bad });
    return;
  }

  try {
    const { doc, sha } = await readFile(repo, token);
    const list = doc.transactions || (doc.transactions = []);
    const sameDay = list.filter(function (x) { return x.date === tx.date; }).length;

    const entry = { id: tx.date + "-" + Date.now().toString(36), seq: 200 + sameDay };
    ["date", "type", "market", "ticker", "name", "shares", "price", "fee",
     "currency", "amount", "from", "to", "rate", "broker", "memo"].forEach(function (k) {
      if (tx[k] !== undefined && tx[k] !== "" && tx[k] !== null) {
        entry[k] = ["shares", "price", "fee", "amount", "rate"].includes(k) ? Number(tx[k]) : tx[k];
      }
    });
    list.push(entry);

    const label = { open: "기초잔고", buy: "매수", sell: "매도", deposit: "입금",
                    withdraw: "출금", fx: "환전", dividend: "배당", fee: "수수료" }[tx.type];
    const what = entry.name || entry.ticker || entry.currency || "";
    const msg = `거래 추가: ${entry.date} ${label} ${what}`.trim();

    const put = await gh(`/repos/${repo}/contents/${FILE}`, token, {
      method: "PUT",
      body: JSON.stringify({
        message: msg,
        content: Buffer.from(JSON.stringify(doc, null, 1), "utf-8").toString("base64"),
        sha: sha,
      }),
    });
    if (!put.ok) {
      const t = await put.text();
      throw new Error("커밋 실패 " + put.status + " " + t.slice(0, 100));
    }
    res.status(200).json({ ok: true, entry: entry, message: msg, total: list.length });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e.message).slice(0, 160) });
  }
}
