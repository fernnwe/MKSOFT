"""ESC/POS receipt generator for thermal printers."""

import socket
from django.utils import timezone

ESC = b'\x1b'
GS = b'\x1d'


def _enc(text, encoding='cp858'):
    return text.encode(encoding, errors='replace')


def send_tcp(data, host, port=9100, timeout=5):
    """Send ESC/POS raw bytes to a network printer via TCP (port 9100)."""
    sock = socket.create_connection((host, port), timeout=timeout)
    try:
        sock.sendall(data)
    finally:
        sock.close()


def build_factura(factura, config, cols=32):
    items = _get_items(factura)
    buf = bytearray()
    buf += ESC + b'@'
    buf += ESC + b't' + b'\x02'

    # Header
    buf += ESC + b'a' + b'\x01'
    buf += GS + b'!' + b'\x10'
    buf += _enc(config.nombre) + b'\n'
    buf += GS + b'!' + b'\x00'
    buf += _enc(config.direccion) + b'\n'
    buf += _enc(f"Tel: {config.telefono}") + b'\n'
    buf += _enc(f"RUC: {config.rfc}") + b'\n'
    buf += ESC + b'a' + b'\x00'
    buf += _sep('-', cols) + b'\n'

    # Info
    buf += ESC + b'a' + b'\x00'
    buf += _enc(f"Folio: {factura.folio}") + b'\n'
    if factura.tipo == 'llevar':
        buf += ESC + b'a' + b'\x01'
        buf += ESC + b'E' + b'\x01'
        buf += _enc("*** PARA LLEVAR ***") + b'\n'
        buf += ESC + b'E' + b'\x00'
        buf += ESC + b'a' + b'\x00'
    else:
        if factura.comanda:
            buf += _enc(f"Comanda: {factura.comanda.codigo}") + b'\n'
            if factura.comanda.mesa:
                buf += _enc(f"Mesa: {factura.comanda.mesa.numero}") + b'\n'
    buf += _enc(f"Fecha: {timezone.localtime(factura.fecha_emision).strftime('%d/%m/%Y %H:%M')}") + b'\n'

    if factura.cliente_nombre:
        buf += _sep('-', cols) + b'\n'
        buf += _enc(f"Cliente: {factura.cliente_nombre}") + b'\n'
        if factura.cliente_rfc:
            buf += _enc(f"RUC: {factura.cliente_rfc}") + b'\n'

    buf += _sep('-', cols) + b'\n'

    # Items header
    buf += _enc(_item_header(cols)) + b'\n'
    buf += _sep('-', cols) + b'\n'

    # Items
    for item in items:
        for line in _item_lines(item, config, cols):
            buf += _enc(line) + b'\n'

    buf += _sep('-', cols) + b'\n'

    # Totals
    buf += _key_val("Subtotal:", f"{config.simbolo_moneda}{factura.subtotal:.2f}", cols)
    if factura.impuestos > 0:
        buf += _key_val("IVA (15%):", f"{config.simbolo_moneda}{factura.impuestos:.2f}", cols)
    if factura.descuento > 0:
        buf += _key_val("Descuento:", f"-{config.simbolo_moneda}{factura.descuento:.2f}", cols)
    if factura.propina > 0:
        buf += _key_val("Servicio (10%):", f"{config.simbolo_moneda}{factura.propina:.2f}", cols)

    buf += _sep('-', cols) + b'\n'
    buf += ESC + b'E' + b'\x01'
    buf += _key_val("TOTAL:", f"{config.simbolo_moneda}{factura.total:.2f}", cols)
    buf += ESC + b'E' + b'\x00'

    buf += _key_val("Pago:", factura.get_metodo_pago_display(), cols)
    if factura.monto_recibido:
        buf += _key_val("Recibido:", f"{config.simbolo_moneda}{factura.monto_recibido:.2f}", cols)
    if factura.cambio and factura.cambio > 0:
        buf += _key_val("Cambio:", f"{config.simbolo_moneda}{factura.cambio:.2f}", cols)

    buf += _sep('-', cols) + b'\n'

    # Footer
    buf += ESC + b'a' + b'\x01'
    buf += _enc("Gracias por su preferencia!") + b'\n'
    buf += _enc("*Este vaucher no sustituye") + b'\n'
    buf += _enc("un documento fiscal*") + b'\n'
    buf += _enc("Gracias por utilizar MKSOFT") + b'\n'

    buf += b'\n' * 2
    buf += GS + b'V' + b'\x00'
    return bytes(buf)


