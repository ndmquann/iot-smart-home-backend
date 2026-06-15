"""
report_gen.py
=============
Stateless generation helpers.  Called on-demand from the report endpoint.

PDF  – reportlab Platypus + Graphics (bar chart, pie chart)
CSV  – stdlib csv, returned as StringIO for StreamingResponse
"""
import io
import csv
from datetime import date
from typing import List, Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak, KeepTogether
)
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

from app.schemas.report import ReportSummary

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

FONT_DIR = os.path.join(os.path.dirname(__file__), 'assets', 'font')
pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")

# ==========================================
# PALETTE
# ==========================================
C_NAVY   = colors.HexColor('#2C3E50')
C_BLUE   = colors.HexColor('#4A90D9')
C_GREEN  = colors.HexColor('#27AE60')
C_PURPLE = colors.HexColor('#8E44AD')
C_ORANGE = colors.HexColor('#E67E22')
C_RED    = colors.HexColor('#E74C3C')
C_LIGHT  = colors.HexColor('#F7F9FC')
C_BORDER = colors.HexColor('#BDC3C7')
C_GRID   = colors.HexColor('#E0E0E0')
C_WHITE  = colors.white


# ==========================================
# CHART HELPERS
# ==========================================

def _bar_chart(data: Dict[str, int], width: float = 380, height: float = 140) -> Drawing:
    """Vertical bar chart from a {label: value} dict."""
    drawing = Drawing(width, height)
    if not data:
        return drawing

    chart = VerticalBarChart()
    chart.x = 45
    chart.y = 25
    chart.width = width - 60
    chart.height = height - 40
    chart.data = [list(data.values())]
    chart.categoryAxis.categoryNames = list(data.keys())
    chart.categoryAxis.labels.angle = 0
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.dy = -4
    chart.bars[0].fillColor = C_BLUE
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontSize = 8
    drawing.add(chart)
    return drawing


def _pie_chart(data: Dict[str, int], width: float = 260, height: float = 160) -> Drawing:
    """Side-label pie chart from a {label: value} dict. Skips zero-value slices."""
    drawing = Drawing(width, height)
    filtered = {k: v for k, v in data.items() if v > 0}
    if not filtered:
        return drawing

    palette = [C_BLUE, C_RED, C_GREEN, C_ORANGE, C_PURPLE]

    pie = Pie()
    pie.x = 20
    pie.y = 20
    pie.width = 110
    pie.height = 110
    pie.data = list(filtered.values())
    pie.labels = [f"{k} ({v})" for k, v in filtered.items()]
    pie.sideLabels = True
    pie.sideLabelsOffset = 0.1
    for i, c in enumerate(palette[:len(pie.data)]):
        pie.slices[i].fillColor = c
        pie.slices[i].strokeColor = C_WHITE
        pie.slices[i].strokeWidth = 1
    drawing.add(pie)
    return drawing


# ==========================================
# TABLE STYLE FACTORY
# ==========================================

def _header_style(header_color) -> TableStyle:
    return TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR',     (0, 0), (-1, 0), C_WHITE),
        ('FONTNAME',      (0, 0), (-1, 0), 'DejaVu-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
        ('BOX',           (0, 0), (-1, -1), 0.8, C_BORDER),
        ('INNERGRID',     (0, 0), (-1, -1), 0.4, C_GRID),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
    ])


# ==========================================
# PDF GENERATION
# ==========================================

