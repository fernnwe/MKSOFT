"""ESC/POS receipt generator for thermal printers."""

ESC = b'\x1b'
GS = b'\x1d'


def _enc(text, encoding='cp858'):
    return text.encode(encoding, errors='replace')


def build_factura(factura, config, cols=32):
    items = _get_items(factura)
    buf = bytearray()
    buf += ESC + b'@'
    buf += ESC + b't' + b'\x02'

    # Header
    buf += ESC + b'a' + b'\x01'
    buf += GS + b'!' + b'\x10'
    buf += _enc(_center(config.nombre, cols)) + b'\n'
    buf += GS + b'!' + b'\x00'
    buf += _enc(_center(config.direccion, cols)) + b'\n'
    buf += _enc(_center(f"Tel: {config.telefono}", cols)) + b'\n'
    buf += _enc(_center(f"RUC: {config.rfc}", cols)) + b'\n'
    buf += _sep('-', cols) + b'\n'

    # Info
    buf += ESC + b'a' + b'\x00'
    buf += _enc(f"Folio: {factura.folio}") + b'\n'
    if factura.tipo == 'llevar':
        buf += ESC + b'a' + b'\x01'
        buf += ESC + b'E' + b'\x01'
        buf += _enc(_center("*** PARA LLEVAR ***", cols)) + b'\n'
        buf += ESC + b'E' + b'\x00'
        buf += ESC + b'a' + b'\x00'
    else:
        if factura.comanda:
            buf += _enc(f"Comanda: {factura.comanda.codigo}") + b'\n'
            if factura.comanda.mesa:
                buf += _enc(f"Mesa: {factura.comanda.mesa.numero}") + b'\n'
    buf += _enc(f"Fecha: {factura.fecha_emision.strftime('%d/%m/%Y %H:%M')}") + b'\n'

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
    buf += _enc(_center("Gracias por su preferencia!", cols)) + b'\n'
    buf += _enc(_center("*Este vaucher no sustituye", cols)) + b'\n'
    buf += _enc(_center("un documento fiscal*", cols)) + b'\n'
    buf += _enc(_center("Gracias por utilizar MKSOFT", cols)) + b'\n'

    buf += b'\n' * 4
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