def _center(text, cols):
    text = str(text)
    if len(text) >= cols:
        return text
    left = (cols - len(text)) // 2
    return ' ' * left + text


def _sep(char, cols=32):
    return _enc(char * cols)


def _item_header(cols=32):
    return f"{'Cant':<5}{'Concepto':<{cols-12}}{'Total':>7}"


def _item_lines(item, config, cols=32):
    if isinstance(item, dict):
        qty = int(item.get('cantidad', 0))
        name = str(item.get('producto_nombre', ''))
        total = float(item.get('subtotal', 0))
    else:
        qty = int(item.cantidad)
        name = str(item.producto.nombre)
        total = float(item.subtotal)
    qty_str = f"{qty}x"
    price_str = f"{total:.2f}"
    first = qty_str + ' ' + name
    if len(first) + len(price_str) + 1 <= cols:
        spaces = cols - len(first) - len(price_str)
        return [first + ' ' * spaces + price_str]
    name_max = cols - len(qty_str) - 1
    if name_max > 0:
        first = qty_str + ' ' + name[:name_max]
    rest = name[name_max:] if name_max > 0 else name
    lines = [first]
    if rest:
        lines.append(rest[:cols])
        rest = rest[cols:]
        while rest:
            lines.append(rest[:cols])
            rest = rest[cols:]
    pad = ' ' * (cols - len(price_str))
    lines.append(pad + price_str)
    return lines


def _key_val(key, val, cols=32):
    key = str(key)
    val = str(val)
    spaces = cols - len(key) - len(val)
    if spaces < 1:
        spaces = 1
    return _enc(key + ' ' * spaces + val) + b'\n'


def _get_items(factura):
    if factura.items_json:
        import json
        try:
            return json.loads(factura.items_json)
        except (json.JSONDecodeError, TypeError):
            return []
    if factura.comanda:
        return list(factura.comanda.items.filter(cancelado=False))
    return []


def _init(cols=32):
    buf = bytearray()
    buf += ESC + b'@'
    buf += ESC + b't' + b'\x02'
    return buf


def _center_header(buf, nombre, direccion, telefono, rfc, cols=32):
    buf += ESC + b'a' + b'\x01'
    buf += GS + b'!' + b'\x10'
    buf += _enc(nombre) + b'\n'
    buf += GS + b'!' + b'\x00'
    buf += _enc(direccion) + b'\n'
    buf += _enc(f"Tel: {telefono}") + b'\n'
    buf += _enc(f"RUC: {rfc}") + b'\n'
    buf += ESC + b'a' + b'\x00'
    buf += _sep('-', cols) + b'\n'


def _footer(buf, cols=32):
    buf += ESC + b'a' + b'\x01'
    buf += _enc("Gracias por su preferencia!") + b'\n'
    buf += _enc("Gracias por utilizar MKSOFT") + b'\n'
    buf += b'\n' * 2
    buf += GS + b'V' + b'\x00'


