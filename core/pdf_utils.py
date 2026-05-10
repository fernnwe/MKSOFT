import io
from datetime import datetime
from django.db.models import Sum
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus.flowables import HRFlowable


COLORS = {
    "primary": colors.HexColor("#6750A4"),
    "primary_light": colors.HexColor("#EADDFF"),
    "secondary": colors.HexColor("#625B71"),
    "surface": colors.HexColor("#FFFBFE"),
    "on_surface": colors.HexColor("#1C1B1F"),
    "on_surface_variant": colors.HexColor("#49454F"),
    "outline_variant": colors.HexColor("#CAC4D0"),
    "success": colors.HexColor("#386A20"),
    "success_light": colors.HexColor("#C4F0A3"),
    "error": colors.HexColor("#BA1A1A"),
    "error_light": colors.HexColor("#FFDAD6"),
    "white": colors.white,
    "light_gray": colors.HexColor("#F5F5F5"),
    "row_alt": colors.HexColor("#F7F2FA"),
    "header_bg": colors.HexColor("#6750A4"),
    "header_text": colors.white,
}


def _header_footer(canvas, doc, title, restaurant_name, currency_symbol):
    w, h = A4
    canvas.saveState()

    canvas.setFillColor(COLORS["primary"])
    canvas.rect(0, h - 28*mm, w, 28*mm, fill=1, stroke=0)

    canvas.setFillColor(COLORS["white"])
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(15*mm, h - 14*mm, restaurant_name)

    canvas.setFont("Helvetica", 10)
    canvas.drawRightString(w - 15*mm, h - 14*mm, title)

    canvas.setFillColor(COLORS["on_surface_variant"])
    canvas.setFont("Helvetica", 8)
    canvas.drawString(15*mm, h - 22*mm, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    canvas.setStrokeColor(COLORS["outline_variant"])
    canvas.setLineWidth(0.5)
    canvas.line(15*mm, 20*mm, w - 15*mm, 20*mm)

    canvas.setFillColor(COLORS["on_surface_variant"])
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w / 2, 10*mm, f"{restaurant_name} | {currency_symbol}")
    canvas.drawRightString(w - 15*mm, 10*mm, f"Pagina {doc.page}")

    canvas.restoreState()