def generate_pdf(report: ReportSummary) -> io.BytesIO:
    """
    Build a multi-page A4 PDF from a ReportSummary.

    Structure
    ---------
    Page 1 : Cover – KPI summary cards
    Page 1 : Section 1 – Zone table
    Page 2 : Section 2 – Device table + status pie chart
    Page 3 : Section 3 – Automation table
    Page 3 : Section 4 – Activity bar chart + breakdown table
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Smart Home Report",
    )

    styles = getSampleStyleSheet()
    T  = ParagraphStyle('RPT_Title', parent=styles['Title'],   fontSize=22, textColor=C_NAVY,   spaceAfter=4)
    H1 = ParagraphStyle('RPT_H1',   parent=styles['Heading1'], fontSize=13, textColor=C_NAVY,   spaceAfter=4,  spaceBefore=10)
    H2 = ParagraphStyle('RPT_H2',   parent=styles['Heading2'], fontSize=10, textColor=C_BLUE,   spaceAfter=3)
    N  = ParagraphStyle('RPT_N',    parent=styles['Normal'],   fontSize=9,  textColor=C_NAVY)
    SM = ParagraphStyle('RPT_SM',   parent=styles['Normal'],   fontSize=8,  textColor=colors.HexColor('#555555'))

    story = []

    # ──────────────────────────────────────────
    # COVER
    # ──────────────────────────────────────────
    story.append(Paragraph("Smart Home IoT — Report", T))
    story.append(Paragraph(
        f"Home ID: {report.home_id}  |  "
        f"Period: {report.date_from} to {report.date_to} ({report.days} days)  |  "
        f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M')}",
        SM
    ))
    story.append(Spacer(1, 0.4 * cm))

    # KPI summary strip
    kpi_data = [
        ['Floors', 'Rooms', 'Devices', 'Schedules', 'Thresholds', 'Logs (period)'],
        [
            str(report.total_floors),
            str(report.total_zones),
            str(report.total_devices),
            str(report.total_schedules),
            str(report.total_thresholds),
            str(report.total_logs_in_period),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[2.7 * cm] * 6)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), C_NAVY),
        ('TEXTCOLOR',     (0, 0), (-1, 0), C_WHITE),
        ('FONTNAME',      (0, 0), (-1, 0), 'DejaVu-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 8),
        ('FONTNAME',      (0, 1), (-1, 1), 'DejaVu-Bold'),
        ('FONTSIZE',      (0, 1), (-1, 1), 18),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND',    (0, 1), (-1, 1), colors.HexColor('#EBF5FB')),
        ('BOX',           (0, 0), (-1, -1), 0.8, C_BORDER),
        ('INNERGRID',     (0, 0), (-1, -1), 0.4, C_BORDER),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.6 * cm))

    # ──────────────────────────────────────────
    # SECTION 1 — ZONES
    # ──────────────────────────────────────────
    story.append(Paragraph("1. Zone Summary", H1))
    story.append(Paragraph(
        f"{report.total_floors} floor(s)  ·  {report.total_zones} room(s) registered.", N
    ))
    story.append(Spacer(1, 0.25 * cm))

    zone_rows = [['Floor', 'Room', 'Devices']]
    for floor in report.floors:
        for zone in floor.rooms:
            zone_rows.append([str(floor.floor), zone.room, str(zone.device_count)])

    zone_table = Table(zone_rows, colWidths=[3 * cm, 11 * cm, 2.6 * cm])
    zone_table.setStyle(_header_style(C_BLUE))
    zone_table.setStyle(TableStyle([
        *_header_style(C_BLUE).getCommands(),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
    ]))
    story.append(zone_table)

    # ──────────────────────────────────────────
    # SECTION 2 — DEVICES
    # ──────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("2. Device Summary", H1))

    # device stats strip
    dev_stats = [
        ['Total', 'Sensors', 'Controllers', 'ON', 'OFF'],
        [
            str(report.total_devices),
            str(report.total_sensors),
            str(report.total_controllers),
            str(report.devices_on),
            str(report.devices_off),
        ]
    ]
    dev_stat_table = Table(dev_stats, colWidths=[3.36 * cm] * 5)
    dev_stat_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), C_GREEN),
        ('TEXTCOLOR',     (0, 0), (-1, 0), C_WHITE),
        ('FONTNAME',      (0, 0), (-1, 0), 'DejaVu-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 8),
        ('FONTNAME',      (0, 1), (-1, 1), 'DejaVu-Bold'),
        ('FONTSIZE',      (0, 1), (-1, 1), 16),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND',    (0, 1), (-1, 1), colors.HexColor('#EAFAF1')),
        ('BOX',           (0, 0), (-1, -1), 0.8, C_BORDER),
        ('INNERGRID',     (0, 0), (-1, -1), 0.4, C_BORDER),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(dev_stat_table)
    story.append(Spacer(1, 0.3 * cm))

    # status pie chart
    status_data = {'ON': report.devices_on, 'OFF': report.devices_off}
    type_data   = {'Sensors': report.total_sensors, 'Controllers': report.total_controllers}

    chart_row = Table(
        [[_pie_chart(status_data), _pie_chart(type_data, width=280)]],
        colWidths=[8.3 * cm, 8.3 * cm]
    )
    pie_labels = Table(
        [[Paragraph("Status Breakdown", H2), Paragraph("Type Breakdown", H2)]],
        colWidths=[8.3 * cm, 8.3 * cm]
    )
    story.append(pie_labels)
    story.append(chart_row)
    story.append(Spacer(1, 0.3 * cm))

    # device detail table
    dev_rows = [['Name', 'Type', 'Status', 'Floor', 'Room', 'Sensor Value']]
    for d in report.devices:
        dev_rows.append([
            d.name,
            d.type.capitalize(),
            d.status,
            str(d.floor),
            d.room,
            str(round(d.current_value, 2)) if d.current_value is not None else '—',
        ])

    dev_table = Table(dev_rows, colWidths=[4.5 * cm, 2.4 * cm, 1.8 * cm, 1.5 * cm, 3.2 * cm, 3.2 * cm])
    dev_table.setStyle(TableStyle([
        *_header_style(C_GREEN).getCommands(),
        ('ALIGN', (2, 0), (5, -1), 'CENTER'),
    ]))
    story.append(dev_table)

    # ──────────────────────────────────────────
    # SECTION 3 — AUTOMATION
    # ──────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("3. Automation Summary", H1))
    story.append(Paragraph(
        f"{report.total_schedules} schedule(s)  ·  {report.total_thresholds} threshold(s) configured.", N
    ))
    story.append(Spacer(1, 0.25 * cm))

    auto_rows = [['Name', 'Type', 'Action', 'Applied To', 'Triggers (period)']]
    for a in report.automations:
        auto_rows.append([
            a.name,
            a.type.capitalize(),
            a.action,
            a.applied_devices,
            str(a.trigger_count),
        ])

    auto_table = Table(auto_rows, colWidths=[3.8 * cm, 2.4 * cm, 2 * cm, 5.4 * cm, 3 * cm])
    auto_table.setStyle(TableStyle([
        *_header_style(C_PURPLE).getCommands(),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
    ]))
    story.append(auto_table)

    # ──────────────────────────────────────────
    # SECTION 4 — ACTIVITY
    # ──────────────────────────────────────────
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph("4. Activity Summary", H1))
    story.append(Paragraph(
        f"{report.total_logs_in_period} log entries recorded in this period.", N
    ))
    story.append(Spacer(1, 0.25 * cm))

    act_rows = [['Log Type', 'Count']]
    for a in report.activity_breakdown:
        act_rows.append([a.type.title(), str(a.count)])

    act_table = Table(act_rows, colWidths=[10 * cm, 6.6 * cm])
    act_table.setStyle(TableStyle([
        *_header_style(C_ORANGE).getCommands(),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    story.append(act_table)

    if report.activity_breakdown:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Activity Distribution", H2))
        chart_data = {a.type: a.count for a in report.activity_breakdown}
        story.append(_bar_chart(chart_data))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ==========================================
# CSV GENERATION
# ==========================================

def generate_csv_sensors(records: List[Dict]) -> io.StringIO:
    """
    CSV of time-series sensor readings.
    Columns: device_name, floor, room, value, timestamp
    """
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=['device_name', 'floor', 'room', 'value', 'timestamp']
    )
    writer.writeheader()
    for r in records:
        writer.writerow({
            'device_name': r['device_name'],
            'floor':       r['floor'],
            'room':        r['room'],
            'value':       r['value'],
            'timestamp':   r['timestamp'].isoformat() if r['timestamp'] else '',
        })
    output.seek(0)
    return output


def generate_csv_logs(records: List[Dict]) -> io.StringIO:
    """
    CSV of activity log entries.
    Columns: id, type, description, timestamp
    """
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=['id', 'type', 'description', 'timestamp']
    )
    writer.writeheader()
    for r in records:
        writer.writerow({
            'id':          r['id'],
            'type':        r['type'],
            'description': r['description'],
            'timestamp':   r['timestamp'].isoformat() if r['timestamp'] else '',
        })
    output.seek(0)
    return output