"""
Sends trade draft and alert emails via SMTP (e.g. Gmail).
SVG screenshots are inlined as HTML since most email clients block SVG attachments.
"""
from __future__ import annotations

import base64
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
import structlog

from app.config import settings

logger = structlog.get_logger()


async def send_trade_draft_email(
    to_email: str,
    ticker: str,
    action: str,
    shares: int,
    est_price: float,
    est_total: float,
    screenshot_b64: str,
    is_mock: bool,
) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("email_skipped_no_smtp_config")
        return

    action_label = action.upper()
    action_color = "#10B981" if action == "buy" else "#EF4444"
    mock_badge = " (Mock)" if is_mock else ""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"SentinelIQ Trade Draft — {action_label} {shares}x {ticker}{mock_badge}"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email

    html = f"""
    <div style="font-family:Inter,system-ui,sans-serif;background:#ffffff;padding:32px;max-width:600px;margin:auto;">
      <table style="margin-bottom:20px;" cellpadding="0" cellspacing="0">
        <tr>
          <td><span style="background:#10B981;color:#fff;font-weight:700;font-size:13px;padding:4px 10px;border-radius:6px;">SentinelIQ</span></td>
          <td style="padding-left:10px;"><span style="color:#94a3b8;font-size:13px;">Trade Draft Ready</span></td>
        </tr>
      </table>

      <h2 style="color:#0f1117;margin:0 0 4px;">
        <span style="color:{action_color};">{action_label}</span> {shares} share{'s' if shares != 1 else ''} of ${ticker}
      </h2>
      <p style="color:#64748b;margin:0 0 24px;font-size:14px;">Nova Act prepared this order on Alpaca Paper Trading — no trade was placed yet.</p>

      <!-- Order details table -->
      <table style="width:100%;border-collapse:collapse;margin-bottom:24px;border:1px solid #e2e8f0;border-radius:8px;">
        <tr style="background:#f8fafc;">
          <td style="color:#64748b;font-size:12px;padding:12px 16px;border-bottom:1px solid #e2e8f0;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">SYMBOL</td>
          <td style="color:#0f1117;font-size:14px;font-weight:700;text-align:right;padding:12px 16px;border-bottom:1px solid #e2e8f0;">${ticker}</td>
        </tr>
        <tr>
          <td style="color:#64748b;font-size:12px;padding:12px 16px;border-bottom:1px solid #e2e8f0;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">SIDE</td>
          <td style="color:{action_color};font-size:14px;font-weight:700;text-align:right;padding:12px 16px;border-bottom:1px solid #e2e8f0;">{action_label}</td>
        </tr>
        <tr style="background:#f8fafc;">
          <td style="color:#64748b;font-size:12px;padding:12px 16px;border-bottom:1px solid #e2e8f0;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">ORDER TYPE</td>
          <td style="color:#0f1117;font-size:14px;font-weight:600;text-align:right;padding:12px 16px;border-bottom:1px solid #e2e8f0;">Market</td>
        </tr>
        <tr>
          <td style="color:#64748b;font-size:12px;padding:12px 16px;border-bottom:1px solid #e2e8f0;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">QUANTITY</td>
          <td style="color:#0f1117;font-size:14px;font-weight:600;text-align:right;padding:12px 16px;border-bottom:1px solid #e2e8f0;">{shares} share{'s' if shares != 1 else ''}</td>
        </tr>
        <tr style="background:#f8fafc;">
          <td style="color:#64748b;font-size:12px;padding:12px 16px;border-bottom:1px solid #e2e8f0;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">EST. PRICE</td>
          <td style="color:#0f1117;font-size:14px;font-weight:600;text-align:right;padding:12px 16px;border-bottom:1px solid #e2e8f0;">${est_price:,.2f}</td>
        </tr>
        <tr>
          <td style="color:#64748b;font-size:12px;padding:12px 16px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">EST. TOTAL</td>
          <td style="color:{action_color};font-size:18px;font-weight:700;text-align:right;padding:12px 16px;">${est_total:,.2f}</td>
        </tr>
      </table>

      <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:12px 16px;margin-bottom:24px;">
        <p style="color:#92400e;font-size:12px;margin:0;">
          &#9889; Nova Act prepared this order and stopped — <strong>no trade has been placed</strong>.
          Return to SentinelIQ to confirm or discard.
        </p>
      </div>

      <p style="color:#94a3b8;font-size:11px;text-align:center;">
        Paper trade only &mdash; no real money involved &middot; SentinelIQ &middot; Powered by Amazon Nova
      </p>
    </div>
    """

    msg.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info("trade_draft_email_sent", to=to_email, ticker=ticker, action=action)
    except Exception as exc:
        logger.error("trade_draft_email_failed", error=str(exc), to=to_email)