def generate_inventario_pdf(inventario_qs, restaurant_name, currency_symbol):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=32*mm,
        bottomMargin=25*mm,
        leftMargin=15*mm,
        rightMargin=15*mm,
        title="Reporte de Inventario",
    )

    elements = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=COLORS["primary"],
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="SectionSub",
        fontName="Helvetica",
        fontSize=10,
        textColor=COLORS["on_surface_variant"],
        spaceAfter=12,
    ))

    elements.append(Paragraph("Reporte de Inventario", styles["SectionTitle"]))
    elements.append(Paragraph(f"Total: {inventario_qs.count()} ingredientes registrados", styles["SectionSub"]))

    col_widths = [40*mm, 30*mm, 25*mm, 28*mm, 25*mm, 32*mm]
    data = [
        ["Ingrediente", "Categoria", "Stock", "Unidad", "Costo Unit.", "Valor Total"]
    ]

    total_valor = 0
    alertas = 0
    for inv in inventario_qs.select_related("ingrediente"):
        costo = float(inv.costo_unitario) or 0
        stock = float(inv.cantidad_actual) or 0
        valor = stock * costo
        total_valor += valor
        if inv.bajo_stock:
            alertas += 1
        data.append([
            inv.ingrediente.nombre,
            inv.ingrediente.categoria or "-",
            f"{stock:.2f}",
            inv.get_unidad_display(),
            f"{currency_symbol}{costo:.2f}",
            f"{currency_symbol}{valor:.2f}",
        ])

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["header_bg"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["header_text"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLORS["outline_variant"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLORS["row_alt"], COLORS["white"]]),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
    ]))

    for i in range(1, len(data)):
        inv = inventario_qs[i - 1]
        if inv.bajo_stock:
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FFDAD6")),
            ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    summary_data = [
        ["Resumen", ""],
        ["Total ingredientes", str(inventario_qs.count())],
        ["Valor total del inventario", f"{currency_symbol}{total_valor:.2f}"],
        ["Alertas de stock bajo", str(alertas)],
    ]
    summary_table = Table(summary_data, colWidths=[100*mm, 80*mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary_light"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["primary"]),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLORS["outline_variant"]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, "Reporte de Inventario", restaurant_name, currency_symbol),
              onLaterPages=lambda c, d: _header_footer(c, d, "Reporte de Inventario", restaurant_name, currency_symbol))

    buffer.seek(0)
    return buffer


def generate_compras_pdf(compras_qs, restaurant_name, currency_symbol):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=32*mm,
        bottomMargin=25*mm,
        leftMargin=15*mm,
        rightMargin=15*mm,
        title="Reporte de Compras",
    )

    elements = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=COLORS["primary"],
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="SectionSub",
        fontName="Helvetica",
        fontSize=10,
        textColor=COLORS["on_surface_variant"],
        spaceAfter=12,
    ))

    total_compras = 0
    total_items = 0
    for compra in compras_qs:
        total_compras += compra.total
        total_items += compra.items.count()

    elements.append(Paragraph("Reporte de Compras", styles["SectionTitle"]))
    elements.append(Paragraph(f"Total: {compras_qs.count()} compras | {total_items} items", styles["SectionSub"]))

    for compra in compras_qs.prefetch_related("items__ingrediente"):
        items_data = [["#", "Ingrediente", "Cantidad", "Costo Unit.", "Subtotal"]]
        compra_total = 0
        for i, item in enumerate(compra.items.all(), 1):
            subtotal = float(item.cantidad) * float(item.costo_unitario)
            compra_total += subtotal
            items_data.append([
                str(i),
                item.ingrediente.nombre,
                f"{float(item.cantidad):.3f}",
                f"{currency_symbol}{float(item.costo_unitario):.2f}",
                f"{currency_symbol}{subtotal:.2f}",
            ])

        col_widths = [15*mm, 55*mm, 30*mm, 35*mm, 35*mm]
        items_data.append(["", "", "", "TOTAL:", f"{currency_symbol}{compra_total:.2f}"])

        items_table = Table(items_data, colWidths=col_widths)
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLORS["header_bg"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["header_text"]),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, COLORS["outline_variant"]),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [COLORS["row_alt"], COLORS["white"]]),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), COLORS["primary_light"]),
            ("TEXTCOLOR", (0, -1), (-1, -1), COLORS["primary"]),
        ]))

        estado_color = COLORS["success"] if compra.estado == "recibida" else (COLORS["error"] if compra.estado == "cancelada" else colors.orange)
        header_data = [
            [f"Compra: {compra.folio}", f"Fecha: {compra.fecha.strftime('%d/%m/%Y %H:%M')}"],
            [f"Proveedor: {compra.proveedor}", f"Estado: {compra.get_estado_display()}"],
        ]
        if compra.notas:
            header_data.append([f"Notas: {compra.notas}", ""])
        header_table = Table(header_data, colWidths=[90*mm, 80*mm])
        header_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, 0), COLORS["primary"]),
            ("TEXTCOLOR", (1, 1), (1, 1), estado_color),
            ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 1, COLORS["outline_variant"]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))

        elements.append(KeepTogether([header_table, items_table, Spacer(1, 10)]))

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, "Reporte de Compras", restaurant_name, currency_symbol),
              onLaterPages=lambda c, d: _header_footer(c, d, "Reporte de Compras", restaurant_name, currency_symbol))

    buffer.seek(0)
    return buffer


