/* מסלול – אבחון שלב חברה */
(() => {
  'use strict';

  const C = {
    ink: '#14213D', rule: '#DCE3EC', muted: '#5B6B82', green: '#1A936F', amber: '#C98A00', red: '#C8102E',
    grid: '#EEF2F6', font: "'IBM Plex Sans Hebrew', 'Segoe UI', sans-serif",
  };
  const EXAMPLES = ['ASTS', 'QS', 'TE', 'LMND', 'PLTR', 'SOFI', 'HOOD', 'KO'];
  const STATIONS = ['סטארטאפ', 'צמיחה הפסדית', 'מעבר לרווח', 'צמיחה רווחית', 'ערך'];
  const POS = { startup: 0, startup_to_growth: 0.5, growth_loss: 1, inflection: 2, growth_profit: 3, maturing: 3.5,
    value: 4, value_to_growth: 3.5, loss_slow: 1, declining: 4, unknown: 0 };
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
    edge: 'החברה קרובה לגבול של שלב אחר ונעה לכיוונו, לפי המגמה ב-4 הרבעונים האחרונים.',
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
    const off = stage === 'loss_slow' || stage === 'declining';
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
    const off = A.stage === 'loss_slow' || A.stage === 'declining';
    const edges = (A.edges || []).map((e) => {
      const col = A.stages[e.to] ? A.stages[e.to].color : color;
      const eta = e.eta ? `לפי המגמה: בעוד כ-${n(e.eta)} ${A.period_months === 12 ? 'שנים' : 'רבעונים'}` : 'קרובה לסף – אין עדיין הערכת זמן';
      return `<div class="edgebox" style="border-inline-start-color:${col}"><b>על הסף: ${esc(e.title)} ← ${esc(e.to_he)}${tipBtn('edge')}</b>
        <div>${esc(e.text)}</div><div class="eta">${eta}</div></div>`;
    }).join('');

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
    const story = (A.narrative || []).map((s) => `<p>${esc(s).replace(esc(name), `<bdi>${esc(name)}</bdi>`)}</p>`).join('');

    let runway = '';
    if (['startup', 'startup_to_growth', 'growth_loss', 'loss_slow', 'declining'].includes(A.stage)) {
      const rf = A.runway.months_fcf, rn = A.runway.months_ni, be = A.breakeven;
      let beLine = '';
      if (be.trend === 'narrowing' && be.months) beLine = `<li>רווח נקי צפוי לפי המגמה: בעוד כ-<b>${n(be.months)} חודשים</b> – ${bad(rf) || be.months <= rf ? 'הקופה מספיקה עד אז' : 'הקופה לא מספיקה עד אז, צפוי גיוס'}</li>`;
      else if (be.trend === 'widening') beLine = '<li>ההפסדים מתרחבים – אין מגמה לרווח.</li>';
      else if (be.trend === 'flat') beLine = '<li>ההפסדים יציבים – אין מגמה ברורה לרווח.</li>';
      runway = `<h3 class="h3" style="margin-top:22px">כמה זמן הקופה מחזיקה</h3><ul class="watch">
        <li>לפי תזרים חופשי (מדויק יותר): <b>${A.runway.self_funded ? 'לא שורפת מזומן' : months(rf)}</b>${A.runway.self_funded ? '' : verdict('runway', rf)}</li>
        <li>לפי הפסד נקי (השיטה מהסרטון): <b>${months(rn)}</b></li>${beLine}</ul>`;
    }

    const asof = A.asof ? `<div class="asof">
        <span>הנתונים מבוססים על ${esc(A.asof.form_he)} (${n(esc(A.asof.form))}) לתקופה שהסתיימה ב-${dmy(A.asof.period_end)}, שהוגש ל-SEC ב-${dmy(A.asof.filed)}.
        ${A.asof.url ? `<a href="${esc(A.asof.url)}" target="_blank" rel="noopener">לדוח המקורי</a>` : ''}</span>
        <a href="#s-verify" class="vbadge" id="vbadge"></a></div>` : '';
    $('#s-overview').innerHTML = `${asof}
      <div class="card trackcard">
        <div class="track-head"><h2 style="color:${color}">${esc(A.stage_he)}</h2>
          ${A.approaching_profit ? `<span class="tag" style="color:${C.green}">מתקרבת לרווח נקי</span>` : ''}</div>
        ${trackHTML(A.stage, color, A.edges)}
        ${off ? `<div class="offtrack">מחוץ למסלול הבריא – ${A.stage === 'loss_slow' ? 'הפסדית בלי צמיחה מספקת' : 'ההכנסות מתכווצות'}</div>` : ''}
        <p class="lead" style="margin:6px 0 0">${esc(A.explain)}</p>
        ${edges ? `<div class="edges">${edges}</div>` : ''}
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
  function baseChart(el) {
    const c = echarts.init(el, null, { renderer: 'canvas' });
    charts.push(c);
    return c;
  }
  const axisMoney = { formatter: (v) => moneyPlain(v), color: C.muted, fontFamily: C.font };
  const tip = { trigger: 'axis', textStyle: { fontFamily: C.font }, confine: true };

  function renderChart(A) {
    const perf = A.perf || {};
    const perfHTML = ['1M', '6M', 'YTD', '1Y', '5Y'].filter((k) => !bad(perf[k])).map((k) => {
      const lbl = { '1M': 'חודש', '6M': 'חצי שנה', 'YTD': 'מתחילת השנה', '1Y': 'שנה', '5Y': '5 שנים' }[k];
      return `<div>${lbl}<b class="${cls(perf[k])}">${pct(perf[k])}</b></div>`;
    }).join('');
    const seen = [];
    (A.series.stage || []).forEach((s) => { if (s !== 'unknown' && !seen.includes(s)) seen.push(s); });
    const legend = seen.map((s) => `<span><i style="background:${A.stages[s].color};opacity:.55"></i>${esc(A.stages[s].he)}</span>`).join('')
      + (A.events.length ? `<span><i style="background:${C.green}"></i>מעבר לרווח נקי (פרסום הדוח)</span>` : '');

    $('#s-chart').innerHTML = `<h2>המניה לאורך המסלול</h2>
      <div class="card">
        ${perfHTML ? `<div class="perf">${perfHTML}</div>` : ''}
        <div class="chart-tools">
          <div class="seg" id="rng">${['1Y', '3Y', '5Y', 'MAX'].map((r) => `<button data-r="${r}" class="${r === 'MAX' ? 'on' : ''}">${r === 'MAX' ? 'הכל' : r}</button>`).join('')}</div>
          <div class="seg" id="scl"><button data-s="log" class="on">לוגריתמי</button><button data-s="value">ליניארי</button></div>
        </div>
        <div class="chart" id="pxChart"></div>
        <div class="legend">${legend}</div>
        <div class="note">הרקע צבוע לפי השלב שאובחן בכל רבעון, לפי הדוחות שפורסמו עד אז.</div>
      </div>`;

    const dates = A.series.dates, stages = A.series.stage;
    const areas = [];
    for (let i = 0; i < dates.length; i++) {
      if (stages[i] === 'unknown') continue;
      const end = i + 1 < dates.length ? dates[i + 1] : addDays(dates[i], 91);
      areas.push([{ xAxis: dates[i], itemStyle: { color: A.stages[stages[i]].color, opacity: 0.14 } }, { xAxis: end }]);
    }
    const hasPx = A.prices && A.prices.length;
    const data = hasPx ? A.prices : dates.map((d, i) => [d, A.series.revenue_ttm[i]]);
    const c = baseChart($('#pxChart'));
    const opt = {
      textStyle: { fontFamily: C.font },
      grid: { left: 56, right: 16, top: 16, bottom: 56 },
      tooltip: { ...tip, valueFormatter: (v) => (hasPx ? '$' + (+v).toFixed(2) : moneyPlain(v)) },
      xAxis: { type: 'time', axisLine: { lineStyle: { color: C.rule } }, axisLabel: { color: C.muted } },
      yAxis: { type: hasPx ? 'log' : 'value', scale: true, splitLine: { lineStyle: { color: C.grid } },
        axisLabel: { color: C.muted, formatter: hasPx ? (v) => '$' + (+v).toLocaleString('en-US', { maximumFractionDigits: v < 10 ? 2 : 0 }) : axisMoney.formatter } },
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 8, borderColor: C.rule, textStyle: { color: C.muted } }],
      series: [{
        type: 'line', name: hasPx ? 'מחיר' : 'הכנסות 12 חודשים', data, showSymbol: false, lineStyle: { color: C.ink, width: 1.6 }, itemStyle: { color: C.ink },
        markArea: { silent: true, data: areas },
        markLine: { symbol: 'none', silent: true, label: { show: false }, lineStyle: { color: C.green, type: 'dashed', width: 1.5 },
          data: (A.events || []).map((e) => ({ xAxis: e.event_date })) },
      }],
    };
    c.setOption(opt);
    $('#rng').addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return;
      [...$('#rng').children].forEach((x) => x.classList.toggle('on', x === b));
      const last = data.length ? data[data.length - 1][0] : null;
      const yrs = { '1Y': 1, '3Y': 3, '5Y': 5 }[b.dataset.r];
      c.dispatchAction(yrs && last ? { type: 'dataZoom', startValue: addDays(last, -365 * yrs), endValue: last } : { type: 'dataZoom', start: 0, end: 100 });
    });
    $('#scl').addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b || !hasPx) return;
      [...$('#scl').children].forEach((x) => x.classList.toggle('on', x === b));
      c.setOption({ yAxis: { type: b.dataset.s } });
    });
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

    const per = A.period_months === 12 ? 'שנתי' : 'רבעוני';
    $('#s-fin').innerHTML = `<h2>דוחות כספיים</h2>${table}
      <div class="grid2 even" style="margin-top:22px">
        <div class="card"><h3 class="h3">הכנסות</h3><div class="chart sm" id="cRev"></div></div>
        <div class="card"><h3 class="h3">רווח נקי ותזרים חופשי</h3><div class="chart sm" id="cNi"></div></div>
        <div class="card"><h3 class="h3">מזומן מול חוב</h3><div class="chart sm" id="cCash"></div></div>
        <div class="card"><h3 class="h3">מספר מניות (דילול)</h3><div class="chart sm" id="cSh"></div></div>
      </div>`;

    const d = A.series.dates, s = A.series;
    const common = (extra) => ({
      textStyle: { fontFamily: C.font }, grid: { left: 58, right: 12, top: 30, bottom: 28 },
      tooltip: { ...tip, valueFormatter: (v) => moneyPlain(v) },
      legend: { top: 0, right: 0, textStyle: { color: C.muted, fontFamily: C.font }, itemWidth: 14, itemHeight: 8 },
      xAxis: { type: 'category', data: d.map((x) => x.slice(0, 7)), axisLabel: { color: C.muted }, axisLine: { lineStyle: { color: C.rule } } },
      yAxis: { type: 'value', axisLabel: axisMoney, splitLine: { lineStyle: { color: C.grid } } },
      ...extra,
    });
    baseChart($('#cRev')).setOption(common({ series: [
      { type: 'bar', name: `הכנסות (${per})`, data: s.revenue_q, itemStyle: { color: '#B8C7DC' } },
      { type: 'line', name: '12 חודשים', data: s.revenue_ttm, showSymbol: false, lineStyle: { color: C.ink, width: 2.2 }, itemStyle: { color: C.ink } },
    ] }));
    baseChart($('#cNi')).setOption(common({ series: [
      { type: 'bar', name: `רווח נקי (${per})`, data: s.net_income_q.map((v) => ({ value: v, itemStyle: { color: (v ?? 0) >= 0 ? C.green : C.red } })) },
      { type: 'line', name: 'רווח 12 ח\'', data: s.net_income_ttm, showSymbol: false, lineStyle: { color: C.ink, width: 2.2 }, itemStyle: { color: C.ink } },
      { type: 'line', name: 'תזרים חופשי 12 ח\'', data: s.fcf_ttm, showSymbol: false, lineStyle: { color: '#0E7490', type: 'dashed' }, itemStyle: { color: '#0E7490' } },
    ] }));
    baseChart($('#cCash')).setOption(common({ series: [
      { type: 'line', name: 'מזומן וני"ע', data: s.liquid, showSymbol: false, connectNulls: true, lineStyle: { color: C.green, width: 2.2 }, itemStyle: { color: C.green }, areaStyle: { color: 'rgba(26,147,111,.08)' } },
      { type: 'line', name: 'חוב', data: s.debt, showSymbol: false, connectNulls: true, lineStyle: { color: C.red, width: 2.2 }, itemStyle: { color: C.red } },
    ] }));
    baseChart($('#cSh')).setOption(common({
      tooltip: { ...tip, valueFormatter: (v) => (bad(v) ? '—' : Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(v)) },
      yAxis: { type: 'value', scale: true, axisLabel: { color: C.muted, formatter: (v) => Intl.NumberFormat('en-US', { notation: 'compact' }).format(v) }, splitLine: { lineStyle: { color: C.grid } } },
      series: [{ type: 'line', name: 'מניות', data: s.shares, showSymbol: false, connectNulls: true, lineStyle: { color: '#7C3AED', width: 2.2 }, itemStyle: { color: '#7C3AED' } }],
    }));
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
    $('#s-verify').innerHTML = `<h2>אמינות הנתונים</h2>
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
