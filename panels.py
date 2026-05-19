from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

def _ts_badge(received_at: str | None) -> str:
    if not received_at:
        return ""
    try:
        dt = datetime.fromisoformat(received_at)
        age = (datetime.now(timezone.utc) - dt).seconds
        label = f"{age} sn once" if age < 60 else f"{age // 60} dk once"
        return f"<span style='font-size:11px;color:#888;margin-left:8px;'>Guncelleme: {label}</span>"
    except Exception:
        return ""

def _status_color(status: str) -> str:
    return {"ok": "#22c55e", "warning": "#f59e0b", "critical": "#ef4444"}.get(status, "#888")

def _empty_state(agent_name: str) -> None:
    st.markdown(
        f"""
        <div style="padding:2rem;text-align:center;color:#888;
                    border:1px solid #333;border-radius:8px;background:#111;">
            <div style="font-size:1.1rem;font-weight:600;margin-bottom:.5rem;color:#ccc;">[ {agent_name.upper()} ] Bekleniyor</div>
            <div style="font-size:.85rem;">Asenkron veri akisi dinleniyor. Gelen payload islendiginde render edilecektir.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_financial_panel(result: dict[str, Any] | None) -> None:
    badge = _ts_badge(result.get("received_at") if result else None)
    st.markdown(f"### Finansal Durum Analizi {badge}", unsafe_allow_html=True)

    if not result:
        _empty_state("Finansal Analiz Ajanı")
        return

    d = result["data"]
    
    if "revenue" not in d:
        st.error("Sema Uyumsuzlugu: Beklenen finansal format saglanamadi. Gelen ham payload:")
        st.json(d)
        return

    status_color = _status_color(d.get("status", "ok"))
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Gelir", f"₺{d['revenue']:,.0f}")
    col2.metric("Toplam Gider", f"₺{d['expenses']:,.0f}")
    delta_color = "normal" if d["net_cash_flow"] >= 0 else "inverse"
    col3.metric("Net Nakit Akisi", f"₺{d['net_cash_flow']:,.0f}", delta_color=delta_color)
    col4.metric("Tahsilat Orani", f"{d['collection_rate_pct']:.1f}%")

    st.divider()
    inv = d.get("invoices", {})
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Fatura", inv.get("total", "—"))
    c2.metric("Odenen", inv.get("paid", "—"), delta=f"+{inv.get('paid', 0)}", delta_color="normal")
    c3.metric(
        "Gecikmiş",
        inv.get("overdue", "—"),
        delta=f"₺{inv.get('overdue_amount', 0):,.0f} risk altinda",
        delta_color="inverse",
    )

    st.markdown(
        f"<div style='margin-top:.5rem;'>"
        f"<span style='background:{status_color}22;color:{status_color};"
        f"padding:3px 10px;border-radius:4px;font-size:.8rem;font-weight:600;'>"
        f"Firma Finansal Sagligi: {d.get('status','—').upper()}</span></div>",
        unsafe_allow_html=True,
    )

def render_risk_panel(result: dict[str, Any] | None) -> None:
    badge = _ts_badge(result.get("received_at") if result else None)
    st.markdown(f"### Yaklasan Odemeler ve Riskler {badge}", unsafe_allow_html=True)

    if not result:
        _empty_state("Risk Degerlendirme Ajanı")
        return

    d = result["data"]

    st.markdown("**Kritik Odemeler Tablosu**")
    payments = d.get("upcoming_payments", [])
    if payments:
        for p in payments:
            urgency_color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}.get(
                p.get("urgency", "low"), "#888"
            )
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"padding:8px 12px;margin-bottom:6px;border-radius:4px;"
                f"border-left:4px solid {urgency_color};background:#1a1a1a;'>"
                f"<span style='font-size:.9rem;color:#eee;'>{p['label']}</span>"
                f"<span style='font-size:.85rem;color:#aaa;'>Son Odeme: {p['due_date']}</span>"
                f"<span style='font-size:.9rem;font-weight:700;color:#fff;'>₺{p['amount']:,.0f}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Sistemde yaklasan odeme bulunamadi.")

    st.divider()

    st.markdown("**Geciken Alacaklar**")
    overdue = d.get("overdue_receivables", [])
    if overdue:
        for o in overdue:
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"padding:8px 12px;margin-bottom:6px;border-radius:4px;"
                f"background:#ef444415;border:1px solid #ef444430;'>"
                f"<span style='color:#ccc;'>{o['counterparty']}</span>"
                f"<span style='color:#ef4444;font-size:.85rem;'>{o['days_overdue']} gun gecikme</span>"
                f"<span style='font-weight:700;color:#ef4444;'>₺{o['amount']:,.0f}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Geciken alacak bulunmamaktadir.")

    st.divider()

    st.markdown("**Nakit Akisi Riskleri**")
    risks = d.get("cash_flow_risks", [])
    if risks:
        for r in risks:
            prob = r.get("probability", 0)
            impact_color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}.get(
                r.get("impact", "low"), "#888"
            )
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:16px;"
                f"padding:8px 12px;border-radius:4px;background:#1a1a1a;margin-bottom:6px;'>"
                f"<div style='flex:1;font-size:.9rem;color:#ccc;'>{r['risk']}</div>"
                f"<div style='width:100px;background:#333;border-radius:2px;height:8px;'>"
                f"<div style='width:{prob*100:.0f}%;background:{impact_color};"
                f"border-radius:2px;height:8px;'></div></div>"
                f"<div style='font-size:.85rem;color:{impact_color};min-width:40px;text-align:right;'>"
                f"{prob*100:.0f}%</div></div>",
                unsafe_allow_html=True,
            )

def render_decision_panel(result: dict[str, Any] | None) -> None:
    badge = _ts_badge(result.get("received_at") if result else None)
    st.markdown(f"### KOBI Finans Asistanı Karar Motoru {badge}", unsafe_allow_html=True)

    if not result:
        _empty_state("Karar Motoru")
        return

    d = result["data"]

    verdict = d.get("verdict", "marginal")
    verdict_map = {
        "feasible":     ("ODEME KAPASITESI YETERLI",     "#22c55e"),
        "marginal":     ("MARJINAL LIKIDITE",      "#f59e0b"),
        "not_feasible": ("KRITIK NAKIT ACIGI", "#ef4444"),
    }
    verdict_label, verdict_color = verdict_map.get(verdict, ("BELIRSIZ", "#888"))

    # KOBI Asistani vizyonuna uygun sabit karar sorusu
    q = d.get("question", "Onumuzdeki ay maas ve kira odemelerini rahat karsilayabilir miyim?")
    st.markdown(
        f"<div style='background:#111;border-left:4px solid #555;"
        f"padding:12px 16px;border-radius:0 4px 4px 0;font-style:italic;"
        f"font-size:1rem;color:#ddd;margin-bottom:1.5rem;'>Soru: {q}</div>",
        unsafe_allow_html=True,
    )

    conf = d.get("confidence", 0)
    col_v, col_c = st.columns([2, 1])
    col_v.markdown(
        f"<div style='background:{verdict_color}15;border:1px solid {verdict_color}40;"
        f"padding:8px 16px;border-radius:4px;text-align:center;'>"
        f"<span style='color:{verdict_color};font-size:1.1rem;font-weight:700;letter-spacing:1px;'>"
        f"{verdict_label}</span></div>",
        unsafe_allow_html=True,
    )
    col_c.metric("Matematiksel Guven Skoru", f"{conf*100:.1f}%")

    st.markdown("")
    answer = d.get("answer", "")
    if answer:
        st.markdown(f"<div style='color:#ccc;font-size:0.95rem;line-height:1.5;margin-bottom:1rem;'>**Sistem Yaniti:** {answer}</div>", unsafe_allow_html=True)
        
    facts = d.get("supporting_facts", [])
    if facts:
        st.markdown("**Destekleyici Veriler:**")
        for f in facts:
            st.markdown(f"<div style='color:#aaa;font-size:0.85rem;margin-left:1rem;'>- {f}</div>", unsafe_allow_html=True)
            
    action = d.get("recommended_action", "")
    if action:
        st.markdown(
            f"<div style='margin-top:1rem;padding:12px;background:#22c55e15;border-left:4px solid #22c55e;color:#ddd;'>"
            f"<strong>Onerilen Aksiyon:</strong> {action}</div>",
            unsafe_allow_html=True
        )