def generate_productos_pdf(productos_qs, restaurant_name, currency_symbol):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=32*mm,
        bottomMargin=25*mm,
        leftMargin=15*mm,
        rightMargin=15*mm,
        title="Reporte de Productos",
    )

    elements = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=COLORS["primary"],
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="SectionSub",
        fontName="Helvetica",
        fontSize=10,
        textColor=COLORS["on_surface_variant"],
        spaceAfter=12,
    ))

    total_productos = productos_qs.count()
    avg_precio = productos_qs.aggregate(total_precio=Sum("precio"))["total_precio"] or 0
    avg_precio = float(avg_precio) / total_productos if total_productos > 0 else 0

    elements.append(Paragraph("Reporte de Productos", styles["SectionTitle"]))
    elements.append(Paragraph(f"Total: {total_productos} productos | Precio promedio: {currency_symbol}{avg_precio:.2f}", styles["SectionSub"]))

    col_widths = [25*mm, 50*mm, 25*mm, 28*mm, 22*mm, 22*mm, 28*mm]
    data = [
        ["Codigo", "Nombre", "Categoria", "Tipo", "Costo", "Precio", "Margen"]
    ]

    for prod in productos_qs.select_related("categoria"):
        costo = float(prod.costo) or 0
        precio = float(prod.precio) or 0
        margen = f"{prod.margen_ganancia}%" if costo > 0 else "-"
        data.append([
            prod.codigo,
            prod.nombre,
            prod.categoria.nombre if prod.categoria else "-",
            prod.get_tipo_display(),
            f"{currency_symbol}{costo:.2f}",
            f"{currency_symbol}{precio:.2f}",
            margen,
        ])

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["header_bg"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["header_text"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLORS["outline_variant"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLORS["row_alt"], COLORS["white"]]),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
    ]))

    for i in range(1, len(data)):
        prod = productos_qs[i - 1]
        if not prod.disponible:
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FFE0E0")),
            ]))

    elements.append(table)

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, "Reporte de Productos", restaurant_name, currency_symbol),
              onLaterPages=lambda c, d: _header_footer(c, d, "Reporte de Productos", restaurant_name, currency_symbol))

    buffer.seek(0)
    return buffer