async def send_full_alert_email(
    to_email: str,
    action_card,  # ActionCard
    trade_action: str,
    trade_token: str = "",
    chart_b64: str = "",
    chart_analysis: str = "",
    sec_filing_b64: str = "",
) -> None:
    """Single combined email: alert details + Nova reasoning + sources + trade form."""
    if not settings.smtp_user or not settings.smtp_password:
        return

    nova = action_card.nova_analysis or {}
    sentiment = action_card.sentiment or {}
    sentiment_label = sentiment.get("label", "neutral")
    sentiment_color = "#10B981" if sentiment_label == "positive" else "#EF4444" if sentiment_label == "negative" else "#F59E0B"
    confidence = nova.get("confidence_level", 0.5)
    trade_color = "#10B981" if trade_action == "buy" else "#EF4444"

    # Risk factors
    risk_html = " ".join(
        f'<span style="background:#fee2e2;color:#dc2626;padding:3px 10px;border-radius:4px;font-size:12px;margin:2px;display:inline-block;">{r}</span>'
        for r in nova.get("risk_factors", [])[:4]
    )

    # Recommended actions
    actions_html = " ".join(
        f'<span style="background:#dcfce7;color:#16a34a;padding:3px 10px;border-radius:4px;font-size:12px;margin:2px;display:inline-block;">{a}</span>'
        for a in nova.get("recommended_actions", [])[:3]
    )

    # Similar historical events
    events_html = ""
    for ev in (action_card.similar_events or [])[:3]:
        match_pct = int((ev.get("similarity_score", ev.get("score", 0))) * 100)
        events_html += f"""
        <tr>
          <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:12px;color:#475569;">{ev.get("date","")}</td>
          <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:12px;color:#0f1117;font-weight:500;">{ev.get("ticker","")}</td>
          <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:12px;color:#334155;">{ev.get("event","")}</td>
          <td style="padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:12px;color:#10B981;text-align:right;">{match_pct}%</td>
        </tr>"""

    # Source links
    sources_html = ""
    for link in (action_card.source_links or [])[:3]:
        if link:
            sources_html += f'<a href="{link}" style="color:#3b82f6;font-size:12px;display:block;margin-bottom:4px;word-break:break-all;">{link}</a>'

    # SEC EDGAR filings snapshot section
    sec_png_bytes = base64.b64decode(sec_filing_b64) if sec_filing_b64 else None
    sec_section_html = ""
    if sec_png_bytes:
        sec_section_html = f"""
      <div style="margin-bottom:20px;">
        <p style="color:#64748b;font-size:11px;font-weight:600;letter-spacing:0.08em;margin:0 0 10px;">
          SEC EDGAR &mdash; RECENT 8-K FILINGS &mdash; ${action_card.ticker}
        </p>
        <img src="cid:sec_img" style="width:100%;max-width:580px;display:block;border-radius:8px;border:1px solid #e2e8f0;"
             alt="{action_card.ticker} SEC EDGAR filings" />
        <p style="color:#94a3b8;font-size:11px;margin:6px 0 0;">
          Captured live from SEC EDGAR via Nova Act &middot; sec.gov
        </p>
      </div>"""

    # TradingView chart section — use cid: for Gmail compatibility (data: URIs are blocked)
    chart_png_bytes = base64.b64decode(chart_b64) if chart_b64 else None
    chart_section_html = ""
    if chart_png_bytes:
        analysis_para = (
            f'<p style="color:#475569;font-size:13px;line-height:1.7;margin:12px 0 0;">{chart_analysis}</p>'
            if chart_analysis else ""
        )
        chart_section_html = f"""
      <div style="margin-bottom:20px;">
        <p style="color:#64748b;font-size:11px;font-weight:600;letter-spacing:0.08em;margin:0 0 10px;">
          TRADINGVIEW CHART &mdash; ${action_card.ticker}
        </p>
        <img src="cid:chart_img" style="width:100%;max-width:580px;display:block;border-radius:8px;border:1px solid #e2e8f0;"
             alt="{action_card.ticker} TradingView chart" />
        {analysis_para}
      </div>"""

    # Trade suggestion card (HTML table — Gmail-safe, replaces SVG which gets stripped)
    trade_color_local = "#10B981" if trade_action == "buy" else "#EF4444"
    screenshot_html = f"""
    <table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;background:#f8fafc;">
      <tr>
        <td style="color:#64748b;font-size:12px;padding:10px 16px;border-bottom:1px solid #e2e8f0;">SYMBOL</td>
        <td style="color:#0f1117;font-size:13px;font-weight:700;text-align:right;padding:10px 16px;border-bottom:1px solid #e2e8f0;">${action_card.ticker}</td>
      </tr>
      <tr style="background:#ffffff;">
        <td style="color:#64748b;font-size:12px;padding:10px 16px;border-bottom:1px solid #e2e8f0;">SIDE</td>
        <td style="color:{trade_color_local};font-size:13px;font-weight:700;text-align:right;padding:10px 16px;border-bottom:1px solid #e2e8f0;">{trade_action.upper()}</td>
      </tr>
      <tr>
        <td style="color:#64748b;font-size:12px;padding:10px 16px;border-bottom:1px solid #e2e8f0;">ORDER TYPE</td>
        <td style="color:#0f1117;font-size:13px;font-weight:600;text-align:right;padding:10px 16px;border-bottom:1px solid #e2e8f0;">Market</td>
      </tr>
      <tr style="background:#ffffff;">
        <td style="color:#64748b;font-size:12px;padding:10px 16px;">QUANTITY</td>
        <td style="color:#0f1117;font-size:13px;font-weight:600;text-align:right;padding:10px 16px;">1 share</td>
      </tr>
    </table>"""

    # Use multipart/related so we can attach the chart PNG as an inline CID image
    msg_related = MIMEMultipart("related")
    msg_alt = MIMEMultipart("alternative")
    msg_related.attach(msg_alt)
    if chart_png_bytes:
        img_part = MIMEImage(chart_png_bytes, "png")
        img_part.add_header("Content-ID", "<chart_img>")
        img_part.add_header("Content-Disposition", "inline", filename=f"{action_card.ticker}_chart.png")
        msg_related.attach(img_part)
    if sec_png_bytes:
        sec_part = MIMEImage(sec_png_bytes, "png")
        sec_part.add_header("Content-ID", "<sec_img>")
        sec_part.add_header("Content-Disposition", "inline", filename=f"{action_card.ticker}_sec.png")
        msg_related.attach(sec_part)

    msg_related["Subject"] = f"SentinelIQ Alert — ${action_card.ticker} {sentiment_label.upper()} | {nova.get('event_summary','')[:60]}"
    msg_related["From"] = settings.smtp_from or settings.smtp_user
    msg_related["To"] = to_email

    html = f"""
    <div style="font-family:Inter,system-ui,sans-serif;background:#ffffff;padding:24px;max-width:620px;margin:auto;color:#0f1117;">

      <!-- Header (table layout — Gmail-safe, no flexbox) -->
      <table style="margin-bottom:20px;" cellpadding="0" cellspacing="0">
        <tr>
          <td><span style="background:#10B981;color:#fff;font-weight:700;font-size:13px;padding:4px 12px;border-radius:6px;">SentinelIQ</span></td>
          <td style="padding-left:10px;"><span style="color:#64748b;font-size:13px;">Market Alert &middot; {action_card.timestamp[:10]}</span></td>
        </tr>
      </table>

      <!-- Title -->
      <h2 style="margin:0 0 6px;font-size:22px;">${action_card.ticker} &nbsp;<span style="color:{sentiment_color};">{sentiment_label.upper()}</span></h2>
      <p style="color:#475569;font-size:14px;line-height:1.6;margin:0 0 20px;">{nova.get("event_summary","")}</p>

      <!-- Stats row -->
      <table style="width:100%;border-collapse:collapse;background:#f8fafc;border-radius:8px;margin-bottom:20px;">
        <tr>
          <td style="padding:12px 16px;border-right:1px solid #e2e8f0;">
            <p style="color:#64748b;font-size:11px;margin:0 0 2px;">NOVA CONFIDENCE</p>
            <p style="color:#0f1117;font-size:18px;font-weight:700;margin:0;">{int(confidence*100)}%</p>
          </td>
          <td style="padding:12px 16px;border-right:1px solid #e2e8f0;">
            <p style="color:#64748b;font-size:11px;margin:0 0 2px;">SOURCE CREDIBILITY</p>
            <p style="color:#0f1117;font-size:18px;font-weight:700;margin:0;">{int(action_card.credibility_score*100)}%</p>
          </td>
          <td style="padding:12px 16px;">
            <p style="color:#64748b;font-size:11px;margin:0 0 2px;">TIME HORIZON</p>
            <p style="color:#0f1117;font-size:18px;font-weight:700;margin:0;">{nova.get("time_horizon","intraday").upper()}</p>
          </td>
        </tr>
      </table>

      <!-- Primary driver + sector -->
      <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
        <tr>
          <td style="width:50%;padding-right:12px;vertical-align:top;">
            <p style="color:#64748b;font-size:11px;margin:0 0 4px;">PRIMARY DRIVER</p>
            <p style="color:#0f1117;font-size:13px;font-weight:500;margin:0;">{nova.get("primary_driver","")}</p>
          </td>
          <td style="width:50%;vertical-align:top;">
            <p style="color:#64748b;font-size:11px;margin:0 0 4px;">SECTOR IMPACT</p>
            <p style="color:#0f1117;font-size:13px;font-weight:500;margin:0;">{nova.get("sector_impact","")}</p>
          </td>
        </tr>
      </table>

      <!-- Risk factors -->
      <p style="color:#64748b;font-size:11px;margin:0 0 6px;">RISK FACTORS</p>
      <div style="margin-bottom:16px;">{risk_html}</div>

      <!-- Recommended actions -->
      <p style="color:#64748b;font-size:11px;margin:0 0 6px;">RECOMMENDED ACTIONS</p>
      <div style="margin-bottom:20px;">{actions_html}</div>

      <!-- Similar historical events -->
      {"" if not events_html else f'''
      <p style="color:#64748b;font-size:11px;margin:0 0 8px;">SIMILAR HISTORICAL EVENTS</p>
      <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
        <tr style="background:#f8fafc;">
          <th style="padding:6px 0;font-size:11px;color:#94a3b8;text-align:left;font-weight:500;">DATE</th>
          <th style="padding:6px 0;font-size:11px;color:#94a3b8;text-align:left;font-weight:500;">TICKER</th>
          <th style="padding:6px 0;font-size:11px;color:#94a3b8;text-align:left;font-weight:500;">EVENT</th>
          <th style="padding:6px 0;font-size:11px;color:#94a3b8;text-align:right;font-weight:500;">MATCH</th>
        </tr>
        {events_html}
      </table>'''}

      <!-- Sources -->
      {"" if not sources_html else f'''
      <p style="color:#64748b;font-size:11px;margin:0 0 6px;">SOURCES</p>
      <div style="margin-bottom:20px;">{sources_html}</div>'''}

      <!-- SEC EDGAR Filings (Nova Act screenshot) -->
      {sec_section_html}

      <!-- TradingView Chart (Nova Act screenshot + multimodal analysis) -->
      {chart_section_html}

      <!-- Trade form -->
      <div style="border-top:1px solid #e2e8f0;padding-top:20px;margin-top:4px;">
        <p style="color:#64748b;font-size:11px;margin:0 0 8px;">NOVA ACT — SUGGESTED TRADE (<span style="color:{trade_color};font-weight:600;">{trade_action.upper()}</span> ${action_card.ticker})</p>
        {screenshot_html}
        <p style="color:#94a3b8;font-size:11px;margin-top:8px;">&#9889; Nova Act prepared this order &mdash; click below to execute on Alpaca paper trading.</p>
      </div>

      <!-- Proceed with Trade button -->
      {f'''
      <div style="text-align:center;margin-top:24px;">
        <a href="{settings.app_base_url}/api/v1/trade/confirm?token={trade_token}"
           style="display:inline-block;background:{trade_color};color:#ffffff;font-weight:700;
                  font-size:14px;padding:14px 32px;border-radius:8px;text-decoration:none;
                  letter-spacing:0.3px;">
          &#9889; Proceed with Trade &mdash; {trade_action.upper()} ${action_card.ticker}
        </a>
        <p style="color:#94a3b8;font-size:11px;margin-top:10px;">
          Link expires in 1 hour &middot; Paper trade only, no real money
        </p>
      </div>''' if trade_token else ''}

      <p style="color:#cbd5e1;font-size:10px;text-align:center;margin-top:24px;">
        SentinelIQ · Autonomous Market Intelligence · Powered by Amazon Nova
      </p>
    </div>
    """

    msg_alt.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            msg_related,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info("full_alert_email_sent", to=to_email, ticker=action_card.ticker)
    except Exception as exc:
        logger.error("full_alert_email_failed", error=str(exc), to=to_email)