def build_cierre(data, config, cols=32):
    """Build ESC/POS receipt for cash closure.
    data: dict from CierreTicketView context"""
    buf = _init(cols)
    _center_header(buf, config.nombre, config.direccion, config.telefono, config.rfc, cols)

    buf += _enc("CIERRE DE CAJA") + b'\n'
    buf += _enc(data["fecha_seleccionada"].strftime('%d/%m/%Y')) + b'\n'
    buf += _enc(f"Generado: {timezone.localtime(data['fecha_cierre']).strftime('%H:%M')}") + b'\n'
    buf += _enc(f"Usuario: {data['user']}") + b'\n'
    buf += _sep('-', cols) + b'\n'

    s = config.simbolo_moneda

    buf += _enc("VENTAS") + b'\n'
    buf += _key_val("Pagadas:", str(data["facturas_pagadas_count"]), cols)
    buf += _key_val("Canceladas:", str(data["facturas_canceladas_count"]), cols)
    buf += _key_val("Comandas:", str(data["comandas_cerradas_count"]), cols)
    if data.get("llevar_count", 0) > 0:
        buf += _key_val("Para llevar:", f"{data['llevar_count']} ({s}{data['llevar_total']:.2f})", cols)
    buf += _sep('-', cols) + b'\n'

    buf += _enc("FORMAS DE PAGO") + b'\n'
    for item in data.get("ventas_por_metodo", []):
        buf += _key_val(f"{item['metodo']} ({item['count']})", f"{s}{item['total']:.2f}", cols)
    buf += ESC + b'E' + b'\x01'
    buf += _key_val("TOTAL VENTAS", f"{s}{data['total_ventas']:.2f}", cols)
    buf += ESC + b'E' + b'\x00'
    buf += _sep('-', cols) + b'\n'

    if data.get("total_iva", 0) > 0 or data.get("total_servicio", 0) > 0 or data.get("total_descuentos", 0) > 0:
        buf += _enc("DESGLOSE") + b'\n'
        if data["total_iva"] > 0:
            buf += _key_val("IVA (15%):", f"{s}{data['total_iva']:.2f}", cols)
        if data["total_servicio"] > 0:
            buf += _key_val("Servicio (10%):", f"{s}{data['total_servicio']:.2f}", cols)
        if data["total_descuentos"] > 0:
            buf += _key_val("Descuentos:", f"-{s}{data['total_descuentos']:.2f}", cols)
        buf += _sep('-', cols) + b'\n'

    buf += _enc("COMPRAS") + b'\n'
    buf += _key_val("Recibidas:", str(data.get("compras_recibidas_count", 0)), cols)
    buf += _key_val("Pendientes:", str(data.get("compras_pendientes_count", 0)), cols)
    buf += _key_val("Canceladas:", str(data.get("compras_canceladas_count", 0)), cols)
    buf += _key_val("Total Compras:", f"{s}{data.get('total_compras', 0):.2f}", cols)
    if data.get("total_gastos_mov", 0) > 0:
        buf += _key_val("Gastos:", f"-{s}{data['total_gastos_mov']:.2f}", cols)
    if data.get("total_retiros_mov", 0) > 0:
        buf += _key_val("Retiros:", f"-{s}{data['total_retiros_mov']:.2f}", cols)
    buf += _sep('-', cols) + b'\n'

    buf += ESC + b'E' + b'\x01'
    buf += _key_val("BALANCE NETO", f"{s}{data.get('balance_neto', 0):.2f}", cols)
    buf += ESC + b'E' + b'\x00'
    buf += _sep('-', cols) + b'\n'

    _footer(buf, cols)
    return bytes(buf)


def build_comanda(comanda, config, cols=32):
    """Build ESC/POS receipt for kitchen order."""
    buf = _init(cols)
    buf += ESC + b'a' + b'\x01'
    buf += _enc(config.nombre) + b'\n'
    buf += GS + b'!' + b'\x10'
    buf += _enc(comanda.codigo) + b'\n'
    buf += GS + b'!' + b'\x00'
    mesa = comanda.mesa.numero if comanda.mesa else "N/A"
    buf += _enc(f"Mesa: {mesa}") + b'\n'
    if comanda.mesero:
        buf += _enc(comanda.mesero.get_full_name() or comanda.mesero.username) + b'\n'
    if comanda.prioridad == 'urgente':
        buf += _enc("*** URGENTE ***") + b'\n'
    elif comanda.prioridad == 'vip':
        buf += _enc("*** VIP ***") + b'\n'
    buf += ESC + b'a' + b'\x00'
    buf += _enc(timezone.localtime(comanda.fecha_creacion).strftime('%d/%m/%Y %H:%M')) + b'\n'
    buf += _sep('-', cols) + b'\n'

    for item in comanda.items.filter(cancelado=False):
        buf += _enc(f"{item.cantidad}x {item.producto.nombre}") + b'\n'
        if item.notas:
            buf += _enc(f"  Nota: {item.notas}") + b'\n'

    buf += _sep('-', cols) + b'\n'
    count = comanda.items.filter(cancelado=False).count()
    buf += _enc(f"{count} item{'es' if count != 1 else ''}") + b'\n'

    if comanda.notas:
        buf += _sep('-', cols) + b'\n'
        buf += _enc(f"Nota: {comanda.notas}") + b'\n'

    _footer(buf, cols)
    return bytes(buf)