def generate_cierre_pdf(apertura_cerrada, facturas_pagadas, facturas_canceladas, compras_recibidas, ventas_por_metodo, total_ventas, total_compras, total_iva, total_servicio, total_descuentos, balance_neto, restaurant_name, currency_symbol, fecha):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=32*mm,
        bottomMargin=25*mm,
        leftMargin=15*mm,
        rightMargin=15*mm,
        title=f"Cierre de Caja - {fecha.strftime('%d/%m/%Y') if hasattr(fecha, 'strftime') else fecha}",
    )

    elements = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=COLORS["primary"],
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="SectionSub",
        fontName="Helvetica",
        fontSize=10,
        textColor=COLORS["on_surface_variant"],
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="CardTitle",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=COLORS["primary"],
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="DataLabel",
        fontName="Helvetica",
        fontSize=9,
        textColor=COLORS["on_surface_variant"],
    ))
    styles.add(ParagraphStyle(
        name="DataValue",
        fontName="Helvetica",
        fontSize=9,
        textColor=COLORS["on_surface"],
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        name="TotalValue",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=COLORS["primary"],
        alignment=TA_RIGHT,
    ))

    fecha_str = fecha.strftime("%d/%m/%Y") if hasattr(fecha, "strftime") else str(fecha)
    elements.append(Paragraph("Cierre de Caja", styles["SectionTitle"]))
    elements.append(Paragraph(f"{restaurant_name} | {fecha_str}", styles["SectionSub"]))

    aperturas_data = [["Apertura", "Hora", "Monto Inicial", "Efectivo Contado", "Diferencia"]]
    if apertura_cerrada:
        aperturas_data.append([
            f"#{apertura_cerrada.pk}",
            apertura_cerrada.fecha_apertura.strftime("%H:%M") if apertura_cerrada.fecha_apertura else "-",
            f"{currency_symbol}{apertura_cerrada.monto_inicial:.2f}",
            f"{currency_symbol}{apertura_cerrada.monto_cierre_efectivo:.2f}" if apertura_cerrada.monto_cierre_efectivo else "-",
            f"{currency_symbol}{apertura_cerrada.diferencia:.2f}" if apertura_cerrada.diferencia is not None else "-",
        ])
    aperturas_table = Table(aperturas_data, colWidths=[30*mm, 25*mm, 35*mm, 40*mm, 40*mm])
    aperturas_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["header_bg"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["header_text"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLORS["outline_variant"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLORS["row_alt"], COLORS["white"]]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(aperturas_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Resumen de Ventas", styles["CardTitle"]))
    resumen_data = [
        ["Concepto", "Monto"],
        ["Facturas Pagadas", f"{facturas_pagadas.count()} | {currency_symbol}{total_ventas:.2f}"],
        ["Facturas Canceladas", str(facturas_canceladas.count())],
        ["IVA (15%)", f"{currency_symbol}{total_iva:.2f}"],
        ["Servicio (10%)", f"{currency_symbol}{total_servicio:.2f}"],
        ["Descuentos", f"-{currency_symbol}{total_descuentos:.2f}"],
    ]
    resumen_table = Table(resumen_data, colWidths=[80*mm, 90*mm])
    resumen_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary_light"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["primary"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLORS["outline_variant"]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(resumen_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Metodos de Pago", styles["CardTitle"]))
    pagos_data = [["Metodo", "Cantidad", "Total"]]
    total_pago = 0
    for item in ventas_por_metodo:
        pagos_data.append([
            item["metodo"],
            str(item["count"]),
            f"{currency_symbol}{item['total']:.2f}",
        ])
        total_pago += item["total"]
    pagos_data.append(["", "TOTAL:", f"{currency_symbol}{total_pago:.2f}"])
    pagos_table = Table(pagos_data, colWidths=[60*mm, 50*mm, 60*mm])
    pagos_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["header_bg"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["header_text"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLORS["outline_variant"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [COLORS["row_alt"], COLORS["white"]]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), COLORS["primary_light"]),
        ("TEXTCOLOR", (0, -1), (-1, -1), COLORS["primary"]),
    ]))
    elements.append(pagos_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Compras del Dia", styles["CardTitle"]))
    compras_data = [["Folio", "Proveedor", "Estado", "Total"]]
    for compra in compras_recibidas[:50]:
        compras_data.append([
            compra.folio,
            compra.proveedor[:25],
            compra.get_estado_display(),
            f"{currency_symbol}{compra.total:.2f}",
        ])
    compras_data.append(["", "", "TOTAL COMPRAS:", f"{currency_symbol}{total_compras:.2f}"])
    compras_table = Table(compras_data, colWidths=[30*mm, 60*mm, 35*mm, 45*mm])
    compras_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["header_bg"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["header_text"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLORS["outline_variant"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [COLORS["row_alt"], COLORS["white"]]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), COLORS["primary_light"]),
        ("TEXTCOLOR", (0, -1), (-1, -1), COLORS["primary"]),
    ]))
    elements.append(compras_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Detalle de Facturas Pagadas", styles["CardTitle"]))
    facturas_data = [["Folio", "Comanda", "Metodo", "Usuario", "Total"]]
    for factura in facturas_pagadas.select_related("comanda", "usuario")[:100]:
        facturas_data.append([
            factura.folio,
            factura.comanda.codigo if factura.comanda else "-",
            factura.get_metodo_pago_display(),
            factura.usuario.get_full_name() if factura.usuario and factura.usuario.get_full_name() else (factura.usuario.username if factura.usuario else "-"),
            f"{currency_symbol}{factura.total_con_impuestos:.2f}",
        ])
    facturas_table = Table(facturas_data, colWidths=[28*mm, 25*mm, 30*mm, 45*mm, 42*mm])
    facturas_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["header_bg"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["header_text"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLORS["outline_variant"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [COLORS["row_alt"], COLORS["white"]]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(facturas_table)
    elements.append(Spacer(1, 12))

    bal_color = COLORS["success"] if balance_neto >= 0 else COLORS["error"]
    balance_data = [
        ["BALANCE NETO", f"{currency_symbol}{balance_neto:.2f}"],
    ]
    balance_table = Table(balance_data, colWidths=[80*mm, 90*mm])
    balance_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary_light"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("TEXTCOLOR", (0, 0), (0, 0), COLORS["primary"]),
        ("TEXTCOLOR", (1, 0), (1, 0), bal_color),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 1, COLORS["primary"]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(balance_table)

    diff_text = ""
    if apertura_cerrada and apertura_cerrada.diferencia is not None:
        diff = apertura_cerrada.diferencia
        if diff < 0:
            diff_text = f"Faltante: {currency_symbol}{abs(diff):.2f}"
        elif diff > 0:
            diff_text = f"Sobrante: {currency_symbol}{diff:.2f}"
        if diff_text:
            elements.append(Spacer(1, 6))
            diff_color = COLORS["error"] if diff < 0 else COLORS["success"]
            diff_para = Paragraph(diff_text, ParagraphStyle("Diff", fontName="Helvetica-Bold", fontSize=11, textColor=diff_color, alignment=TA_CENTER))
            elements.append(diff_para)

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, f"Cierre de Caja - {fecha_str}", restaurant_name, currency_symbol),
              onLaterPages=lambda c, d: _header_footer(c, d, f"Cierre de Caja - {fecha_str}", restaurant_name, currency_symbol))

    buffer.seek(0)
    return buffer