async def send_alert_email(
    to_email: str,
    ticker: str,
    event_summary: str,
    primary_driver: str,
    confidence: float,
    sentiment: str,
    risk_factors: list,
    recommended_actions: list,
) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        return

    sentiment_color = "#10B981" if sentiment == "positive" else "#EF4444" if sentiment == "negative" else "#F59E0B"
    risk_html = "".join(f'<span style="background:#fee2e2;color:#dc2626;padding:2px 8px;border-radius:4px;font-size:12px;margin:2px;">{r}</span>' for r in risk_factors[:3])
    actions_html = "".join(f'<span style="background:#dcfce7;color:#16a34a;padding:2px 8px;border-radius:4px;font-size:12px;margin:2px;">{a}</span>' for a in recommended_actions[:2])

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"SentinelIQ Alert — ${ticker} {sentiment.upper()} signal detected"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email

    html = f"""
    <div style="font-family:Inter,system-ui,sans-serif;background:#ffffff;padding:32px;max-width:600px;margin:auto;">
      <div style="margin-bottom:20px;">
        <span style="background:#10B981;color:#fff;font-weight:700;font-size:13px;padding:4px 10px;border-radius:6px;margin-right:12px;">SentinelIQ</span>
        <span style="color:#64748b;font-size:13px;">New Market Alert</span>
      </div>

      <h2 style="color:#0f1117;margin:0 0 8px;">${ticker} <span style="color:{sentiment_color};">{sentiment.upper()}</span></h2>
      <p style="color:#334155;font-size:14px;line-height:1.6;margin:0 0 20px;">{event_summary}</p>

      <div style="background:#f8fafc;border-radius:8px;padding:16px;margin-bottom:20px;">
        <p style="color:#64748b;font-size:11px;margin:0 0 4px;">PRIMARY DRIVER</p>
        <p style="color:#0f1117;font-size:14px;margin:0 0 12px;font-weight:500;">{primary_driver}</p>
        <p style="color:#64748b;font-size:11px;margin:0 0 4px;">NOVA CONFIDENCE</p>
        <div style="background:#e2e8f0;border-radius:4px;height:6px;margin-bottom:4px;">
          <div style="background:#10B981;width:{int(confidence*100)}%;height:6px;border-radius:4px;"></div>
        </div>
        <p style="color:#0f1117;font-size:12px;margin:0;">{int(confidence*100)}%</p>
      </div>

      <p style="color:#64748b;font-size:11px;margin:0 0 6px;">RISK FACTORS</p>
      <div style="margin-bottom:16px;">{risk_html}</div>

      <p style="color:#64748b;font-size:11px;margin:0 0 6px;">RECOMMENDED ACTIONS</p>
      <div style="margin-bottom:24px;">{actions_html}</div>

      <p style="color:#94a3b8;font-size:11px;text-align:center;">
        SentinelIQ · Autonomous Market Intelligence · Powered by Amazon Nova
      </p>
    </div>
    """

    msg.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info("alert_email_sent", to=to_email, ticker=ticker)
    except Exception as exc:
        logger.error("alert_email_failed", error=str(exc), to=to_email)


