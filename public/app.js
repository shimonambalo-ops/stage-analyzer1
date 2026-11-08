/* מסלול – אבחון שלב חברה */
(() => {
  'use strict';

  const C = {
    ink: '#14213D', rule: '#DCE3EC', muted: '#5B6B82', green: '#1A936F', amber: '#C98A00', red: '#C8102E',
    grid: '#EEF2F6', font: "'IBM Plex Sans Hebrew', 'Segoe UI', sans-serif",
  };
  const EXAMPLES = ['ASTS', 'QS', 'TE', 'LMND', 'PLTR', 'SOFI', 'HOOD', 'KO'];
  const STATIONS = ['היכרות', 'צמיחה', 'בשלות', 'התנערות', 'דעיכה'];
  const POS = { introduction: 0, growth: 1, mature: 2, shakeout: 3, decline: 4, unknown: 0 };
  const REC_HE = { strong_buy: 'קנייה חזקה', buy: 'קנייה', hold: 'החזק', underperform: 'תשואת חסר', sell: 'מכירה', strong_sell: 'מכירה חזקה', none: '—' };

  const EXPLAIN = {
    mcap: 'שווי כל המניות של החברה בשוק: מחיר המניה כפול מספר המניות.',
    pe: 'מחיר המניה חלקי הרווח למניה ב-12 החודשים האחרונים – כמה שנות רווח משלמים על המניה. אין לו משמעות כשהחברה מפסידה.',
    fpe: 'כמו מכפיל רווח, אבל לפי תחזית הרווח של האנליסטים לשנה הקרובה.',
    ps: 'שווי השוק חלקי ההכנסות השנתיות. שימושי במיוחד בחברות צמיחה שעדיין מפסידות.',
    pfcf: 'שווי השוק חלקי התזרים החופשי השנתי – כמה שנים של מזומן פנוי משלמים על החברה.',
    pb: 'שווי השוק חלקי ההון העצמי בספרים.',
    eps: 'הרווח הנקי השנתי חלקי מספר המניות.',
    div: 'הדיבידנד השנתי כאחוז ממחיר המניה.',
    rev: 'סך ההכנסות ב-12 החודשים האחרונים (4 רבעונים), והשינוי לעומת 12 החודשים שלפניהם.',
    ni: 'מה שנשאר מההכנסות אחרי כל ההוצאות, הריבית והמיסים, ב-12 החודשים האחרונים.',
    nm: 'רווח נקי חלקי הכנסות: כמה סנטים של רווח נשארים מכל דולר הכנסה.',
    gm: 'הכנסות פחות עלות המכר, חלקי הכנסות – כמה רווחי המוצר עצמו, לפני הוצאות פיתוח, שיווק והנהלה.',
    roe: 'רווח נקי חלקי ההון העצמי: כמה החברה מרוויחה על הכסף של בעלי המניות.',
    fcf: 'המזומן שהפעילות מייצרת, פחות השקעות ברכוש קבוע. שלילי = החברה שורפת מזומנים.',
    liquid: 'מזומן, פיקדונות וניירות ערך סחירים (בעיקר אג"ח) – הכסף שזמין לחברה.',
    debt: 'הלוואות ואג"ח שהחברה גייסה, כולל אג"ח להמרה. לא כולל התחייבויות חכירה.',
    beta: 'כמה המניה זזה ביחס לשוק כולו. 1 = כמו השוק, 2 = פי שניים מהשוק.',
    vol: 'סטיית התקן השנתית של התשואות היומיות בשנה האחרונה. מעל 50% = מניה תנודתית מאוד.',
    avgvol: 'ממוצע המניות שנסחרות ביום.',
    shares: 'מספר המניות של החברה, לפי הדוח האחרון.',
    dil: 'בכמה גדל מספר המניות בשנה האחרונה. גידול = כל מניה מחזיקה חלק קטן יותר מהחברה.',
    short: 'אחוז מהמניות הצפות שמושאלות למכירה בחסר – כלומר הימורים על ירידה.',
    inst: 'אחוז מהמניות שמוחזקות בידי גופים מוסדיים: קרנות, בנקים וחברות ביטוח.',
    insider: 'אחוז מהמניות שמוחזקות בידי מנהלים, מייסדים ובעלי עניין.',
    risk: 'ציון 0–100 שמשלב את השלב של החברה, הקופה, החוב, הדילול, מגמת ההפסדים, התמחור והתנודתיות. הפירוט ב"סימני אזהרה" ו"נקודות חוזק".',
    scores: 'ציונים שלנו בסולם 1–10, לפי הנתונים מהדוחות. צמיחה – קצב גידול ההכנסות; רווחיות – שולי רווח ותזרים; חוסן – קופה, חוב ודילול; תמחור – מכפילים (גבוה = זול).',
    edge: 'אחד משלושת התזרימים קרוב לאפס, והמגמה ב-4 הרבעונים האחרונים צפויה להפוך את הסימן שלו – ואז, לפי Dickinson, משתנה גם השלב.',
    dickinson: 'מודל אקדמי (Dickinson, The Accounting Review, 2011): השלב נקבע לפי הסימן של שלושת חלקי דוח תזרים המזומנים ב-12 החודשים האחרונים – פעילות שוטפת, השקעות ומימון. 8 צירופים → 5 שלבים. ההסבר המלא בלשונית "אמינות הנתונים".',
    damodaran: 'מחזור החיים של Aswath Damodaran (NYU): שישה שלבים לפי צמיחת ההכנסות והרווחיות, וכל שלב מתמחרים אחרת. Damodaran מתאר את השלבים במילים – הספים המספריים הם התרגום שלנו.',
    cfo: 'המזומן שהפעילות העסקית מייצרת (חיובי) או שורפת (שלילי) – לפני השקעות ומימון.',
    cfi: 'השקעות ברכוש קבוע, רכישות וכדומה (בדרך כלל שלילי). חיובי = החברה מוכרת נכסים. מנוטרל מקנייה ומכירה של ניירות ערך סחירים.',
    cff: 'כסף שהחברה גייסה (חיובי – הנפקות, הלוואות) או החזירה למשקיעים (שלילי – דיבידנד, קנייה עצמית, החזר חוב).',
  };
  const tipBtn = (key) => (EXPLAIN[key] ? `<button type="button" class="i" data-tip="${key}" aria-label="הסבר">?</button>` : '');
  function verdict(kind, v) {
    if (v === null || v === undefined || Number.isNaN(v)) return '';
    const V = (t, c) => `<span class="verdict ${c}">${t}</span>`;
    switch (kind) {
      case 'pe': return v < 15 ? V('זול', 'g') : v < 25 ? V('סביר', 'n') : v < 40 ? V('יקר', 'a') : V('יקר מאוד', 'r');
      case 'ps': return v < 2 ? V('זול', 'g') : v < 6 ? V('סביר', 'n') : v < 15 ? V('יקר', 'a') : V('יקר מאוד', 'r');
      case 'pfcf': return v < 15 ? V('זול', 'g') : v < 30 ? V('סביר', 'n') : v < 60 ? V('יקר', 'a') : V('יקר מאוד', 'r');
      case 'dil': return v > 0.08 ? V('דילול כבד', 'r') : v > 0.03 ? V('דילול', 'a') : v < -0.01 ? V('רכישה עצמית', 'g') : V('יציב', 'n');
      case 'vol': return v > 0.6 ? V('תנודתית מאוד', 'r') : v > 0.35 ? V('תנודתית', 'a') : V('רגילה', 'n');
      case 'nm': return v < 0 ? V('הפסדית', 'r') : v < 0.05 ? V('דקים', 'a') : v < 0.15 ? V('סבירים', 'n') : V('גבוהים', 'g');
      case 'growth': return !Number.isFinite(v) ? V('מאפס', 'g') : v < 0 ? V('ירידה', 'r') : v < 0.08 ? V('איטית', 'n') : v < 0.2 ? V('מתונה', 'n') : V('מהירה', 'g');
      case 'short': return v > 0.15 ? V('גבוה מאוד', 'r') : v > 0.08 ? V('גבוה', 'a') : '';
      case 'runway': return v < 12 ? V('קצר', 'r') : v < 24 ? V('בינוני', 'a') : V('ארוך', 'g');
      case 'fcf': return v < 0 ? V('שורפת מזומן', 'r') : V('מייצרת מזומן', 'g');
      case 'beta': return v > 1.5 ? V('תנודתית מהשוק', 'a') : v < 0.8 ? V('יציבה מהשוק', 'n') : '';
      default: return '';
    }
  }

  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const bad = (x) => x === null || x === undefined || Number.isNaN(x) || !Number.isFinite(x);
  const n = (s) => `<span class="num">${s}</span>`;

  // ---------------- פורמט ----------------
  function money(x, cur = 'USD', dec) {
    if (bad(x)) return '—';
    const sym = cur === 'USD' ? '$' : cur + ' ';
    const a = Math.abs(x), sg = x < 0 ? '-' : '';
    const units = [[1e12, 'T', 2], [1e9, 'B', 2], [1e6, 'M', 1], [1e3, 'K', 0]];
    for (const [d, u, p] of units) if (a >= d) return n(`${sg}${sym}${(a / d).toFixed(dec ?? p)}${u}`);
    return n(`${sg}${sym}${a.toFixed(0)}`);
  }
  function moneyPlain(x) {
    if (bad(x)) return '';
    const a = Math.abs(x), sg = x < 0 ? '-' : '';
    for (const [d, u] of [[1e12, 'T'], [1e9, 'B'], [1e6, 'M'], [1e3, 'K']]) if (a >= d) return `${sg}$${+(a / d).toFixed(1)}${u}`;
    return `${sg}$${a.toFixed(0)}`;
  }
  function pct(x, plus = true) {
    if (x === null || x === undefined || Number.isNaN(x)) return '—';
    if (!Number.isFinite(x)) return 'מאפס';
    const d = Math.abs(x) < 0.1 ? 1 : 0;
    const s = (x * 100).toFixed(d) + '%';
    return n(plus && x > 0 ? '+' + s : s);
  }
  const cls = (x) => (bad(x) ? '' : x >= 0 ? 'pos' : 'neg');
  const num = (x, d = 1) => (bad(x) ? '—' : n(x.toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d })));
  const big = (x) => (bad(x) ? '—' : n(Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(x)));
  const months = (x) => (bad(x) ? '—' : x >= 120 ? '10+ שנים' : `${n(Math.round(x))} חודשים`);
  function dmy(iso) {
    if (!iso) return '—';
    const [y, m, d] = iso.slice(0, 10).split('-');
    return n(`${d}.${m}.${y}`);
  }
  function relTime(iso) {
    if (!iso) return '';
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 3600) return `לפני ${Math.max(1, Math.round(s / 60))} דקות`;
    if (s < 86400) { const h = Math.round(s / 3600); return h === 1 ? 'לפני שעה' : `לפני ${h} שעות`; }
    const d = Math.round(s / 86400);
    if (d === 1) return 'אתמול';
    if (d < 30) return `לפני ${d} ימים`;
    return new Date(iso).toLocaleDateString('he-IL');
  }

  // ---------------- מסלול ----------------
  function trackHTML(stage, color, edges = []) {
    const pos = POS[stage] ?? 0;
    const off = stage === 'unknown';
    let st = '';
    STATIONS.forEach((nm, i) => {
      const c = (i <= pos ? 'past ' : '') + (i === 0 || i === STATIONS.length - 1 ? 'end' : '');
      st += `<div class="station ${c}" style="right:${(i / 4) * 100}%;color:${color}"><div class="dot"></div><div class="nm">${nm}</div></div>`;
    });
    let edge = '';
    const e = edges.find((x) => POS[x.to] !== undefined && POS[x.to] !== pos);
    if (e) {
      const a = pos / 4 * 100, b = POS[e.to] / 4 * 100;
      const lo = Math.min(a, b), hi = Math.max(a, b);
      edge = `<div class="edge ${b > a ? 'toL' : 'toR'}" style="right:${lo}%;width:${hi - lo}%;color:${color};border-color:${color}"></div>`;
    }
    return `<div class="track">
      <div class="line"></div>${off ? '' : `<div class="fill" style="width:${(pos / 4) * 100}%;background:${color}"></div>`}
      ${edge}${st}
      <div class="marker" style="right:${(pos / 4) * 100}%;color:${color}"><div class="pin"></div></div>
    </div>`;
  }

  function gaugeSVG(score) {
    const col = score < 25 ? C.green : score < 50 ? C.amber : C.red;
    const R = 90, cx = 110, cy = 105;
    const pt = (v) => { const a = Math.PI * (1 - v / 100); return [cx + R * Math.cos(a), cy - R * Math.sin(a)]; };
    const [x1, y1] = pt(0), [x2, y2] = pt(100), [xv, yv] = pt(score);
    return `<svg class="gauge" viewBox="0 0 220 125" role="img" aria-label="רמת סיכון ${score} מתוך 100">
      <path d="M${x1} ${y1} A${R} ${R} 0 0 1 ${x2} ${y2}" fill="none" stroke="#E7ECF2" stroke-width="16" stroke-linecap="round"/>
      ${score > 0 ? `<path d="M${x1} ${y1} A${R} ${R} 0 0 1 ${xv.toFixed(1)} ${yv.toFixed(1)}" fill="none" stroke="${col}" stroke-width="16" stroke-linecap="round"/>` : ''}
      <text x="${cx}" y="${cy - 8}" text-anchor="middle" font-size="44" font-weight="700" fill="${C.ink}" font-family="${C.font}">${score}</text>
      <text x="${cx}" y="${cy + 14}" text-anchor="middle" font-size="12" fill="${C.muted}" font-family="${C.font}">מתוך 100</text>
    </svg>`;
  }

  // ---------------- חיפוש + השלמה אוטומטית ----------------
  let TICKERS = null, sugIdx = -1;
  async function loadTickers() {
    if (TICKERS) return TICKERS;
    try {
      const r = await fetch('/api/tickers');
      TICKERS = (await r.json()).tickers || [];
    } catch { TICKERS = []; }
    return TICKERS;
  }
  function renderSuggest(q) {
    const ul = $('#suggest');
    q = q.trim().toUpperCase();
    if (!q || !TICKERS) { ul.hidden = true; return; }
    const starts = [], has = [];
    for (const [t, name] of TICKERS) {
      if (t.startsWith(q)) starts.push([t, name]);
      else if (q.length >= 3 && name.toUpperCase().includes(q)) has.push([t, name]);
      if (starts.length >= 8) break;
    }
    starts.sort((a, b) => a[0].length - b[0].length);
    const list = starts.concat(has).slice(0, 8);
    sugIdx = -1;
    ul.innerHTML = list.map(([t, nm], i) => `<li role="option" data-t="${esc(t)}" id="sg${i}"><span class="t">${esc(t)}</span><span class="n">${esc(nm)}</span></li>`).join('');
    ul.hidden = !list.length;
  }
  function moveSuggest(d) {
    const items = [...$('#suggest').children];
    if (!items.length) return;
    sugIdx = (sugIdx + d + items.length) % items.length;
    items.forEach((li, i) => li.setAttribute('aria-selected', i === sugIdx));
  }
  function initSearch() {
    const q = $('#q');
    q.addEventListener('focus', loadTickers, { once: true });
    q.addEventListener('input', async () => { await loadTickers(); renderSuggest(q.value); });
    q.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); moveSuggest(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); moveSuggest(-1); }
      else if (e.key === 'Escape') { $('#suggest').hidden = true; }
    });
    $('#suggest').addEventListener('mousedown', (e) => {
      const li = e.target.closest('li'); if (!li) return;
      e.preventDefault(); go(li.dataset.t);
    });
    q.addEventListener('blur', () => setTimeout(() => ($('#suggest').hidden = true), 120));
    $('#search').addEventListener('submit', (e) => {
      e.preventDefault();
      const items = [...$('#suggest').children];
      const t = sugIdx >= 0 && items[sugIdx] ? items[sugIdx].dataset.t : q.value;
      if (t.trim()) go(t);
    });
    $('#examples').innerHTML = EXAMPLES.map((t) => `<button class="pill" data-t="${t}">${t}</button>`).join('');
    $('#examples').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) go(b.dataset.t); });
    $('#heroTrack').innerHTML = trackHTML('growth_loss', C.ink);
    $('#brand').addEventListener('click', (e) => { e.preventDefault(); history.pushState({}, '', '/'); route(); });
  }

  function go(t) {
    t = t.trim().toUpperCase();
    $('#q').value = t;
    $('#suggest').hidden = true;
    history.pushState({ t }, '', `/${encodeURIComponent(t)}`);
    route();
  }

  function currentTicker() {
    const legacy = new URLSearchParams(location.search).get('t');  // קישורים ישנים בסגנון ?t=PLTR
    if (legacy) { history.replaceState({}, '', `/${encodeURIComponent(legacy.toUpperCase())}`); return legacy; }
    const p = decodeURIComponent(location.pathname.replace(/^\/+|\/+$/g, ''));
    return /^[A-Za-z0-9.\-]{1,10}$/.test(p) ? p : null;
  }

  function route() {
    const t = currentTicker();
    if (!t) {
      $('#home').hidden = false; $('#view').hidden = true;
      document.title = 'מסלול – אבחון שלב חברה';
      return;
    }
    $('#home').hidden = true; $('#view').hidden = false;
    $('#q').value = t.toUpperCase();
    load(t.toUpperCase());
  }

  // ---------------- טעינה ----------------
  let reqId = 0;
  const charts = [];
  async function load(t) {
    const id = ++reqId;
    charts.splice(0).forEach((c) => c.dispose());
    window.scrollTo({ top: 0 });
    $('#status').innerHTML = '';
    $('#mast').innerHTML = `<div class="mast"><div class="skel" style="width:64px;height:64px;background-color:#2a3a60"></div>
      <div><div style="font:900 2rem var(--serif)">${esc(t)}</div><div class="sub" style="color:#AEB9C9">מושך את הדוחות מ-SEC…</div></div></div>`;
    ['#s-overview', '#s-chart', '#s-stats', '#s-fin', '#s-news', '#s-profile', '#s-verify'].forEach((s) => ($(s).innerHTML = `<div class="skel" style="height:180px"></div>`));

    const pA = fetch(`/api/analyze?t=${encodeURIComponent(t)}`).then((r) => r.json()).catch(() => ({ error: 'לא הצלחתי להתחבר לשרת. נסה שוב בעוד רגע.' }));
    const pE = fetch(`/api/extras?t=${encodeURIComponent(t)}`).then((r) => r.json()).catch(() => ({}));

    const A = await pA;
    if (id !== reqId) return;
    if (A.error) {
      $('#mast').innerHTML = `<div class="error-box"><h2 class="h3">${esc(t)}</h2><p>${esc(A.error)}</p>
        <p class="muted">אפשר לנסות טיקר אחר, או לבחור מהרשימה שנפתחת בזמן ההקלדה.</p></div>`;
      ['#s-overview', '#s-chart', '#s-stats', '#s-fin', '#s-news', '#s-profile', '#s-verify'].forEach((s) => ($(s).innerHTML = ''));
      $('#subnav').hidden = true;
      return;
    }
    $('#subnav').hidden = false;
    document.title = `${A.ticker} · ${A.stage_he} – מסלול`;
    renderMast(A, null);
    renderOverview(A);
    renderChart(A);
    renderStats(A, null);
    renderFin(A);
    renderVerify(A, null);
    $('#s-news').innerHTML = `<h2>עדכונים אחרונים</h2><div class="skel" style="height:220px"></div>`;
    $('#s-profile').innerHTML = `<h2>על החברה</h2><div class="skel" style="height:160px"></div>`;

    const E = await pE;
    if (id !== reqId) return;
    renderMast(A, E);
    renderStats(A, E);
    renderNews(A, E);
    renderProfile(A, E);
    renderVerify(A, E);
    initSubnav();
  }

  // ---------------- כותרת ----------------
  function renderMast(A, E) {
    const P = (E && E.profile) || {};
    const S = (E && E.stats) || {};
    const chips = [`<span class="chip tk">${esc(A.ticker)}</span>`];
    if (P.exchange) chips.push(`<span class="chip">${esc(P.exchange)}</span>`);
    if (P.sector_he) chips.push(`<span class="chip">${esc(P.sector_he)}</span>`);
    if (P.industry) chips.push(`<span class="chip">${esc(P.industry)}</span>`);
    else if (P.sic) chips.push(`<span class="chip">${esc(P.sic)}</span>`);
    if (P.country) chips.push(`<span class="chip">${esc(P.country)}</span>`);

    let px = '';
    if (!bad(A.price)) {
      const ch = A.change_1d;
      let r52 = '';
      if (!bad(S.fiftyTwoWeekLow) && !bad(S.fiftyTwoWeekHigh) && S.fiftyTwoWeekHigh > S.fiftyTwoWeekLow) {
        const p = Math.min(100, Math.max(0, (A.price - S.fiftyTwoWeekLow) / (S.fiftyTwoWeekHigh - S.fiftyTwoWeekLow) * 100));
        r52 = `<div class="range52"><div class="sub">טווח 52 שבועות</div><div class="bar"><div class="dot" style="left:${p}%"></div></div>
          <div class="ends"><span>$${S.fiftyTwoWeekLow.toFixed(2)}</span><span>$${S.fiftyTwoWeekHigh.toFixed(2)}</span></div></div>`;
      }
      px = `<div class="mast-col"><div class="px num">$${A.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        ${bad(ch) ? '' : `<div class="${ch >= 0 ? 'up' : 'down'}">${pct(ch)} ביום האחרון</div>`}
        <div class="sub">שווי שוק ${money(A.market_cap)}</div>${r52}</div>`;
    }
    let nx = '';
    if (E && E.next_report && E.next_report.date) {
      const d = Math.round((new Date(E.next_report.date) - new Date(new Date().toDateString())) / 86400000);
      const cd = d > 1 ? `בעוד ${n(d)} ימים` : d === 1 ? 'מחר' : d === 0 ? 'היום' : 'צפוי בקרוב';
      nx = `<div class="mast-col next"><div class="sub">הדוח הבא</div><div class="d">${dmy(E.next_report.date)}</div>
        <div class="cd">${cd}</div><div class="sub" style="margin-top:4px">${esc(E.next_report.source)}</div></div>`;
    } else if (!E) {
      nx = `<div class="mast-col next"><div class="sub">הדוח הבא</div><div class="skel" style="height:26px;width:110px;margin-top:6px;background-color:#2a3a60"></div></div>`;
    }
    const name = P.name || A.name;
    $('#mast').innerHTML = `<div class="mast">
      <div class="mono" style="background:${A.stage_color}">${esc(A.ticker.slice(0, 5))}</div>
      <div><h1><bdi>${esc(name)}</bdi></h1><div class="chips">${chips.join('')}</div></div>
      ${px}${nx}</div>`;
    $('#status').innerHTML = (A.warnings || []).map((w) => `<div class="notice">${esc(w)}</div>`).join('');
  }

  // ---------------- סקירה ----------------
  function renderOverview(A) {
    const L = A.latest, color = A.stage_color;
    const edges = (A.edges || []).map((e) => {
      const col = A.stages[e.to] ? A.stages[e.to].color : color;
      const eta = e.eta ? `לפי המגמה: בעוד כ-${n(e.eta)} ${A.period_months === 12 ? 'שנים' : 'רבעונים'}` : '';
      return `<div class="edgebox" style="border-inline-start-color:${col}"><b>על הסף: ${esc(e.title)} ← שלב ${esc(e.to_he)}${tipBtn('edge')}</b>
        <div>${esc(e.text)}</div>${eta ? `<div class="eta">${eta}</div>` : ''}</div>`;
    }).join('');

    // רכיבי Dickinson
    const cf = [
      ['תזרים מפעילות שוטפת', L.ocf_ttm, 'cfo'],
      ['תזרים מהשקעות', L.cfi_ttm, 'cfi'],
      ['תזרים ממימון', L.cff_ttm, 'cff'],
    ].map(([lbl, v, k]) => {
      const sg = bad(v) ? '' : v > 0 ? '+' : '−';
      return `<div class="cf"><div class="cf-l">${lbl}${tipBtn(k)}</div><div class="cf-v">${money(v, A.currency)}</div>
        <span class="sign ${bad(v) ? '' : v > 0 ? 'p' : 'm'}">${sg}</span></div>`;
    }).join('');
    const adj = !bad(L.sec_change_12m) && Math.abs(L.sec_change_12m) > 0 && !bad(L.cfi_raw_ttm)
      ? `<div class="note">תזרים ההשקעות מנוטרל מקנייה ומכירה של ניירות ערך סחירים (ניהול הקופה). לפני הנטרול: ${plain(money(L.cfi_raw_ttm, A.currency))}.</div>` : '';

    // Damodaran
    const D = A.damodaran;
    const dSteps = (A.damodaran_stages || []).map((x) => `<span class="dstep ${D && D.code === x.code ? 'on' : ''}">${esc(x.he)}</span>`).join('');
    const damo = D ? `<div class="lens">
        <div class="lens-h"><span class="lens-k">לפי Damodaran (2024)${tipBtn('damodaran')}</span><b>${esc(D.he)}</b></div>
        <div class="dsteps">${dSteps}</div>
        <div class="lens-b"><span class="muted">למה:</span> ${esc(D.rule)}.</div>
        <div class="lens-b"><span class="muted">איך מתמחרים בשלב הזה:</span> ${esc(D.value)}</div>
      </div>` : '';

    // שכבת הסרטון: מעבר לרווח נקי
    const lastEv = (A.events || []).slice(-1)[0];
    const recentEv = lastEv && (Date.now() - new Date(lastEv.event_date)) / 86400000 < 400;
    const dvir = A.approaching_profit
      ? `<span class="tag" style="color:${C.green}">מתקרבת לרווח נקי</span>`
      : recentEv ? `<span class="tag" style="color:${C.green}">עברה לרווח נקי לאחרונה</span>` : '';

    const sc = A.scores || {};
    const scoreRows = [['growth', 'צמיחה'], ['profitability', 'רווחיות'], ['strength', 'חוסן פיננסי'], ['valuation', 'תמחור']].map(([k, lbl]) => {
      const v = sc[k];
      if (bad(v)) return `<div class="score"><span class="lbl">${lbl}</span><span class="muted">אין נתון</span><span></span></div>`;
      const col = v >= 7 ? C.green : v >= 4 ? C.amber : C.red;
      const bars = Array.from({ length: 10 }, (_, i) => `<i style="background:${i < v ? col : '#E7ECF2'}"></i>`).join('');
      return `<div class="score"><span class="lbl">${lbl}</span><span class="bars">${bars}</span><span class="val num" style="color:${col}">${v}</span></div>`;
    }).join('');

    const risk = A.risk;
    const rcol = risk.score < 25 ? C.green : risk.score < 50 ? C.amber : C.red;
    const neg = risk.reasons.slice(1).map((r) => `<li><span class="ic" style="background:${C.red}">!</span><span>${esc(r.text)}</span><span class="p num" style="color:${C.red}">+${r.pts}</span></li>`).join('');
    const posi = risk.positives.map((r) => `<li><span class="ic" style="background:${C.green}">✓</span><span>${esc(r.text)}</span><span class="p num" style="color:${C.green}">${r.pts}</span></li>`).join('');
    const name = A.name;
    const story = (A.narrative || []).map((x) => `<p>${esc(x).replace(esc(name), `<bdi>${esc(name)}</bdi>`)}</p>`).join('');

    let runway = '';
    if (!bad(L.net_income_ttm) && L.net_income_ttm < 0 || (!bad(L.fcf_ttm) && L.fcf_ttm < 0)) {
      const rf = A.runway.months_fcf, rn = A.runway.months_ni, be = A.breakeven;
      let beLine = '';
      if (be.trend === 'narrowing' && be.months) beLine = `<li>רווח נקי צפוי לפי המגמה: בעוד כ-<b>${n(be.months)} חודשים</b> – ${bad(rf) || be.months <= rf ? 'הקופה מספיקה עד אז' : 'הקופה לא מספיקה עד אז, צפוי גיוס'}</li>`;
      else if (be.trend === 'widening') beLine = '<li>ההפסדים מתרחבים – אין מגמה לרווח.</li>';
      runway = `<h3 class="h3" style="margin-top:22px">כמה זמן הקופה מחזיקה</h3><ul class="watch">
        <li>לפי תזרים חופשי: <b>${A.runway.self_funded ? 'לא שורפת מזומן' : months(rf)}</b>${A.runway.self_funded ? '' : verdict('runway', rf)}</li>
        ${bad(rn) ? '' : `<li>לפי הפסד נקי (השיטה מהסרטון): <b>${months(rn)}</b></li>`}${beLine}</ul>`;
    }

    const asof = A.asof ? `<div class="asof">
        <span>הנתונים מבוססים על ${esc(A.asof.form_he)} (${n(esc(A.asof.form))}) לתקופה שהסתיימה ב-${dmy(A.asof.period_end)}, שהוגש ל-SEC ב-${dmy(A.asof.filed)}.
        ${A.asof.url ? `<a href="${esc(A.asof.url)}" target="_blank" rel="noopener">לדוח המקורי</a>` : ''}</span>
        <a href="#s-verify" class="vbadge" id="vbadge"></a></div>` : '';

    $('#s-overview').innerHTML = `${asof}
      <div class="card trackcard">
        <div class="track-head">
          <div><div class="kicker">שלב במחזור החיים לפי Dickinson (2011)${tipBtn('dickinson')}</div>
          <h2 style="color:${color}">${esc(A.stage_he)}</h2></div>${dvir}</div>
        ${trackHTML(A.stage, color, A.edges)}
        <div class="cfrow">${cf}</div>${adj}
        <p class="lead" style="margin:12px 0 0">${esc(A.explain)}</p>
        ${edges ? `<div class="edges">${edges}</div>` : ''}
        ${damo}
      </div>
      <div class="grid2" style="margin-top:28px">
        <div>
          <h2 class="h2">תמונת מצב</h2>
          <div class="story">${story}</div>
          <div class="signals" style="margin-top:20px">
            <div><h3 class="h3">סימני אזהרה</h3><ul class="siglist">${neg || '<li><span></span><span class="muted">לא זוהו</span><span></span></li>'}</ul></div>
            <div><h3 class="h3">נקודות חוזק</h3><ul class="siglist">${posi || '<li><span></span><span class="muted">לא זוהו</span><span></span></li>'}</ul></div>
          </div>
        </div>
        <div>
          <h2 class="h2">רמת סיכון${tipBtn('risk')}</h2>
          ${gaugeSVG(risk.score)}
          <div class="gauge-label" style="color:${rcol};margin-top:6px">סיכון ${esc(risk.level)} ביחס לשלב</div>
          <h3 class="h3" style="margin-top:22px">ציונים${tipBtn('scores')}</h3>
          ${scoreRows}
          <div class="note">1–10, גבוה = טוב יותר. בתמחור: גבוה = זול יותר. החישוב שלנו, לא מדד רשמי.</div>
          <h3 class="h3" style="margin-top:22px">מה לבדוק בשלב הזה</h3>
          <ul class="watch">${(A.watch || []).map((w) => `<li>${esc(w)}</li>`).join('')}</ul>
          ${runway}
        </div>
      </div>`;
  }

  // ---------------- גרפים ----------------
  const PAL = { ink: '#14213D', slate: '#9AA9BF', blue: '#2563EB', green: '#1A936F', red: '#C8102E', orange: '#C2410C', violet: '#7C3AED', grid: '#EDF1F6', axis: '#5B6B82' };
  function baseChart(el) {
    const c = echarts.init(el, null, { renderer: 'canvas' });
    charts.push(c);
    return c;
  }
  const qLabel = (iso) => { const d = new Date(iso); return `Q${Math.floor(d.getMonth() / 3) + 1} '${String(d.getFullYear()).slice(2)}`; };
  const qLong = (iso) => { const d = new Date(iso); return `רבעון ${Math.floor(d.getMonth() / 3) + 1}, ${d.getFullYear()}`; };
  const dLabel = (t) => { const d = new Date(t); return `${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.${d.getFullYear()}`; };
  const pctTxt = (x, d = 1) => (bad(x) ? '—' : `${x > 0 ? '+' : ''}${(x * 100).toFixed(d)}%`);
  const AX = {
    axisLine: { lineStyle: { color: PAL.grid } }, axisTick: { show: false },
    axisLabel: { color: PAL.axis, fontFamily: C.font, fontSize: 11 },
    splitLine: { lineStyle: { color: PAL.grid, type: 'dashed' } },
  };
  const LEG = { bottom: 0, right: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 8, itemGap: 16,
    textStyle: { color: PAL.axis, fontFamily: C.font, fontSize: 12 } };
  const TIP = { trigger: 'axis', confine: true, backgroundColor: '#fff', borderColor: PAL.grid, borderWidth: 1, padding: [8, 12],
    textStyle: { color: PAL.ink, fontFamily: C.font, fontSize: 12 }, extraCssText: 'box-shadow:0 6px 20px rgba(20,33,61,.12);direction:rtl;text-align:right' };
  function tipRows(title, rows) {
    return `<div style="font-weight:600;margin-bottom:4px">${title}</div>` + rows.map(([col, lbl, val]) =>
      `<div style="display:flex;justify-content:space-between;gap:16px"><span><i style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${col};margin-inline-end:6px"></i>${lbl}</span><b style="direction:ltr">${val}</b></div>`).join('');
  }

  // ----- גרף המניה: טווחים, תשואה בטווח, מצב אחוזים ומדידה בין שתי נקודות -----
  function renderChart(A) {
    const prices = (A.prices || []).map(([d, v]) => [new Date(d).getTime(), v]);
    const hasPx = prices.length > 1;
    const seen = [];
    (A.series.stage || []).forEach((x) => { if (x !== 'unknown' && !seen.includes(x)) seen.push(x); });
    const legend = seen.map((x) => `<span><i style="background:${A.stages[x].color};opacity:.45"></i>${esc(A.stages[x].he)}</span>`).join('')
      + (A.events.length ? `<span><i style="background:${C.green}"></i>מעבר לרווח נקי</span>` : '');
    const RANGES = [['1M', 'חודש', 30], ['3M', '3 חודשים', 91], ['6M', 'חצי שנה', 182], ['YTD', 'מתחילת השנה', null], ['1Y', 'שנה', 365], ['3Y', '3 שנים', 1095], ['5Y', '5 שנים', 1826], ['MAX', 'הכל', 0]];
    $('#s-chart').innerHTML = `<h2>מחיר המניה</h2>
      <div class="card">
        ${hasPx ? `<div class="px-head">
          <div class="px-ret"><span class="muted">תשואה בטווח המוצג</span><b id="rangeRet" class="num">—</b><span class="muted num" id="rangeDates"></span></div>
          <div class="px-meas" id="measure"><span class="muted">לחיצה על הגרף קובעת נקודת ייחוס – ואז רואים את השינוי באחוזים מכל נקודה אחרת.</span></div>
        </div>
        <div class="chart-tools">
          <div class="seg" id="rng">${RANGES.map(([k, lbl]) => `<button data-r="${k}" title="${lbl}" class="${k === 'MAX' ? 'on' : ''}">${k === 'MAX' ? 'הכל' : k}</button>`).join('')}</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <div class="seg" id="mode"><button data-m="price" class="on">מחיר</button><button data-m="pct">אחוזים</button></div>
            <div class="seg" id="scl"><button data-s="value" class="on">ליניארי</button><button data-s="log">לוגריתמי</button></div>
          </div>
        </div>` : '<p class="muted">מחירי מניה לא זמינים כרגע.</p>'}
        <div class="chart" id="pxChart" ${hasPx ? '' : 'hidden'}></div>
        <div class="legend">${legend}</div>
        <div class="note">הרקע צבוע לפי השלב במחזור החיים (Dickinson) שאובחן בכל רבעון, לפי הדוחות שפורסמו עד אז.</div>
      </div>`;
    if (!hasPx) return;

    const dates = A.series.dates, stages = A.series.stage;
    const areas = [];
    for (let i = 0; i < dates.length; i++) {
      if (stages[i] === 'unknown') continue;
      const end = i + 1 < dates.length ? dates[i + 1] : addDays(dates[i], 91);
      areas.push([{ xAxis: new Date(dates[i]).getTime(), itemStyle: { color: A.stages[stages[i]].color, opacity: 0.09 } }, { xAxis: new Date(end).getTime() }]);
    }
    const st = { i0: 0, i1: prices.length - 1, mode: 'price', anchor: null, scale: 'value' };
    const idxAt = (t) => { let lo = 0, hi = prices.length - 1; while (lo < hi) { const mid = (lo + hi) >> 1; if (prices[mid][0] < t) lo = mid + 1; else hi = mid; } return lo; };
    const base = () => prices[st.i0][1];
    const shown = () => (st.mode === 'pct' ? prices.map(([t, v]) => [t, (v / base() - 1) * 100]) : prices);
    const c = baseChart($('#pxChart'));
    const anchorMark = () => (st.anchor === null ? [] : [{ xAxis: prices[st.anchor][0], lineStyle: { color: PAL.ink, type: 'solid', width: 1.2 },
      label: { show: true, formatter: 'נקודת ייחוס', color: PAL.ink, fontFamily: C.font, position: 'insideEndTop' } }]);
    const marks = () => ({ symbol: 'none', silent: true, label: { show: false }, lineStyle: { color: C.green, type: 'dashed', width: 1.4 },
      data: (A.events || []).map((e) => ({ xAxis: new Date(e.event_date).getTime() })).concat(anchorMark()) });

    c.setOption({
      textStyle: { fontFamily: C.font }, animation: false,
      grid: { left: 64, right: 18, top: 18, bottom: 60 },
      xAxis: { type: 'time', ...AX, splitLine: { show: false } },
      yAxis: { type: 'value', scale: true, ...AX, axisLabel: { ...AX.axisLabel, formatter: (v) => '$' + (+v).toLocaleString('en-US', { maximumFractionDigits: v < 10 ? 2 : 0 }) } },
      dataZoom: [{ type: 'inside', filterMode: 'weakFilter' }, { type: 'slider', filterMode: 'weakFilter', height: 22, bottom: 10, borderColor: PAL.grid, fillerColor: 'rgba(20,33,61,.06)',
        handleStyle: { color: '#fff', borderColor: PAL.slate }, dataBackground: { lineStyle: { color: PAL.slate }, areaStyle: { color: PAL.grid } }, labelFormatter: (v) => dLabel(v), textStyle: { color: PAL.axis } }],
      tooltip: { ...TIP, axisPointer: { type: 'cross', lineStyle: { color: PAL.slate }, label: { show: false } },
        formatter: (ps) => {
          const i = idxAt(ps[0].value[0]); const [t, v] = prices[i];
          const rows = [[PAL.ink, 'מחיר', '$' + v.toFixed(2)], [PAL.slate, 'מתחילת הטווח', pctTxt(v / base() - 1)]];
          if (st.anchor !== null) rows.push([PAL.blue, `מנקודת הייחוס (${dLabel(prices[st.anchor][0])})`, pctTxt(v / prices[st.anchor][1] - 1)]);
          return tipRows(dLabel(t), rows);
        } },
      series: [{ type: 'line', data: shown(), showSymbol: false, lineStyle: { color: PAL.ink, width: 1.6 }, itemStyle: { color: PAL.ink },
        markArea: { silent: true, data: areas }, markLine: marks() }],
    });

    const update = () => {
      const r = prices[st.i1][1] / base() - 1;
      $('#rangeRet').textContent = pctTxt(r);
      $('#rangeRet').className = 'num ' + cls(r);
      $('#rangeDates').textContent = `${dLabel(prices[st.i0][0])} – ${dLabel(prices[st.i1][0])}`;
      if (st.anchor !== null) {
        const a = prices[st.anchor], z = prices[st.i1];
        const ch = z[1] / a[1] - 1;
        $('#measure').innerHTML = `<span>מנקודת הייחוס ${dLabel(a[0])} ($${a[1].toFixed(2)}) עד ${dLabel(z[0])}: <b class="num ${cls(ch)}">${pctTxt(ch)}</b></span>
          <button type="button" class="linkbtn" id="clearAnchor">ביטול</button>`;
        $('#clearAnchor').onclick = () => { st.anchor = null; redraw(); };
      } else {
        $('#measure').innerHTML = '<span class="muted">לחיצה על הגרף קובעת נקודת ייחוס – ואז רואים את השינוי באחוזים מכל נקודה אחרת.</span>';
      }
    };
    const redraw = () => {
      const pctMode = st.mode === 'pct';
      c.setOption({
        yAxis: { type: pctMode ? 'value' : st.scale, axisLabel: { formatter: pctMode ? (v) => `${v > 0 ? '+' : ''}${(+v).toFixed(0)}%` : (v) => '$' + (+v).toLocaleString('en-US', { maximumFractionDigits: v < 10 ? 2 : 0 }) } },
        series: [{ data: shown(), markLine: marks() }],
      });
      update();
    };
    c.on('datazoom', () => {
      const dz = c.getOption().dataZoom[0];
      const t0 = dz.startValue ?? prices[0][0], t1 = dz.endValue ?? prices[prices.length - 1][0];
      st.i0 = idxAt(t0); st.i1 = Math.max(st.i0, Math.min(prices.length - 1, idxAt(t1)));
      if (st.mode === 'pct') redraw(); else update();
    });
    c.getZr().on('click', (e) => {
      if (!c.containPixel({ gridIndex: 0 }, [e.offsetX, e.offsetY])) return;
      const t = c.convertFromPixel({ gridIndex: 0 }, [e.offsetX, e.offsetY])[0];
      const i = idxAt(t);
      st.anchor = st.anchor === i ? null : i;
      redraw();
    });
    $('#rng').addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return;
      [...$('#rng').children].forEach((x) => x.classList.toggle('on', x === b));
      const last = prices[prices.length - 1][0];
      const R = RANGES.find((x) => x[0] === b.dataset.r);
      let start = prices[0][0];
      if (R[0] === 'YTD') start = new Date(new Date(last).getFullYear(), 0, 1).getTime();
      else if (R[2]) start = last - R[2] * 86400000;
      c.dispatchAction({ type: 'dataZoom', startValue: Math.max(start, prices[0][0]), endValue: last });
    });
    $('#mode').addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return;
      [...$('#mode').children].forEach((x) => x.classList.toggle('on', x === b));
      st.mode = b.dataset.m;
      $('#scl').style.visibility = st.mode === 'pct' ? 'hidden' : 'visible';
      redraw();
    });
    $('#scl').addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return;
      [...$('#scl').children].forEach((x) => x.classList.toggle('on', x === b));
      st.scale = b.dataset.s; redraw();
    });
    update();
  }
  function addDays(iso, d) { const t = new Date(iso); t.setDate(t.getDate() + d); return t.toISOString().slice(0, 10); }

  // ---------------- נתונים ----------------
  function renderStats(A, E) {
    const L = A.latest, S = (E && E.stats) || {};
    const loading = E === null;
    const kv = (k, v, tip, vd = '') => `<div class="kv"><span>${k}${tipBtn(tip)}</span><span>${v}${vd}</span></div>`;
    const ys = (x) => (loading ? '<span class="skel" style="display:inline-block;width:60px;height:14px"></span>' : x);
    const dil = L.dilution_yoy;
    const valuation = [
      kv('שווי שוק', money(A.market_cap), 'mcap'),
      kv('מכפיל רווח (P/E)', bad(L.pe) ? 'אין רווח' : num(L.pe), 'pe', verdict('pe', L.pe)),
      kv('מכפיל רווח עתידי', ys(num(S.forwardPE)), 'fpe', loading ? '' : verdict('pe', S.forwardPE)),
      kv('מכפיל מכירות (P/S)', num(L.ps), 'ps', verdict('ps', L.ps)),
      kv('מכפיל תזרים (P/FCF)', num(L.pfcf), 'pfcf', verdict('pfcf', L.pfcf)),
      kv('מכפיל הון (P/B)', ys(num(S.priceToBook)), 'pb'),
      kv('רווח למניה (EPS)', ys(bad(S.trailingEps) ? '—' : n((S.trailingEps < 0 ? '-$' : '$') + Math.abs(S.trailingEps).toFixed(2))), 'eps'),
      kv('תשואת דיבידנד', ys(bad(S.dividendYield) || !S.dividendYield ? 'אין' : pct(S.dividendYield, false)), 'div'),
    ].join('');
    const health = [
      kv('הכנסות, 12 חודשים', `${money(L.revenue_ttm, A.currency)} <span class="${cls(L.revenue_yoy)}" style="font-weight:500">${pct(L.revenue_yoy)}</span>`, 'rev', verdict('growth', L.revenue_yoy)),
      kv('רווח נקי, 12 חודשים', money(L.net_income_ttm, A.currency), 'ni'),
      kv('שולי רווח נקי', pct(L.net_margin_ttm, false), 'nm', verdict('nm', L.net_margin_ttm)),
      kv('שולי רווח גולמי', ys(pct(S.grossMargins, false)), 'gm'),
      kv('תשואה על ההון (ROE)', ys(pct(S.returnOnEquity, false)), 'roe'),
      kv('תזרים חופשי, 12 חודשים', money(L.fcf_ttm, A.currency), 'fcf', verdict('fcf', L.fcf_ttm)),
      kv('מזומן וניירות ערך', money(L.liquid, A.currency), 'liquid'),
      kv('חוב פיננסי', money(L.debt, A.currency), 'debt'),
    ].join('');
    const trading = [
      kv('בטא', ys(num(S.beta, 2)), 'beta', loading ? '' : verdict('beta', S.beta)),
      kv('תנודתיות שנתית', pct(L.volatility, false), 'vol', verdict('vol', L.volatility)),
      kv('מחזור יומי ממוצע', ys(big(S.averageVolume)), 'avgvol'),
      kv('מניות במחזור', big(L.shares), 'shares'),
      kv('דילול שנתי', pct(dil), 'dil', verdict('dil', dil)),
      kv('שורט מהמניות הצפות', ys(pct(S.shortPercentOfFloat, false)), 'short', loading ? '' : verdict('short', S.shortPercentOfFloat)),
      kv('החזקת מוסדיים', ys(pct(S.heldPercentInstitutions, false)), 'inst'),
      kv('החזקת בעלי עניין', ys(pct(S.heldPercentInsiders, false)), 'insider'),
    ].join('');

    let analyst = '';
    if (!loading && !bad(S.targetMeanPrice) && !bad(A.price)) {
      const lo = Math.min(S.targetLowPrice ?? S.targetMeanPrice, A.price), hi = Math.max(S.targetHighPrice ?? S.targetMeanPrice, A.price);
      const at = (v) => ((v - lo) / (hi - lo || 1)) * 100;
      const up = S.targetMeanPrice / A.price - 1;
      analyst = `<div class="card analyst">
        <h3 class="h3">אנליסטים</h3>
        <div class="grid2 even" style="gap:20px">
          <div>
            <div class="kv"><span>המלצה ממוצעת</span><span>${esc(REC_HE[E.recommendation] || E.recommendation || '—')}</span></div>
            <div class="kv"><span>מספר אנליסטים</span><span>${num(S.numberOfAnalystOpinions, 0)}</span></div>
            <div class="kv"><span>מחיר יעד ממוצע</span><span>${n('$' + S.targetMeanPrice.toFixed(2))} <span class="${cls(up)}" style="font-weight:500">(${pct(up)})</span></span></div>
          </div>
          <div>
            <div class="tgt">
              <span class="m" style="left:${at(A.price)}%;color:${C.ink}">מחיר נוכחי</span>
              <span class="m below" style="left:${at(S.targetMeanPrice)}%;color:${C.green}">יעד ממוצע</span>
            </div>
            <div class="tgt-ends"><span>$${lo.toFixed(2)}</span><span>$${hi.toFixed(2)}</span></div>
          </div>
        </div>
      </div>`;
    }
    $('#s-stats').innerHTML = `<h2>נתונים מרכזיים</h2>
      <div class="note" style="margin:-6px 0 10px">B = מיליארד, M = מיליון. לחיצה על ? ליד נתון מסבירה מה הוא אומר. התוויות הצבעוניות הן הערכה כללית, לא המלצה.</div>
      <div class="card"><div class="stats">
        <div><h3>שווי ומכפילים</h3>${valuation}</div>
        <div><h3>רווחיות וחוסן</h3>${health}</div>
        <div><h3>מסחר ובעלות</h3>${trading}</div>
      </div></div>${analyst}`;
  }

  // חוב זניח (פחות מ-2% מהקופה, או שלא דווח) – לא מציירים קו שנראה כמו נתון
  function debtIsNegligible(A) {
    const d = (A.series.debt || []).filter((x) => !bad(x));
    const l = (A.series.liquid || []).filter((x) => !bad(x));
    if (!d.length) return true;
    return Math.max(...d) < 0.02 * Math.max(1, ...l);
  }
  function debtNote(A) {
    if (!debtIsNegligible(A)) return '';
    const d = (A.series.debt || []).filter((x) => !bad(x));
    const txt = d.length ? `החוב הפיננסי זניח (${plain(money(A.latest.debt))}) ולכן לא מוצג בגרף.` : 'לא נמצא חוב פיננסי בדוחות.';
    return `<div class="note" style="margin:-4px 0 6px">${txt}</div>`;
  }

  function renderFin(A) {
    const Y = A.yearly || [];
    const cols = Y.map((r) => `<th>12 ח' עד ${dmy(r.end)}</th>`).join('');
    const row = (lbl, f) => `<tr><td>${lbl}</td>${Y.map((r) => `<td>${f(r)}</td>`).join('')}</tr>`;
    const table = Y.length ? `<div class="tablewrap"><table class="fin"><thead><tr><th></th>${cols}</tr></thead><tbody>
      ${row('הכנסות', (r) => money(r.revenue, A.currency))}
      ${row('צמיחה שנתית', (r) => `<span class="${cls(r.growth)}">${pct(r.growth)}</span>`)}
      ${row('רווח נקי', (r) => `<span class="${cls(r.net_income)}">${money(r.net_income, A.currency)}</span>`)}
      ${row('שולי רווח נקי', (r) => pct(r.margin, false))}
      ${row('תזרים חופשי', (r) => money(r.fcf, A.currency))}
      ${row('מזומן וני"ע', (r) => money(r.liquid, A.currency))}
      ${row('חוב פיננסי', (r) => money(r.debt, A.currency))}
      ${row('מניות', (r) => big(r.shares))}
    </tbody></table></div>` : '<p class="muted">אין מספיק נתונים לטבלה.</p>';

    const L = A.latest, s = A.series, d = s.dates;
    const last = (arr) => { for (let i = arr.length - 1; i >= 0; i--) if (!bad(arr[i])) return arr[i]; return null; };
    const kpi = (val, sub, subCls = '') => `<div class="kpi"><b>${val}</b>${sub ? `<span class="${subCls}">${sub}</span>` : ''}</div>`;
    const netCash = !bad(L.liquid) ? L.liquid - (L.debt || 0) : null;
    const sh = A.series.shares;
    const per = A.period_months === 12 ? 'שנתי' : 'רבעוני';

    $('#s-fin').innerHTML = `<h2>דוחות כספיים</h2>${table}
      <div class="fgrid">
        <div class="fcard wide"><div class="fhead"><div><h3>תזרימי המזומנים – הבסיס למודל Dickinson</h3>
            <div class="fsub">12 חודשים מתגלגלים. הצירוף של שלושת הסימנים קובע את השלב (הפס העליון).</div></div>
            ${kpi(`${esc(A.stage_he)} <span class="num" style="font-weight:500">(${(L.pattern || '').split('').join(' ')})</span>`, '')}</div>
          <div class="chart" id="cCF" style="height:340px"></div></div>
        <div class="fcard"><div class="fhead"><div><h3>הכנסות</h3><div class="fsub">${per}, וצמיחה שנתית ב-%</div></div>
            ${kpi(money(L.revenue_ttm, A.currency), bad(L.revenue_yoy) ? '' : `${pct(L.revenue_yoy)} בשנה`, cls(L.revenue_yoy))}</div>
          <div class="chart sm" id="cRev"></div></div>
        <div class="fcard"><div class="fhead"><div><h3>רווחיות</h3><div class="fsub">12 חודשים מתגלגלים</div></div>
            ${kpi(money(L.net_income_ttm, A.currency), bad(L.net_margin_ttm) ? '' : `שולי רווח ${pct(L.net_margin_ttm, false)}`, cls(L.net_income_ttm))}</div>
          <div class="chart sm" id="cNi"></div></div>
        <div class="fcard"><div class="fhead"><div><h3>מזומן מול חוב</h3><div class="fsub">לסוף כל רבעון</div></div>
            ${kpi(money(netCash, A.currency), bad(netCash) ? '' : (netCash >= 0 ? 'מזומן נטו' : 'חוב נטו'), cls(netCash))}</div>
          ${debtNote(A)}<div class="chart sm" id="cCash"></div></div>
        <div class="fcard"><div class="fhead"><div><h3>מספר מניות</h3><div class="fsub">גידול = דילול</div></div>
            ${kpi(big(last(sh)), bad(L.dilution_yoy) ? '' : `${pct(L.dilution_yoy)} בשנה`, bad(L.dilution_yoy) ? '' : L.dilution_yoy > 0.01 ? 'neg' : L.dilution_yoy < -0.01 ? 'pos' : '')}</div>
          <div class="chart sm" id="cSh"></div></div>
      </div>`;

    const X = { type: 'category', data: d.map(qLabel), ...AX, splitLine: { show: false }, axisLabel: { ...AX.axisLabel, hideOverlap: true } };
    const Ymoney = { type: 'value', ...AX, axisLabel: { ...AX.axisLabel, formatter: (v) => moneyPlain(v) } };
    const G = { left: 60, right: 16, top: 16, bottom: 44 };
    const fmtTip = (ps, fmt) => tipRows(qLong(d[ps[0].dataIndex]), ps.filter((p) => p.value !== null && p.value !== undefined && p.seriesName)
      .map((p) => [p.color && p.color.colorStops ? PAL.ink : (typeof p.color === 'string' ? p.color : PAL.ink), p.seriesName, fmt(p.value, p.seriesName)]));

    // 1) תזרימים + פס שלבים
    const cf = baseChart($('#cCF'));
    cf.setOption({
      textStyle: { fontFamily: C.font }, animation: false,
      grid: [{ left: 60, right: 16, top: 8, height: 14 }, { left: 60, right: 16, top: 34, bottom: 44 }],
      xAxis: [{ ...X, gridIndex: 0, show: false }, { ...X, gridIndex: 1 }],
      yAxis: [{ gridIndex: 0, show: false, max: 1 }, { ...Ymoney, gridIndex: 1 }],
      legend: { ...LEG, data: ['תזרים מפעילות שוטפת', 'תזרים מהשקעות', 'תזרים ממימון'] },
      tooltip: { ...TIP, axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(20,33,61,.04)' } },
        formatter: (ps) => {
          const i = ps[0].dataIndex, stg = A.series.stage[i];
          const head = `${qLong(d[i])}${stg && stg !== 'unknown' ? ` – <span style="color:${A.stages[stg].color}">${A.stages[stg].he}</span>` : ''}`;
          return tipRows(head, ps.filter((p) => p.seriesIndex > 0).map((p) => [p.color, p.seriesName, moneyPlain(p.value) || '—']));
        } },
      series: [
        { type: 'bar', xAxisIndex: 0, yAxisIndex: 0, barWidth: '100%', silent: true,
          data: A.series.stage.map((x) => ({ value: x === 'unknown' ? 0 : 1, itemStyle: { color: x === 'unknown' ? 'transparent' : A.stages[x].color, opacity: 0.85 } })) },
        { type: 'bar', name: 'תזרים מפעילות שוטפת', xAxisIndex: 1, yAxisIndex: 1, data: s.ocf_ttm, itemStyle: { color: PAL.green, borderRadius: [2, 2, 0, 0] }, barMaxWidth: 10, barGap: '15%' },
        { type: 'bar', name: 'תזרים מהשקעות', xAxisIndex: 1, yAxisIndex: 1, data: s.cfi_ttm, itemStyle: { color: PAL.blue, borderRadius: [2, 2, 0, 0] }, barMaxWidth: 10 },
        { type: 'bar', name: 'תזרים ממימון', xAxisIndex: 1, yAxisIndex: 1, data: s.cff_ttm, itemStyle: { color: PAL.orange, borderRadius: [2, 2, 0, 0] }, barMaxWidth: 10 },
      ],
    });

    // 2) הכנסות + צמיחה
    baseChart($('#cRev')).setOption({
      textStyle: { fontFamily: C.font }, animation: false, grid: { ...G, right: 46 }, legend: LEG,
      tooltip: { ...TIP, axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(20,33,61,.04)' } },
        formatter: (ps) => fmtTip(ps, (v, n2) => (n2.includes('%') ? pctTxt(v / 100) : moneyPlain(v))) },
      xAxis: X,
      yAxis: [Ymoney, { type: 'value', ...AX, splitLine: { show: false }, axisLabel: { ...AX.axisLabel, formatter: (v) => `${v}%` } }],
      series: [
        { type: 'bar', name: `הכנסות (${per})`, data: s.revenue_q, itemStyle: { color: PAL.slate, borderRadius: [2, 2, 0, 0] }, barMaxWidth: 14 },
        { type: 'line', name: 'צמיחה שנתית %', yAxisIndex: 1, data: s.revenue_yoy.map((v) => (bad(v) ? null : +(v * 100).toFixed(1))),
          showSymbol: false, smooth: 0.2, lineStyle: { color: PAL.ink, width: 2 }, itemStyle: { color: PAL.ink } },
      ],
    });

    // 3) רווחיות
    baseChart($('#cNi')).setOption({
      textStyle: { fontFamily: C.font }, animation: false, grid: G, legend: LEG,
      tooltip: { ...TIP, formatter: (ps) => fmtTip(ps, (v) => moneyPlain(v) || '—') },
      xAxis: X, yAxis: Ymoney,
      series: [
        { type: 'line', name: 'רווח נקי', data: s.net_income_ttm, showSymbol: false, lineStyle: { color: PAL.ink, width: 2.2 }, itemStyle: { color: PAL.ink },
          markLine: { silent: true, symbol: 'none', label: { show: false }, lineStyle: { color: PAL.slate, type: 'solid', width: 1 }, data: [{ yAxis: 0 }] } },
        { type: 'line', name: 'רווח תפעולי', data: s.op_income_ttm, showSymbol: false, lineStyle: { color: PAL.blue, width: 1.6, type: 'dashed' }, itemStyle: { color: PAL.blue } },
        { type: 'line', name: 'תזרים חופשי', data: s.fcf_ttm, showSymbol: false, lineStyle: { color: PAL.green, width: 1.6 }, itemStyle: { color: PAL.green } },
      ],
    });

    // 4) מזומן מול חוב
    const cashSeries = [{ type: 'line', name: 'מזומן וני"ע', data: s.liquid, showSymbol: false, lineStyle: { color: PAL.green, width: 2.2 }, itemStyle: { color: PAL.green },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(26,147,111,.18)' }, { offset: 1, color: 'rgba(26,147,111,0)' }] } } }];
    if (!debtIsNegligible(A)) cashSeries.push({ type: 'line', name: 'חוב', data: s.debt, showSymbol: false, lineStyle: { color: PAL.red, width: 2 }, itemStyle: { color: PAL.red } });
    baseChart($('#cCash')).setOption({ textStyle: { fontFamily: C.font }, animation: false, grid: G, legend: LEG,
      tooltip: { ...TIP, formatter: (ps) => fmtTip(ps, (v) => moneyPlain(v) || '—') }, xAxis: X, yAxis: Ymoney, series: cashSeries });

    // 5) מניות
    const nf = (v) => (bad(v) ? '—' : Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(v));
    baseChart($('#cSh')).setOption({ textStyle: { fontFamily: C.font }, animation: false, grid: G, legend: LEG,
      tooltip: { ...TIP, formatter: (ps) => fmtTip(ps, nf) }, xAxis: X,
      yAxis: { type: 'value', scale: true, ...AX, axisLabel: { ...AX.axisLabel, formatter: (v) => Intl.NumberFormat('en-US', { notation: 'compact' }).format(v) } },
      series: [{ type: 'line', name: 'מניות', data: sh, showSymbol: false, step: 'end', lineStyle: { color: PAL.violet, width: 2 }, itemStyle: { color: PAL.violet } }] });
  }

  // ---------------- עדכונים ----------------
  function renderNews(A, E) {
    const N = (E && E.news) || { en: [], he: [] };
    const F = (E && E.filings) || { filings: [] };
    const item = (x) => {
      const he = x.title_he && x.title_he !== x.title;
      return `<li><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(he ? x.title_he : x.title)}</a>
        ${he ? `<span class="orig">${esc(x.title)}</span>` : ''}
        <div class="meta">${esc(x.source || '')}${x.source && x.time ? ' – ' : ''}${relTime(x.time)}</div></li>`;
    };
    const en = N.en.length ? `<ul class="news">${N.en.map(item).join('')}</ul>` : '<p class="muted">לא נמצאו כותרות אחרונות.</p>';
    const he = N.he && N.he.length ? `<h3 class="h3" style="margin-top:22px">בתקשורת בישראל</h3><ul class="news">${N.he.map(item).join('')}</ul>` : '';

    const flags = [];
    if (F.shelf_filings_365d && F.shelf_filings_365d.length) {
      flags.push(`<div class="flag warn"><b>הגשות תשקיף בשנה האחרונה (${F.shelf_filings_365d.map((x) => esc(x.form)).join(', ')})</b><br>
        תשקיף מדף מאפשר לחברה לגייס הון בזמן קצר – כלומר אפשרות לדילול.</div>`);
    }
    if (!bad(F.insider_trades_90d)) {
      flags.push(`<div class="flag">${n(F.insider_trades_90d)} דיווחי עסקאות של בעלי עניין (Form 4) ב-90 הימים האחרונים.</div>`);
    }
    const fil = F.filings.length ? F.filings.map((f) => `<div class="filing"><span class="muted">${dmy(f.date)}</span><span class="f">${esc(f.form)}</span>
      <div><a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.label)}</a>${f.items.length ? `<div class="tags">${f.items.map((i) => `<span>${esc(i)}</span>`).join('')}</div>` : ''}</div></div>`).join('')
      : '<p class="muted">אין דיווחים להצגה.</p>';

    $('#s-news').innerHTML = `<h2>עדכונים אחרונים</h2>
      <div class="grid2">
        <div class="card"><h3 class="h3">חדשות</h3>${en}${he}</div>
        <div class="card"><h3 class="h3">דיווחים רשמיים ל-SEC</h3>${flags.join('')}${fil}</div>
      </div>`;
  }

  // ---------------- פרופיל ----------------
  function renderProfile(A, E) {
    const P = (E && E.profile) || {};
    const desc = P.summary_he ? `<p class="lead">${esc(P.summary_he)}</p>`
      : P.summary_short_en ? `<p class="lead" style="direction:ltr;text-align:left">${esc(P.summary_short_en)}</p>`
      : '<p class="muted">תיאור העסק לא זמין כרגע ממקור הנתונים.</p>';
    const full = P.summary_en ? `<details class="full"><summary>התיאור המלא (באנגלית)</summary><div>${esc(P.summary_en)}</div></details>` : '';
    const facts = [];
    if (P.sector_he) facts.push(['סקטור', esc(P.sector_he)]);
    if (P.industry) facts.push(['תעשייה', esc(P.industry)]);
    else if (P.sic) facts.push(['סיווג ענפי (SEC)', esc(P.sic)]);
    if (P.city || P.country) facts.push(['מטה', esc([P.city, P.country].filter(Boolean).join(', '))]);
    if (P.employees) facts.push(['עובדים', n(Number(P.employees).toLocaleString('en-US'))]);
    if (P.website) {
      const url = P.website.startsWith('http') ? P.website : 'https://' + P.website;
      facts.push(['אתר', `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(P.website.replace(/^https?:\/\//, '').replace(/\/$/, ''))}</a>`]);
    }
    if (P.fiscal_year_end && P.fiscal_year_end.length === 4) facts.push(['סוף שנת כספים', n(`${P.fiscal_year_end.slice(2)}/${P.fiscal_year_end.slice(0, 2)}`)]);
    if (P.last_report) facts.push(['דוח אחרון', `${n(esc(P.last_report.form))} לתקופה שהסתיימה ב-${dmy(P.last_report.period)}, פורסם ${dmy(P.last_report.filed)}`]);

    const ev = A.events || [];
    const evTable = ev.length ? `<div class="tablewrap"><table class="fin"><thead><tr><th>רבעון</th><th>פרסום הדוח</th><th>מחיר בפרסום</th><th>12 חודשים אחרי</th><th>עד היום</th><th>שיא מאז</th></tr></thead><tbody>
      ${ev.map((e) => `<tr><td>${dmy(e.quarter_end)}</td><td>${dmy(e.event_date)}</td><td>${bad(e.price_at_event) ? '—' : n('$' + e.price_at_event.toFixed(2))}</td>
        <td class="${cls(e.return_12m)}">${pct(e.return_12m)}</td><td class="${cls(e.return_since)}">${pct(e.return_since)}</td><td class="${cls(e.max_return_since)}">${pct(e.max_return_since)}</td></tr>`).join('')}
      </tbody></table></div><div class="note">התאריך הוא מועד הגשת הדוח ל-SEC – הרגע שבו השוק יודע על הרווח.</div>`
      : '<p class="muted">לא זוהה מעבר מהפסד לרווח נקי בתקופה שיש עליה נתונים.</p>';

    $('#s-profile').innerHTML = `<h2>על החברה</h2>
      <div class="grid2">
        <div class="card">${desc}${full}${facts.length ? `<dl class="facts">${facts.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>` : ''}</div>
        <div class="card"><h3 class="h3">מעבר לרווח נקי – ומה קרה למניה</h3>${evTable}</div>
      </div>
      <div class="note" style="margin-top:14px">עודכן: ${esc(A.updated)} (UTC). דוחות כספיים מתעדכנים בכל פרסום דוח רבעוני.</div>`;
  }


  // ---------------- אמינות הנתונים ----------------
  function crossChecks(A, E) {
    if (!E) return [{ id: 'x', title: 'השוואה מול Yahoo Finance', status: 'info', detail: 'טוען נתונים להשוואה…' }];
    const S = E.stats || {}, L = A.latest;
    if (A.currency !== 'USD' || (E.financial_currency && E.financial_currency !== 'USD')) {
      return [{ id: 'x', title: 'השוואה מול Yahoo Finance', status: 'info', detail: 'לא בוצעה – הדוחות מדווחים במטבע שאינו דולר.' }];
    }
    if (!Object.keys(S).length) return [{ id: 'x', title: 'השוואה מול Yahoo Finance', status: 'info', detail: 'נתוני Yahoo לא זמינים כרגע להשוואה.' }];
    let lag = '';
    if (S.mostRecentQuarter && L.quarter_end) {
      const yq = new Date(S.mostRecentQuarter * 1000), oq = new Date(L.quarter_end);
      if (Math.abs(yq - oq) / 86400000 > 45) lag = ` Yahoo מעודכן לרבעון שהסתיים ב-${yq.toLocaleDateString('he-IL')}, לכן פער מסוים צפוי.`;
    }
    const rows = [];
    const cmp = (title, ours, theirs, okTol, warnTol, note = '', scale = null) => {
      if (bad(ours) || bad(theirs)) return;
      const base = Math.max(Math.abs(ours), Math.abs(theirs), scale || 0) || 1;
      const diff = Math.abs(ours - theirs) / base;
      const st = diff <= okTol ? 'ok' : diff <= warnTol ? 'warn' : 'fail';
      rows.push({ id: 'x-' + title, title: `${title}: תואם ל-Yahoo Finance`, status: lag && st !== 'ok' ? 'info' : st,
        detail: `SEC: ${plain(money(ours))}, Yahoo: ${plain(money(theirs))} (פער ${(diff * 100).toFixed(1)}%).${note}${st !== 'ok' ? lag : ''}` });
    };
    cmp('הכנסות 12 חודשים', L.revenue_ttm, S.totalRevenue, 0.03, 0.10);
    cmp('רווח נקי 12 חודשים', L.net_income_ttm, S.netIncomeToCommon, 0.05, 0.15, '', Math.abs(L.revenue_ttm || 0) * 0.05);
    const ourCash = (L.cash || 0) + (L.st_investments || 0);
    if (ourCash) cmp('מזומן והשקעות קצרות', ourCash, S.totalCash, 0.10, 0.25, ' Yahoo לא כולל ניירות ערך לטווח ארוך.');
    if (!bad(L.shares) && !bad(S.sharesOutstanding)) {
      const d = Math.abs(L.shares - S.sharesOutstanding) / Math.max(L.shares, S.sharesOutstanding);
      rows.push({ id: 'x-sh', title: 'מספר מניות: תואם ל-Yahoo Finance', status: d <= 0.03 ? 'ok' : d <= 0.10 ? 'warn' : 'info',
        detail: `SEC: ${big(L.shares).replace(/<[^>]+>/g, '')}, Yahoo: ${big(S.sharesOutstanding).replace(/<[^>]+>/g, '')} (פער ${(d * 100).toFixed(1)}%). פער קטן נובע לרוב מסוגי מניות שונים או ממועד הספירה.` });
    }
    return rows.length ? rows : [{ id: 'x', title: 'השוואה מול Yahoo Finance', status: 'info', detail: 'אין מספיק נתונים להשוואה.' }];
  }

  const plain = (h) => String(h).replace(/<[^>]+>/g, '');

  function renderVerify(A, E) {
    const all = (A.checks || []).concat(crossChecks(A, E));
    const scored = all.filter((c) => c.status !== 'info');
    const okN = scored.filter((c) => c.status === 'ok').length;
    const fails = scored.filter((c) => c.status === 'fail').length;
    const warns = scored.filter((c) => c.status === 'warn').length;
    const level = fails ? 'fail' : warns ? 'warn' : 'ok';
    const icon = { ok: '✓', warn: '!', fail: '✕', info: 'i' };
    const summary = level === 'ok' ? `כל ${scored.length} הבדיקות עברו` : `${okN} מתוך ${scored.length} בדיקות עברו`;
    const vb = $('#vbadge');
    if (vb) { vb.className = `vbadge ${level}`; vb.innerHTML = `${icon[level]} אימות נתונים: ${summary}`; }

    const checks = all.map((c) => `<li><span class="st ${c.status}">${icon[c.status]}</span><div><b>${esc(c.title)}</b><span class="d">${esc(c.detail)}</span></div></li>`).join('');
    const src = (A.sources || []).map((r) => {
      const isMoney = r.key !== 'shares';
      const val = isMoney ? money(r.value, A.currency) : big(r.value);
      const links = r.filings.slice(0, 4).map((f) => `<a href="${esc(f.url)}" target="_blank" rel="noopener" title="${esc(f.form_he)}, הוגש ${esc(f.filed)}">${n(esc(f.form))} ${dmy(f.period_end)}</a>`).join('');
      return `<tr><td>${esc(r.label)}<div class="how">${esc(r.how)}</div></td><td>${val}</td>
        <td><div class="flinks">${links || '<span class="muted">—</span>'}</div></td>
        <td class="tag">${r.concepts.map(esc).join('<br>')}</td></tr>`;
    }).join('');
    const signHe = (c) => (c === '+' ? '<span class="sign p">+</span>' : '<span class="sign m">−</span>');
    const dtab = (A.dickinson_table || []).map((r) => `<tr${r.stage === A.stage && r.pattern === A.latest.pattern ? ' class="hl"' : ''}>
      <td>${signHe(r.pattern[0])}</td><td>${signHe(r.pattern[1])}</td><td>${signHe(r.pattern[2])}</td>
      <td><span style="color:${A.stages[r.stage].color};font-weight:600">${esc(r.he)}</span></td></tr>`).join('');
    const drules = (A.damodaran_stages || []).map((r) => `<tr${A.damodaran && A.damodaran.code === r.code ? ' class="hl"' : ''}><td><b>${esc(r.he)}</b></td><td>${esc(r.rule)}</td></tr>`).join('');
    const method = `<div class="card" style="margin-bottom:22px"><h3 class="h3">איך נקבע השלב</h3>
      <div class="grid2 even" style="gap:28px">
        <div>
          <p><b>מודל Dickinson (2011).</b> מודל אקדמי שפורסם ב-The Accounting Review. השלב נקבע לפי הסימן של שלושת חלקי דוח תזרים המזומנים
          ב-12 החודשים האחרונים, בלי ספים: 8 צירופים אפשריים, 5 שלבים. השורה המודגשת היא הצירוף של החברה.</p>
          <div class="tablewrap"><table class="fin mtab"><thead><tr><th>פעילות שוטפת</th><th>השקעות</th><th>מימון</th><th>שלב</th></tr></thead><tbody>${dtab}</tbody></table></div>
          <p class="note">התאמה שלנו: מתזרים ההשקעות מנוטרלות קנייה ומכירה של ניירות ערך סחירים (לפי השינוי ביתרתם במאזן), כי זה ניהול של הקופה ולא השקעה בעסק.
          בלי הנטרול, חברות עם קופה גדולה "קופצות" לשלב התנערות בכל פעם שהן מוכרות אג"ח.</p>
        </div>
        <div>
          <p><b>מחזור החיים של Damodaran.</b> שישה שלבים לפי צמיחה ורווחיות, וכל שלב מתמחרים אחרת – זה הבסיס לרעיון בסרטון.
          Damodaran מתאר את השלבים במילים. הכללים כאן הם התרגום שלנו למספרים.</p>
          <div class="tablewrap"><table class="fin mtab"><thead><tr><th>שלב</th><th>כלל</th></tr></thead><tbody>${drules}</tbody></table></div>
          <p class="note"><b>שכבה נוספת מהסרטון:</b> "מעבר לרווח נקי" – הרבעון שבו הרווח הנקי השנתי הפך לחיובי, ומה קרה למניה מאז. רווח שנובע מסעיפים לא תפעוליים לא נספר.</p>
        </div>
      </div>
      <div class="note" style="margin-top:10px">מקורות:
        <a href="https://doi.org/10.2308/accr-10130" target="_blank" rel="noopener">Dickinson, V. (2011). Cash Flow Patterns as a Proxy for Firm Life Cycle. The Accounting Review</a>;
        <a href="https://pages.stern.nyu.edu/~adamodar/pdfiles/blog/corporatelifecycle.pdf" target="_blank" rel="noopener">Damodaran, A. The Corporate Life Cycle</a>.</div>
    </div>`;
    $('#s-verify').innerHTML = `<h2>המודל ואמינות הנתונים</h2>${method}
      <div class="grid2">
        <div class="card"><h3 class="h3">בדיקות (${summary})</h3><ul class="checks">${checks}</ul></div>
        <div class="card"><h3 class="h3">איך זה עובד</h3>
          <ul class="watch">
            <li>המספרים מגיעים ישירות מהדוחות הרשמיים שהחברה הגישה ל-SEC, בפורמט XBRL – לא מאתר צד שלישי.</li>
            <li>בדיקות פנימיות: שהנתונים עדכניים, שאין רבעונים חסרים או שליליים, ושהקופה והחוב סבירים ביחס למאזן.</li>
            <li>בדיקה חיצונית: השוואה למספרים של Yahoo Finance, שמגיעים ממקור נתונים אחר.</li>
            <li>לכל נתון בטבלה למטה יש קישור לדוח המקורי ב-SEC, כדי שתוכל לבדוק בעצמך.</li>
          </ul></div>
      </div>
      <div class="card" style="margin-top:22px"><h3 class="h3">מאיפה כל מספר מגיע</h3>
        <div class="tablewrap"><table class="fin src"><thead><tr><th>נתון</th><th>ערך</th><th>הדוחות</th><th>השדה בדוח (XBRL)</th></tr></thead><tbody>${src}</tbody></table></div>
        <div class="howto">איך לבדוק בעצמך: לוחצים על דוח, נפתח עמוד הדוח ב-SEC. פותחים את המסמך הראשי (הקובץ הראשון ברשימה) ומחפשים בו (Ctrl+F) את המספר או את שם הסעיף,
        למשל "Total revenue" או "Cash and cash equivalents". בנתוני 12 חודשים – הערך הוא סכום ארבעת הרבעונים שבקישורים.</div>
      </div>`;
  }

  // ---------------- חלונית הסבר ----------------
  function initTips() {
    const pop = $('#tip');
    let current = null;
    const hide = () => { pop.hidden = true; current = null; };
    document.addEventListener('click', (e) => {
      const b = e.target.closest('.i');
      if (!b) { if (!e.target.closest('#tip')) hide(); return; }
      e.preventDefault();
      if (current === b) { hide(); return; }
      current = b;
      pop.textContent = EXPLAIN[b.dataset.tip] || '';
      pop.hidden = false;
      const r = b.getBoundingClientRect();
      const w = Math.min(300, window.innerWidth - 24);
      pop.style.maxWidth = w + 'px';
      let left = r.left + window.scrollX + r.width / 2 - pop.offsetWidth / 2;
      left = Math.max(12 + window.scrollX, Math.min(left, window.scrollX + window.innerWidth - pop.offsetWidth - 12));
      pop.style.left = left + 'px';
      pop.style.top = (r.bottom + window.scrollY + 8) + 'px';
    });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hide(); });
    window.addEventListener('scroll', hide, { passive: true });
  }

  // ---------------- ניווט פנימי ----------------
  function initSubnav() {
    const links = [...document.querySelectorAll('.subnav a')];
    links.forEach((a) => {
      if (a.dataset.bound) return;
      a.dataset.bound = '1';
      a.addEventListener('click', (e) => { e.preventDefault(); $(a.getAttribute('href')).scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }); });
    });
    const obs = new IntersectionObserver((ents) => {
      ents.forEach((e) => { if (e.isIntersecting) links.forEach((a) => a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id)); });
    }, { rootMargin: '-40% 0px -55% 0px' });
    links.forEach((a) => obs.observe($(a.getAttribute('href'))));
  }

  window.addEventListener('resize', () => charts.forEach((c) => c.resize()));
  window.addEventListener('popstate', route);
  initSearch();
  initTips();
  route();
})();
