import json
from datetime import datetime, timezone
import streamlit as st
import streamlit.components.v1 as components

# ── Sayfa ayarı ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="KOBİ Finans Asistanı",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],
[data-testid="block-container"],.main,.stApp{background:#0a0a0a!important}
header[data-testid="stHeader"]{background:#0a0a0a!important}
footer,#MainMenu,.stDeployButton{display:none!important}
</style>
""", unsafe_allow_html=True)

# ── Mock Veriler ──────────────────────────────────────────────────────────────
MOCK_FINANCIAL = {
    "revenue": 847000.0,
    "expenses": 723000.0,
    "net_cash_flow": 124000.0,
    "collection_rate_pct": 78.4,
    "invoices": {"total": "142 Adet", "overdue": "₺106.8K"},
    "status": "warning"
}

MOCK_RISK = {
    "upcoming_payments": [
        {"label": "SGK Prim", "due_date": "2026-05-25", "amount": 68400, "urgency": "high"},
        {"label": "Personel Maaş", "due_date": "2026-05-30", "amount": 142000, "urgency": "high"},
        {"label": "Ofis Kira", "due_date": "2026-06-01", "amount": 38500, "urgency": "medium"},
        {"label": "Tedarikçi (Hammadde)", "due_date": "2026-06-05", "amount": 91200, "urgency": "medium"}
    ],
    "overdue_receivables": [
        {"counterparty": "XYZ Lojistik", "days_overdue": 14, "amount": 42000},
        {"counterparty": "Alfa Üretim A.Ş.", "days_overdue": 8, "amount": 64800}
    ],
    "cash_flow_risks": [
        {"risk": "Likidite Sıkışıklığı", "probability": 0.85, "impact": "high"},
        {"risk": "Şüpheli Alacak Artışı", "probability": 0.45, "impact": "medium"},
        {"risk": "Hammadde Maliyet Artışı", "probability": 0.20, "impact": "low"}
    ]
}

MOCK_DECISION = {
    "verdict": "marginal",
    "confidence": 0.81,
    "answer": "Tahsilat oranı %78.4 ile hedefin altında. 30 günlük yükümlülükler mevcut nakit rezervini zorlayacak seviyede. Likidite oranı kritik eşik olan 1.2'nin altına (1.08) inme eğiliminde.",
    "recommended_action": "Kredi limiti kullanmak yerine gecikmiş alacaklar (₺106.8K) için acil faktoring işlemi başlatılmalı."
}

if "financial_result" not in st.session_state:
    st.session_state["financial_result"] = {"data": MOCK_FINANCIAL, "received_at": datetime.now(timezone.utc).isoformat()}
    st.session_state["risk_result"] = {"data": MOCK_RISK, "received_at": datetime.now(timezone.utc).isoformat()}
    st.session_state["decision_result"] = {"data": MOCK_DECISION, "received_at": datetime.now(timezone.utc).isoformat()}
    st.session_state["mq_connected"] = True
    st.session_state["mq_error"] = None
    st.session_state["last_update"] = datetime.now(timezone.utc).isoformat()


def _j(key: str) -> str:
    r = st.session_state.get(f"{key}_result")
    return json.dumps(r.get("data")) if r else "null"

def _build_html(fin_j: str, risk_j: str, dec_j: str, mq_ok: bool, mq_err: str | None) -> str:
    conn_badge = '<span style="color:#1D9E75">● RabbitMQ · canlı (Mock)</span>'

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0a0a0a;color:#e4e4e4;font-family:'Inter',system-ui,sans-serif;font-size:13px}}
.shell{{display:flex;flex-direction:column;min-height:700px}}
.topbar{{background:#111;border-bottom:1px solid #1e1e1e;padding:10px 18px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}}
.brand{{display:flex;align-items:center;gap:8px}}
.bdot{{width:7px;height:7px;border-radius:50%;background:#1D9E75;animation:blink 2s infinite}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
.bname{{font-size:12px;font-weight:500;letter-spacing:.3px}}
.bsub{{font-size:10px;color:#444;margin-left:2px}}
.topbar-r{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.pill{{font-size:10px;padding:3px 9px;border-radius:20px;border:1px solid #1D9E7440;color:#1D9E75;background:#111;display:flex;align-items:center;gap:5px}}
.pill .pd{{width:5px;height:5px;border-radius:50%;background:currentColor}}
.pill.off{{border-color:#333;color:#555}}
.tabs{{display:flex;background:#111;border-bottom:1px solid #1e1e1e;padding:0 18px}}
.tab{{font-size:11px;padding:9px 14px;cursor:pointer;color:#555;border-bottom:2px solid transparent;white-space:nowrap}}
.tab.active{{color:#e4e4e4;border-bottom-color:#1D9E75}}
.tab:hover:not(.active){{color:#aaa}}
.pane{{display:none;padding:14px 18px;flex-direction:column;gap:12px}}
.pane.active{{display:flex}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}}
.mc{{background:#141414;border:1px solid #1e1e1e;border-radius:6px;padding:11px 13px}}
.ml{{font-size:10px;color:#555;margin-bottom:5px;text-transform:uppercase;letter-spacing:.4px}}
.mv{{font-size:19px;font-weight:500}}
.md{{font-size:10px;margin-top:3px}}
.gn{{color:#1D9E75}}.rn{{color:#E24B4A}}.yn{{color:#BA7517}}
.twocol{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.card{{background:#111;border:1px solid #1e1e1e;border-radius:8px;padding:13px 15px}}
.ct{{font-size:10px;color:#444;text-transform:uppercase;letter-spacing:.5px;margin-bottom:11px;font-weight:500}}
.cw{{position:relative;width:100%;height:170px}}
.empty{{color:#333;font-size:11px;font-style:italic;padding:8px 0;line-height:1.6}}
.alert{{padding:8px 13px;border-radius:5px;font-size:11px;display:flex;gap:8px;line-height:1.5;margin-bottom:4px}}
.ac{{background:#1a0a0a;border:1px solid #3a1515;color:#f09595}}
.aw{{background:#140f00;border:1px solid #2e2000;color:#EF9F27}}
.chips{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}}
.chip{{font-size:10px;padding:4px 10px;border-radius:20px;border:1px solid #222;cursor:pointer;color:#555;background:#111;transition:all .15s}}
.chip:hover{{border-color:#1D9E7440;color:#1D9E75}}
.chip.active{{background:#0a1f18;border-color:#1D9E75;color:#1D9E75;font-weight:500}}
.sc-out{{min-height:55px;font-size:12px;color:#777;line-height:1.7;padding:8px 0}}
.sc-out strong{{color:#e4e4e4}}
.pi{{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #181818}}
.pi:last-child{{border-bottom:none}}
.pn{{font-size:12px;color:#ccc}}.pd2{{font-size:10px;color:#444}}.pa{{font-size:12px;font-weight:500}}
.ud{{width:5px;height:5px;border-radius:50%;margin-right:7px;flex-shrink:0}}
.uh{{background:#E24B4A}}.um{{background:#BA7517}}.ul{{background:#1D9E75}}
.oi{{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #181818;font-size:12px}}
.oi:last-child{{border-bottom:none}}
.op{{font-size:10px;background:#1a0a0a;color:#E24B4A;border:1px solid #2a1010;padding:2px 7px;border-radius:10px}}
.rb{{margin-bottom:9px}}
.rh{{display:flex;justify-content:space-between;margin-bottom:4px;font-size:11px;color:#555}}
.rt{{height:4px;background:#1a1a1a;border-radius:2px;overflow:hidden}}
.rf{{height:100%;border-radius:2px;transition:width .4s}}
.ai-wrap{{background:#111;border:1px solid #1e1e1e;border-radius:8px;overflow:hidden}}
.ai-hdr{{padding:10px 15px;border-bottom:1px solid #1e1e1e;display:flex;align-items:center;gap:8px}}
.ai-ico{{width:18px;height:18px;border-radius:50%;background:#0a1f18;border:1px solid #1D9E7440;display:flex;align-items:center;justify-content:center;font-size:9px;color:#1D9E75;font-weight:700}}
.ai-body{{padding:13px 15px;display:flex;flex-direction:column;gap:11px}}
.sg{{display:grid;grid-template-columns:1fr 1fr;gap:7px}}
.sb{{background:#141414;border:1px solid #1e1e1e;border-radius:6px;padding:9px 11px;cursor:pointer;text-align:left;transition:border-color .15s}}
.sb:hover{{border-color:#1D9E7440}}
.st2{{font-size:9px;color:#1D9E75;font-weight:500;margin-bottom:3px;text-transform:uppercase;letter-spacing:.3px}}
.ss{{font-size:11px;color:#888;line-height:1.45}}
.cm{{min-height:70px;max-height:220px;overflow-y:auto;display:flex;flex-direction:column;gap:9px;padding-bottom:6px}}
.msg{{padding:8px 11px;border-radius:5px;max-width:88%;font-size:12px;line-height:1.6}}
.mu{{background:#1a1a1a;align-self:flex-end;color:#ccc;border:1px solid #222}}
.ma{{background:#0a1f18;color:#9FE1CB;align-self:flex-start;border:1px solid #1D9E7530}}
.ma strong{{color:#1D9E75}}
.ml2{{color:#444;font-style:italic;font-size:11px;align-self:flex-start}}
.cr{{display:flex;gap:7px;margin-top:8px}}
.cr input{{flex:1;padding:7px 11px;font-size:12px;border-radius:5px;border:1px solid #1e1e1e;background:#141414;color:#e4e4e4;outline:none}}
.cr input:focus{{border-color:#1D9E7440}}
.cr input::placeholder{{color:#333}}
.cr button{{padding:7px 13px;background:#1D9E75;color:#0a0a0a;border:none;border-radius:5px;font-size:12px;cursor:pointer;font-weight:600}}
.cr button:hover{{background:#5DCAA5}}
.cr button:disabled{{opacity:.4;cursor:default}}
.sl{{font-size:10px;font-weight:500;color:#333;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}}
.vb{{border-radius:5px;padding:11px 14px;border:1px solid;margin-bottom:10px}}
.mq-bar{{background:#0a1208;border:1px solid #1D9E7520;border-radius:5px;padding:7px 12px;font-size:10px;color:#444;display:flex;align-items:center;gap:8px}}
.legend{{display:flex;gap:14px;margin-bottom:7px;flex-wrap:wrap}}
.li{{display:flex;align-items:center;gap:5px;font-size:10px;color:#555}}
.ls{{width:9px;height:9px;border-radius:2px}}
</style>
</head>
<body>
<div class="shell">

<div class="topbar">
  <div class="brand">
    <div class="bdot"></div>
    <div><span class="bname">KOBİ Finans Asistanı</span><span class="bsub">· Otonom Karar Motoru v2</span></div>
  </div>
  <div class="topbar-r">
    <div class="pill" id="pill-fin"><div class="pd"></div>Finansal Analiz</div>
    <div class="pill" id="pill-risk"><div class="pd"></div>Risk Ajanı</div>
    <div class="pill" id="pill-dec"><div class="pd"></div>Karar Motoru</div>
    <div style="font-size:10px" id="mq-status">{conn_badge}</div>
  </div>
</div>

<div class="tabs">
  <div class="tab active" data-tab="overview">Genel Bakış</div>
  <div class="tab" data-tab="risk">Risk & Ödemeler</div>
  <div class="tab" data-tab="ai">AI Asistan</div>
</div>

<div class="pane active" id="pane-overview">
  <div id="alert-area"></div>
  <div class="metrics">
    <div class="mc"><div class="ml">Toplam Gelir</div><div class="mv" id="m-gelir">—</div><div class="md" id="m-gelir-d"></div></div>
    <div class="mc"><div class="ml">Net Nakit Akışı</div><div class="mv" id="m-nakit">—</div><div class="md" id="m-nakit-d"></div></div>
    <div class="mc"><div class="ml">Tahsilat Oranı</div><div class="mv" id="m-tahsilat">—</div><div class="md yn" id="m-tahsilat-d"></div></div>
    <div class="mc"><div class="ml">Fatura / Gecikmiş</div><div class="mv" id="m-fatura">—</div><div class="md" id="m-fatura-d"></div></div>
  </div>
  <div class="twocol">
    <div class="card">
      <div class="ct">Nakit Akışı Trendi</div>
      <div class="legend"><div class="li"><div class="ls" style="background:#1D9E75"></div>Gelir</div><div class="li"><div class="ls" style="background:#BA7517"></div>Gider</div></div>
      <div class="cw"><canvas id="c1" role="img" aria-label="Nakit akışı trendi">Nakit akışı grafiği yükleniyor</canvas></div>
    </div>
    <div class="card">
      <div class="ct">Karar Motoru Sonucu</div>
      <div id="verdict-area" class="empty">Yükleniyor...</div>
    </div>
  </div>
  <div class="card">
    <div class="ct">Senaryo Analizi</div>
    <div class="chips" id="sch">
      <div class="chip active" data-q="liquidity30">Likidite 30 gün</div>
      <div class="chip" data-q="salary3m">3 Aylık Maaş & Kira</div>
      <div class="chip" data-q="baddebt20">%20 Şüpheli Alacak</div>
      <div class="chip" data-q="personnel">Yeni Personel</div>
      <div class="chip" data-q="rawmat10">Ham Madde +%10</div>
      <div class="chip" data-q="breakeven">Başabaş Noktası</div>
      <div class="chip" data-q="cashcycle">Nakit Çevrim</div>
      <div class="chip" data-q="revenue_target">Yıl Sonu Hedef</div>
    </div>
    <div class="sc-out" id="sc-out">Bir senaryo seçin.</div>
  </div>
</div>

<div class="pane" id="pane-risk">
  <div class="twocol">
    <div class="card">
      <div class="ct">Yaklaşan Kritik Ödemeler</div>
      <div id="payments-list" class="empty">Veri bekleniyor...</div>
    </div>
    <div class="card">
      <div class="ct">Gecikmiş Alacaklar</div>
      <div id="overdue-list" class="empty">Veri bekleniyor...</div>
    </div>
  </div>
  <div class="card">
    <div class="ct">Risk Göstergeleri</div>
    <div id="risk-bars" class="empty">Veri bekleniyor...</div>
  </div>
  <div class="card">
    <div class="ct">30 Günlük Projeksiyon</div>
    <div class="cw" style="height:150px"><canvas id="c3" role="img" aria-label="30 günlük projeksiyon">Projeksiyon grafiği</canvas></div>
  </div>
</div>

<div class="pane" id="pane-ai">
  <div class="mq-bar">
    <div style="width:5px;height:5px;border-radius:50%;background:#1D9E75;flex-shrink:0;animation:blink 2s infinite"></div>
    <span>RabbitMQ consumer aktif · </span>
    <span style="color:#1D9E75">voiderp.risk</span> &nbsp;|&nbsp;
    <span style="color:#1D9E75">voiderp.financial</span> &nbsp;|&nbsp;
    <span style="color:#1D9E75">voiderp.decision</span>
    &nbsp;· Son mesaj: <span id="last-ts">—</span>
  </div>
  <div class="ai-wrap">
    <div class="ai-hdr">
      <div class="ai-ico">AI</div>
      <div style="font-size:11px;font-weight:500;color:#aaa">Konuşmalı Analitik · Agent bağlamı aktif</div>
      <div style="margin-left:auto;font-size:10px;color:#333">claude-sonnet-4</div>
    </div>
    <div class="ai-body">
      <div>
        <div class="sl">Proaktif Öneriler</div>
        <div class="sg">
          <button class="sb" onclick="askQ('liquidity_ratio')"><div class="st2">⚠ Likidite Riski</div><div class="ss">30 günde likidite oranım güvenli eşiğin altına düşer mi?</div></button>
          <button class="sb" onclick="askQ('salary_credit')"><div class="st2">💰 Maaş Dönemi</div><div class="ss">Maaş ödemeleri için kredi limitimi kullanmalı mıyım?</div></button>
          <button class="sb" onclick="askQ('three_month_reserves')"><div class="st2">📊 3 Aylık Projeksiyon</div><div class="ss">3 büyük ödeme kalemim için yeterli rezervim var mı?</div></button>
          <button class="sb" onclick="askQ('bad_debt_impact')"><div class="st2">🔴 Şüpheli Alacak</div><div class="ss">%20 alacak tahsil edilemezse operasyonum kaç gün etkilenir?</div></button>
          <button class="sb" onclick="askQ('personnel_cost')"><div class="st2">👥 Personel Planı</div><div class="ss">Yeni personel ne zaman nakit akışımı negatife döndürür?</div></button>
          <button class="sb" onclick="askQ('rawmat_margin')"><div class="st2">📈 Maliyet Analizi</div><div class="ss">%10 ham madde artışı brüt marjımı nasıl etkiler?</div></button>
          <button class="sb" onclick="askQ('breakeven_days')"><div class="st2">🎯 Başabaş Noktası</div><div class="ss">Mevcut giderlerimle başabaşa ne kadar yakınım?</div></button>
          <button class="sb" onclick="askQ('revenue_target_monthly')"><div class="st2">🚀 Yıl Sonu Hedef</div><div class="ss">Hedefe ulaşmak için aylık ne kadar yeni satış lazım?</div></button>
        </div>
      </div>
      <div>
        <div class="sl">Sohbet</div>
        <div class="cm" id="chat-msgs">
          <div class="msg ma">Finansal verileriniz RabbitMQ üzerinden akıyor. Bir senaryo seçin ya da sorunuzu yazın.</div>
        </div>
        <div class="cr">
          <input id="chat-inp" placeholder="Sorunuzu yazın..." onkeydown="if(event.key==='Enter')sendChat()">
          <button onclick="sendChat()" id="sbtn">Sor ↗</button>
        </div>
      </div>
    </div>
  </div>
</div>

</div><script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
const INIT = {{
  financial: {fin_j},
  risk:      {risk_j},
  decision:  {dec_j}
}};

const SC = {{
  liquidity30:    `Tahsilat <strong>%78.4</strong> — hedef %85 altında. 30 gün yükümlülük <strong>₺340.100</strong>. <strong>Likidite 1.42 → ~1.08</strong> — güvenli eşik 1.2 altına giriyor.`,
  salary3m:       `3 büyük kalemin 3 aylık toplamı <strong>₺745.500</strong>. Nakit + tahsilat <strong>₺489.600</strong> → açık <strong>₺255.900</strong>. Faktoring önerilir.`,
  baddebt20:      `%20 şüpheli = <strong>₺62.400 kayıp</strong>. Nakit ₺248K → <strong>₺185.600</strong>. Operasyon <strong>38-42 gün</strong> etkilenir.`,
  personnel:      `3 yeni personelde oran <strong>%31.9</strong>. Nakit akışı <strong>4.2 ayda negatife</strong> döner.`,
  rawmat10:       `Brüt marj <strong>%31 → %27.4</strong>. Aylık etki <strong>−₺15.300</strong>. Yıllık <strong>−₺183.600</strong>.`,
  breakeven:      `Sabit gider <strong>₺115K</strong>, marj <strong>%31</strong>, eşik <strong>₺370.967</strong>. Mevcut <strong>₺141K — eşik geçilmiş</strong>.`,
  cashcycle:      `CCC <strong>38 gün net</strong>. Faktoring ile <strong>6 güne</strong> düşer — önemli nakit serbest kalır.`,
  revenue_target: `Hedef <strong>₺1.2M</strong>, YTD <strong>₺847K</strong>. Mevcut hızda yıl sonu <strong>₺1.435K — hedef zaten aşılacak</strong>.`
}};

const QP = {{
  liquidity_ratio:        "Tahsilat oranım %78.4. 30 günde 340.100 TL yükümlülük, nakit 248.000 TL. Likidite oranım 1.42'den ne kadar düşer?",
  salary_credit:          "30 Mayıs maaş 142.000, SGK 68.400, kira 38.500 TL. Nakit 248.000. Kredi limiti 500.000 (187.000 kullanımda). Kredi kullanmalı mıyım?",
  three_month_reserves:   "3 aylık SGK+Maaş+Kira ~745.500 TL. Nakit 248.000, tahsilat 489.600. Faktoring veya kredi gerekir mi?",
  bad_debt_impact:        "%20 alacak (62.400 TL) tahsil edilemezse, aylık 115.000 TL sabit giderle kaç gün operasyonel kalabilirim?",
  personnel_cost:         "18 çalışan, ort. 7.889 TL. 3 yeni personelde personel/ciro oranım ne olur ve nakit ne zaman negatife döner?",
  rawmat_margin:          "Ham madde %10 artarsa brüt marjım %31'den ne kadar düşer?",
  breakeven_days:         "Aylık sabit gider 115.000, brüt marj %31, aylık gelir ort. 141.166 TL. Başabaş durumum?",
  revenue_target_monthly: "Hedef 1.200.000 TL. 847.000 TL yaptım, 7 ay kaldı. Aylık ne kadar yeni satış lazım?"
}};

setTimeout(() => {{
  applyFinancial({{data: INIT.financial}});
  applyRisk({{data: INIT.risk}});
  applyDecision({{data: INIT.decision}});
  const el = document.getElementById('last-ts');
  if (el) el.textContent = new Date().toLocaleTimeString('tr-TR');
}}, 100);

function applyFinancial(m) {{
  const d = m.data;
  if (!d) return;
  document.getElementById('pill-fin').classList.remove('off');
  if (d.revenue != null)
    document.getElementById('m-gelir').textContent = '₺' + Math.round(d.revenue/1000) + 'K';
  if (d.net_cash_flow != null) {{
    const el = document.getElementById('m-nakit');
    el.textContent = (d.net_cash_flow>=0?'₺':'-₺') + Math.abs(Math.round(d.net_cash_flow/1000)) + 'K';
    el.className = 'mv ' + (d.net_cash_flow>=0?'gn':'rn');
  }}
  if (d.collection_rate_pct != null)
    document.getElementById('m-tahsilat').textContent = '%' + d.collection_rate_pct.toFixed(1);
  const inv = d.invoices;
  if (inv) {{
    document.getElementById('m-fatura').textContent = inv.total || '—';
    document.getElementById('m-fatura-d').innerHTML = `<span class="rn">Gecikmiş: ${{inv.overdue||0}}</span>`;
  }}
  const status = d.status;
  const aa = document.getElementById('alert-area');
  if (status === 'critical')
    aa.innerHTML = `<div class="alert ac"><strong>Kritik:</strong> Finansal sağlık kritik seviyede. Acil değerlendirme gerekiyor.</div>`;
  else if (status === 'warning')
    aa.innerHTML = `<div class="alert aw"><strong>Uyarı:</strong> Tahsilat oranı hedefin altında. Gecikmiş alacak takibi önceliklendirilmeli.</div>`;
}}

function applyRisk(m) {{
  const d = m.data;
  if (!d) return;
  document.getElementById('pill-risk').classList.remove('off');
  const uc = {{high:'#E24B4A',medium:'#BA7517',low:'#1D9E75'}};
  const payments = d.upcoming_payments || [];
  if (payments.length)
    document.getElementById('payments-list').innerHTML = payments.map(p=>`
      <div class="pi">
        <div style="display:flex;align-items:center">
          <div class="ud ${{p.urgency==='high'?'uh':p.urgency==='medium'?'um':'ul'}}"></div>
          <div><div class="pn">${{p.label}}</div><div class="pd2">${{p.due_date}}</div></div>
        </div>
        <div class="pa" style="color:${{uc[p.urgency||'low']}}">₺${{(p.amount||0).toLocaleString('tr-TR')}}</div>
      </div>`).join('');

  const overdue = d.overdue_receivables || [];
  if (overdue.length)
    document.getElementById('overdue-list').innerHTML = overdue.map(o=>`
      <div class="oi">
        <div class="pn">${{o.counterparty}}</div>
        <div style="text-align:right">
          <div class="pa rn">₺${{(o.amount||0).toLocaleString('tr-TR')}}</div>
          <div class="op">${{o.days_overdue}} gün</div>
        </div>
      </div>`).join('');

  const risks = d.cash_flow_risks || [];
  if (risks.length) {{
    const rc = {{high:'#E24B4A',medium:'#BA7517',low:'#1D9E75'}};
    const h = Math.ceil(risks.length/2);
    const col = arr => arr.map(r=>`
      <div class="rb">
        <div class="rh"><span>${{r.risk}}</span><span style="color:${{rc[r.impact]}}">%${{Math.round(r.probability*100)}}</span></div>
        <div class="rt"><div class="rf" style="width:${{Math.round(r.probability*100)}}%;background:${{rc[r.impact]}}"></div></div>
      </div>`).join('');
    document.getElementById('risk-bars').innerHTML =
      `<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px"><div>${{col(risks.slice(0,h))}}</div><div>${{col(risks.slice(h))}}</div></div>`;
  }}
}}

function applyDecision(m) {{
  const d = m.data;
  if (!d) return;
  document.getElementById('pill-dec').classList.remove('off');
  const vm = {{
    feasible:     ['ÖDEME KAPASİTESİ YETERLİ','#1D9E75'],
    marginal:     ['MARJİNAL LİKİDİTE','#BA7517'],
    not_feasible: ['KRİTİK NAKİT AÇIĞI','#E24B4A'],
  }};
  const [label,color] = vm[d.verdict]||['BELİRSİZ','#555'];
  const conf = Math.round((d.confidence||0)*100);
  document.getElementById('verdict-area').innerHTML = `
    <div class="vb" style="background:${{color}}10;border-color:${{color}}40">
      <div style="font-size:10px;font-weight:600;letter-spacing:.5px;color:${{color}};margin-bottom:5px">${{label}}</div>
      <div style="font-size:12px;color:#aaa;line-height:1.6">${{d.answer||''}}</div>
      ${{d.recommended_action?`<div style="margin-top:8px;font-size:11px;color:#ccc;border-top:1px solid #222;padding-top:7px"><strong style="color:#1D9E75">Aksiyon:</strong> ${{d.recommended_action}}</div>`:''}}
      <div style="margin-top:6px;font-size:10px;color:#333">Güven: <strong style="color:${{color}}">${{conf}}%</strong></div>
    </div>`;
}}

document.getElementById('sc-out').innerHTML = SC['liquidity30'];

document.querySelectorAll('.chip').forEach(c => {{
  c.addEventListener('click', function() {{
    document.querySelectorAll('.chip').forEach(x=>x.classList.remove('active'));
    this.classList.add('active');
    const el = document.getElementById('sc-out');
    el.innerHTML = '<span style="color:#333;font-style:italic">Hesaplanıyor...</span>';
    setTimeout(()=>{{ el.innerHTML = SC[this.dataset.q]||'—'; }}, 280);
  }});
}});

document.querySelectorAll('.tabs .tab').forEach(t => {{
  t.addEventListener('click', function() {{
    document.querySelectorAll('.tabs .tab').forEach(x=>x.classList.remove('active'));
    document.querySelectorAll('.pane').forEach(x=>x.classList.remove('active'));
    this.classList.add('active');
    document.getElementById('pane-'+this.dataset.tab).classList.add('active');
  }});
}});

new Chart(document.getElementById('c1'), {{
  type: 'line',
  data: {{
    labels: ['Ara','Oca','Şub','Mar','Nis','May'],
    datasets: [
      {{ label:'Gelir', data:[720,760,810,790,830,847], borderColor:'#1D9E75', backgroundColor:'rgba(29,158,117,.06)', fill:true, tension:.35, pointRadius:2, pointBackgroundColor:'#1D9E75' }},
      {{ label:'Gider', data:[680,710,750,740,750,723], borderColor:'#BA7517', backgroundColor:'transparent', fill:false, tension:.35, pointRadius:2, pointBackgroundColor:'#BA7517', borderDash:[4,3] }}
    ]
  }},
  options:{{ responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ display:false }} }},
    scales:{{
      x:{{ grid:{{ color:'rgba(255,255,255,.04)' }}, ticks:{{ font:{{ size:10 }}, color:'#444' }} }},
      y:{{ grid:{{ color:'rgba(255,255,255,.04)' }}, ticks:{{ font:{{ size:10 }}, color:'#444', callback:v=>'₺'+v+'K' }} }}
    }}
  }}
}});

new Chart(document.getElementById('c3'), {{
  type: 'bar',
  data: {{
    labels: ['SGK','Maaş','Kira','Tedarikçi'],
    datasets: [
      {{ label:'Yükümlülük', data:[68.4,142,38.5,91.2], backgroundColor:['#E24B4A','#E24B4A','#BA7517','#BA7517'], borderRadius:3 }},
      {{ label:'Kalan Nakit', data:[248,179.6,37.6,0], backgroundColor:'rgba(29,158,117,.15)', borderRadius:3 }}
    ]
  }},
  options:{{ responsive:true, maintainAspectRatio:false,
    plugins:{{ legend:{{ display:false }} }},
    scales:{{
      x:{{ grid:{{ display:false }}, ticks:{{ font:{{ size:10 }}, color:'#444', autoSkip:false, maxRotation:0 }} }},
      y:{{ grid:{{ color:'rgba(255,255,255,.04)' }}, ticks:{{ font:{{ size:10 }}, color:'#444', callback:v=>'₺'+v+'K' }} }}
    }}
  }}
}});

function appendMsg(text, role) {{
  const c = document.getElementById('chat-msgs');
  const d = document.createElement('div');
  d.className = 'msg ' + (role==='user'?'mu':'ma');
  d.innerHTML = text;
  c.appendChild(d);
  c.scrollTop = c.scrollHeight;
}}

async function askQ(key) {{
  const p = QP[key]; if (!p) return;
  document.querySelector('[data-tab="ai"]').click();
  appendMsg(p, 'user');
  await callClaude(p);
}}

async function sendChat() {{
  const inp = document.getElementById('chat-inp');
  const txt = inp.value.trim(); if (!txt) return;
  inp.value = '';
  appendMsg(txt, 'user');
  await callClaude(txt);
}}

const MOCK_AI_RESPONSES = {{
  "Tahsilat oranım %78.4. 30 günde 340.100 TL yükümlülük, nakit 248.000 TL. Likidite oranım 1.42'den ne kadar düşer?": "Hesaplamalarıma göre likidite oranınız <strong>1.42'den 1.08'e</strong> düşecektir. Bu seviye 1.20 olan risk eşiğinin altındadır. 106.800 TL'lik gecikmiş alacaklar için faktoring teklifi alınması nakit akışını güvenceye alacaktır.<br><br><strong style='color:#1D9E75'>Aksiyon:</strong> Faktoring entegrasyonu üzerinden bankalara teklif isteği gönderildi.",
  "30 Mayıs maaş 142.000, SGK 68.400, kira 38.500 TL. Nakit 248.000. Kredi limiti 500.000 (187.000 kullanımda). Kredi kullanmalı mıyım?": "Mevcut nakdiniz (248.000 TL), toplam 248.900 TL'lik yükümlülüğü karşılamamaktadır (900 TL açık). Operasyonel riski sıfırlamak için boşta kalan limitinizden <strong>50.000 TL kısa vadeli rotatif kredi</strong> kullanımı optimum çözümdür.<br><br><strong style='color:#1D9E75'>Aksiyon:</strong> SAP BTP üzerinden kredi kullanım taslağı hazırlandı.",
  "3 aylık SGK+Maaş+Kira ~745.500 TL. Nakit 248.000, tahsilat 489.600. Faktoring veya kredi gerekir mi?": "Nakit ve beklenen tahsilat toplamınız 737.600 TL'dir. 745.500 TL'lik yükümlülüğe karşı <strong>7.900 TL yapısal açık</strong> tespit edilmiştir. Beklenmedik giderler hesaba katıldığında minimum 100.000 TL'lik kredi hattı hazır tutulmalıdır.<br><br><strong style='color:#1D9E75'>Aksiyon:</strong> Hazine yöneticisine risk uyarısı iletildi.",
  "%20 alacak (62.400 TL) tahsil edilemezse, aylık 115.000 TL sabit giderle kaç gün operasyonel kalabilirim?": "Şüpheli alacak kaybı (62.400 TL) düşüldüğünde serbest nakdiniz 185.600 TL'ye inmektedir. Günlük sabit gideriniz (3.833 TL) baz alındığında, sıfır yeni gelir senaryosunda <strong>48 gün</strong> operasyonel kalabilirsiniz.<br><br><strong style='color:#1D9E75'>Aksiyon:</strong> Şüpheli alacaklar yasal takip listesine eklendi.",
  "18 çalışan, ort. 7.889 TL. 3 yeni personelde personel/ciro oranım ne olur ve nakit ne zaman negatife döner?": "Mevcut %16.7 olan personel maliyeti/ciro oranınız, aylık 23.667 TL'lik ek yük ile <strong>%19.5'e</strong> yükselecektir. Tahsilat hızınızın aynı kaldığı simülasyonda, net nakit akışı <strong>4.2 ay içinde negatife</strong> döner.<br><br><strong style='color:#1D9E75'>Aksiyon:</strong> İşe alım planlaması 3. çeyreğe ertelendi.",
  "Ham madde %10 artarsa brüt marjım %31'den ne kadar düşer?": "Ham madde maliyetlerindeki %10'luk artış, satışların maliyetine doğrudan yansıyacağından brüt marjınızı %31'den <strong>%27.4'e</strong> çekecektir. Bu durum güncel ciro ile aylık 15.300 TL net kar kaybı yaratır.<br><br><strong style='color:#1D9E75'>Aksiyon:</strong> Tedarikçi sözleşmeleri revize edilmek üzere işaretlendi.",
  "Aylık sabit gider 115.000, brüt marj %31, aylık gelir ort. 141.166 TL. Başabaş durumum?": "Aylık 115.000 TL sabit gider ve %31 brüt marj ile başabaş (breakeven) noktası cironuz <strong>370.967 TL'dir.</strong> Mevcut 141.166 TL gelir ile bu noktanın çok altındasınız. Yapısal bir açık söz konusu.<br><br><strong style='color:#E24B4A'>Aksiyon:</strong> Acil OPEX (Operasyonel Gider) optimizasyon senaryosu çalıştırıldı.",
  "Hedef 1.200.000 TL. 847.000 TL yaptım, 7 ay kaldı. Aylık ne kadar yeni satış lazım?": "1.200.000 TL hedefi için kalan 353.000 TL'nin 7 ayda kapanması gerekmektedir. Bu hesaplamayla aylık ortalama <strong>50.428 TL</strong> yeni ve realize edilmiş satış gerektirir. Mevcut büyüme hızıyla hedefe ulaşılabilir.<br><br><strong style='color:#1D9E75'>Aksiyon:</strong> Satış ekibi KPI tablosu güncellendi."
}};

async function callClaude(userMsg) {{
  const btn = document.getElementById('sbtn');
  btn.disabled = true;
  const c = document.getElementById('chat-msgs');
  const ld = document.createElement('div');
  ld.className = 'msg ml2'; 
  ld.textContent = 'control_pod üzerinden analiz ediliyor...';
  c.appendChild(ld); 
  c.scrollTop = c.scrollHeight;
  
  await new Promise(resolve => setTimeout(resolve, 1200));
  ld.remove();
  
  let answer = MOCK_AI_RESPONSES[userMsg];
  if (!answer) {{
    answer = `Mevcut finansal verilerinize göre bu parametre işletme sermayesi üzerinde <strong>orta seviyeli risk</strong> yaratmaktadır. Nakit çevrim süresini (38 gün) ve tahsilat hızını (%78.4) artıracak önlemler alınmalıdır.<br><br><strong style='color:#1D9E75'>Aksiyon:</strong> Finansal model parametreleri yeniden hesaplandı.`;
  }}
  
  appendMsg(answer, 'ai');
  btn.disabled = false;
}}
</script>
</body>
</html>"""

def main() -> None:
    mq  = st.session_state["mq_connected"]
    err = st.session_state["mq_error"]

    components.html(
        _build_html(_j("financial"), _j("risk"), _j("decision"), mq, err),
        height=880,
        scrolling=False,
    )

if __name__ == "__main__":
    main()