async def send_trade_confirmation_email(
    to_email: str,
    ticker: str,
    action: str,
    shares: int,
    est_price: float = 0.0,
    est_total: float = 0.0,
    order_id: str = "",
    # kept for backwards-compat with callers that still pass these
    screenshot_b64: str = "",
    is_mock: bool = True,
) -> None:
    """Confirmation email sent after user clicks 'Proceed with Trade'."""
    if not settings.smtp_user or not settings.smtp_password:
        return

    action_color = "#10B981" if action == "buy" else "#EF4444"
    mock_note = " (paper/mock)" if is_mock else " (paper trading)"
    price_str = f"${est_price:,.2f}" if est_price else "Market"
    total_str = f"${est_total:,.2f}" if est_total else "Pending fill"
    order_id_str = order_id[:8].upper() if order_id else "—"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"SentinelIQ — Trade Confirmed: {action.upper()} {ticker}"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email

    html = f"""
    <div style="font-family:Inter,system-ui,sans-serif;background:#ffffff;padding:24px;max-width:620px;margin:auto;color:#0f1117;">
      <table style="margin-bottom:20px;" cellpadding="0" cellspacing="0">
        <tr>
          <td><span style="background:#10B981;color:#fff;font-weight:700;font-size:13px;padding:4px 12px;border-radius:6px;">SentinelIQ</span></td>
          <td style="padding-left:10px;"><span style="color:#64748b;font-size:13px;">Trade Confirmation</span></td>
        </tr>
      </table>

      <!-- Success card -->
      <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:20px 24px;margin-bottom:24px;text-align:center;">
        <p style="color:#16a34a;font-size:32px;margin:0 0 8px;">&#10003;</p>
        <h2 style="margin:0 0 8px;font-size:20px;color:#0f1117;">Order Submitted{mock_note}</h2>
        <p style="color:#475569;font-size:14px;margin:0;">
          <strong style="color:{action_color};">{action.upper()}</strong>
          {shares} share{'s' if shares != 1 else ''} of
          <strong>${ticker}</strong> &mdash; Market Order &mdash; Alpaca Paper Trading
        </p>
      </div>

      <!-- Order details -->
      <p style="color:#64748b;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 10px;">ORDER DETAILS</p>
      <table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:24px;">
        <tr style="background:#f8fafc;">
          <td style="color:#64748b;font-size:12px;padding:11px 16px;border-bottom:1px solid #e2e8f0;">Order ID</td>
          <td style="color:#0f1117;font-size:13px;font-weight:600;font-family:monospace;text-align:right;padding:11px 16px;border-bottom:1px solid #e2e8f0;">{order_id_str}</td>
        </tr>
        <tr>
          <td style="color:#64748b;font-size:12px;padding:11px 16px;border-bottom:1px solid #e2e8f0;">Symbol</td>
          <td style="color:#0f1117;font-size:13px;font-weight:700;text-align:right;padding:11px 16px;border-bottom:1px solid #e2e8f0;">${ticker}</td>
        </tr>
        <tr style="background:#f8fafc;">
          <td style="color:#64748b;font-size:12px;padding:11px 16px;border-bottom:1px solid #e2e8f0;">Side</td>
          <td style="color:{action_color};font-size:13px;font-weight:700;text-align:right;padding:11px 16px;border-bottom:1px solid #e2e8f0;">{action.upper()}</td>
        </tr>
        <tr>
          <td style="color:#64748b;font-size:12px;padding:11px 16px;border-bottom:1px solid #e2e8f0;">Quantity</td>
          <td style="color:#0f1117;font-size:13px;font-weight:600;text-align:right;padding:11px 16px;border-bottom:1px solid #e2e8f0;">{shares} share{'s' if shares != 1 else ''}</td>
        </tr>
        <tr style="background:#f8fafc;">
          <td style="color:#64748b;font-size:12px;padding:11px 16px;border-bottom:1px solid #e2e8f0;">Fill Price</td>
          <td style="color:#0f1117;font-size:13px;font-weight:600;text-align:right;padding:11px 16px;border-bottom:1px solid #e2e8f0;">{price_str}</td>
        </tr>
        <tr>
          <td style="color:#64748b;font-size:12px;padding:11px 16px;">Est. Total</td>
          <td style="color:{action_color};font-size:16px;font-weight:700;text-align:right;padding:11px 16px;">{total_str}</td>
        </tr>
      </table>

      <p style="color:#94a3b8;font-size:11px;text-align:center;">
        Paper trade only &mdash; no real money involved &middot; Powered by Nova Act &amp; SentinelIQ
      </p>
    </div>
    """

    msg.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info("trade_confirmation_email_sent", to=to_email, ticker=ticker, action=action)
    except Exception as exc:
        logger.error("trade_confirmation_email_failed", error=str(exc), to=to_email)
