var AGENT_URL = 'http://127.0.0.1:8765';

function printEscpos(url) {
    var el = document.createElement('div');
    el.style.cssText = 'position:fixed;bottom:16px;left:50%;transform:translateX(-50%);padding:10px 20px;background:#333;color:#fff;border-radius:6px;font-family:sans-serif;font-size:14px;z-index:99999;box-shadow:0 2px 12px rgba(0,0,0,0.3);';
    document.body.appendChild(el);

    function setStatus(msg, ok) {
        el.textContent = msg;
        el.style.background = ok ? '#2e7d32' : (msg.includes('Error') ? '#c62828' : '#333');
        if (msg.includes('correctamente')) {
            setTimeout(function() { el.remove(); }, 2500);
        }
    }

    fetch(AGENT_URL + '/status')
        .then(function(r) { return r.json(); })
        .then(function(info) {
            setStatus('Enviando a ' + (info.printer || 'impresora') + '...');
            return fetch(url).then(function(r) {
                if (!r.ok) throw new Error('Error ESC/POS');
                return r.arrayBuffer();
            }).then(function(data) {
                return fetch(AGENT_URL + '/print', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/octet-stream' },
                    body: data
                });
            }).then(function(r) { return r.json(); }).then(function(result) {
                if (result.success) setStatus('Impreso correctamente!', 1);
                else setStatus('Error: ' + (result.error || 'desconocido'), 0);
            });
        })
        .catch(function() {
            setStatus('Agente no disponible - descargando archivo', 0);
            window.open(url, '_blank');
            setTimeout(function() { el.remove(); }, 4000);
        });
}
