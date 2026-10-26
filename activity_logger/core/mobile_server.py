"""Server kecil untuk membuka catatan dari HP di jaringan lokal (Wi-Fi sama).

Hanya memakai pustaka standar (``http.server``) sehingga tidak menambah
dependensi. Endpoint:

* ``GET  /``                       — halaman web mobile-first
* ``GET  /api/state?period=month`` — ringkasan + daftar kegiatan
* ``POST /api/activities``         — ``{"text": "..."}`` tambah kegiatan
* ``POST /api/activities/<id>/toggle``
* ``DELETE /api/activities/<id>``
* ``GET  /health``

Server berjalan di thread daemon; UI tetap responsif dan melakukan *polling*
``revision`` untuk menyegarkan tampilan saat ada input dari HP.
"""

from __future__ import annotations

import json
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from . import stats, timeutil
from .models import Activity

MAX_BODY_BYTES = 64 * 1024


def lan_ip() -> str:
    """Perkirakan alamat IP LAN mesin ini (tanpa benar-benar mengirim data)."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        probe.close()


class MobileServer:
    """Pembungkus ``ThreadingHTTPServer`` yang mudah dinyalakan/dimatikan."""

    def __init__(self, store, port: int = 8765) -> None:
        self.store = store
        self.port = int(port)
        self.revision = 0
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    # -- status --------------------------------------------------------- #
    @property
    def running(self) -> bool:
        return self._httpd is not None

    @property
    def actual_port(self) -> int:
        if self._httpd is not None:
            return int(self._httpd.server_address[1])
        return self.port

    def url(self) -> str:
        return "http://{}:{}".format(lan_ip(), self.actual_port)

    def local_url(self) -> str:
        return "http://127.0.0.1:{}".format(self.actual_port)

    def bump(self) -> None:
        self.revision += 1

    # -- hidup/mati ----------------------------------------------------- #
    def start(self, port: Optional[int] = None) -> str:
        with self._lock:
            if self._httpd is not None:
                return self.url()
            wanted = int(port or self.port)
            handler = _make_handler(self)
            last_error: Optional[Exception] = None
            for candidate in _port_candidates(wanted):
                try:
                    httpd = ThreadingHTTPServer(("0.0.0.0", candidate), handler)
                except OSError as error:  # port dipakai aplikasi lain
                    last_error = error
                    continue
                httpd.daemon_threads = True
                self._httpd = httpd
                self.port = candidate
                thread = threading.Thread(
                    target=httpd.serve_forever,
                    kwargs={"poll_interval": 0.2},
                    name="activity-logger-mobile",
                    daemon=True,
                )
                self._thread = thread
                thread.start()
                return self.url()
            raise OSError("Tidak bisa membuka port: {}".format(last_error))

    def stop(self) -> None:
        with self._lock:
            httpd, thread = self._httpd, self._thread
            self._httpd = None
            self._thread = None
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

    # -- dipakai handler ----------------------------------------------- #
    def state_payload(
        self,
        period_key: str = "month",
        query: str = "",
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        reference = timeutil.today()
        period = stats.resolve_period(
            period_key,
            reference=reference,
            start=timeutil.parse_date(start) if start else None,
            end=timeutil.parse_date(end) if end else None,
        )
        items = stats.filter_activities(self.store.all(), period=period, query=query)
        summary = stats.summarize(items, period=period, reference=reference)
        today_items = stats.filter_activities(
            self.store.all(), period=stats.resolve_period("today", reference=reference)
        )
        return {
            "now": timeutil.fmt_ts(timeutil.now()),
            "period": {
                "key": period.key,
                "label": period.label,
                "start": timeutil.fmt_date_numeric(period.start_date) if period.start_date else None,
                "end": timeutil.fmt_date_numeric(period.end_date) if period.end_date else None,
            },
            "summary": {
                "total": summary.total,
                "today": summary.today,
                "this_month": summary.this_month,
                "active_days": summary.active_days,
                "avg_per_day": round(summary.avg_per_day, 2),
                "current_streak": summary.current_streak,
                "range_days": summary.range_days,
            },
            "today_count": len(today_items),
            "activities": [_activity_payload(item) for item in items[:limit]],
            "total_all": self.store.count(),
            "revision": self.revision,
        }

    def add_activity(self, text: str) -> Dict[str, Any]:
        activity = self.store.add(text)
        self.bump()
        return _activity_payload(activity)

    def toggle_activity(self, activity_id: str) -> Optional[Dict[str, Any]]:
        try:
            activity = self.store.toggle_done(activity_id)
        except Exception:
            return None
        self.bump()
        return _activity_payload(activity)

    def delete_activity(self, activity_id: str) -> bool:
        removed = self.store.delete(activity_id)
        if removed:
            self.bump()
        return removed


def _activity_payload(item: Activity) -> Dict[str, Any]:
    return {
        "id": item.id,
        "text": item.text,
        "date": timeutil.fmt_date_numeric(item.date),
        "date_label": timeutil.fmt_date_indonesian(item.date),
        "day": item.day_name,
        "time": item.clock(seconds=True),
        "done": item.done,
        "ts": timeutil.fmt_ts(item.ts),
    }


def _port_candidates(port: int):
    yield port
    for offset in range(1, 12):
        yield port + offset


def _make_handler(server: MobileServer):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ActivityLoggerMobile/1.0"

        # -- util ---------------------------------------------------- #
        def log_message(self, fmt: str, *args: Any) -> None:  # senyap
            return

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, payload: Dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(status, body, "application/json; charset=utf-8")

        def _query(self) -> Dict[str, List[str]]:
            return parse_qs(urlparse(self.path).query)

        def _read_json(self) -> Dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return {}
            if length <= 0 or length > MAX_BODY_BYTES:
                return {}
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8", errors="replace"))
            except ValueError:
                return {}
            return payload if isinstance(payload, dict) else {}

        # -- routes -------------------------------------------------- #
        def do_GET(self) -> None:  # noqa: N802 (API bawaan http.server)
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                body = MOBILE_PAGE.encode("utf-8")
                self._send(HTTPStatus.OK, body, "text/html; charset=utf-8")
                return
            if path == "/api/state":
                params = self._query()
                payload = server.state_payload(
                    period_key=_param(params, "period", "month"),
                    query=_param(params, "q", ""),
                    start=_param(params, "start", None),
                    end=_param(params, "end", None),
                    limit=_int_param(params, "limit", 100),
                )
                self._json(payload)
                return
            if path == "/health":
                self._json({"ok": True, "revision": server.revision})
                return
            if path == "/favicon.ico":
                self._send(HTTPStatus.NO_CONTENT, b"", "image/x-icon")
                return
            self._json({"error": "not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/activities":
                payload = self._read_json()
                text = str(payload.get("text") or "").strip()
                if not text:
                    self._json({"error": "Kegiatan tidak boleh kosong"}, status=400)
                    return
                try:
                    activity = server.add_activity(text)
                except (OSError, ValueError) as error:
                    self._json({"error": str(error)}, status=500)
                    return
                self._json({"ok": True, "activity": activity}, status=201)
                return
            parts = [part for part in path.split("/") if part]
            if len(parts) == 4 and parts[:2] == ["api", "activities"] and parts[3] == "toggle":
                activity = server.toggle_activity(parts[2])
                if activity is None:
                    self._json({"error": "Tidak ditemukan"}, status=404)
                    return
                self._json({"ok": True, "activity": activity})
                return
            self._json({"error": "not found"}, status=404)

        def do_DELETE(self) -> None:  # noqa: N802
            parts = [part for part in urlparse(self.path).path.split("/") if part]
            if len(parts) == 3 and parts[:2] == ["api", "activities"]:
                if server.delete_activity(parts[2]):
                    self._json({"ok": True})
                else:
                    self._json({"error": "Tidak ditemukan"}, status=404)
                return
            self._json({"error": "not found"}, status=404)

    return Handler


def _param(params: Dict[str, List[str]], key: str, default: Optional[str]) -> Optional[str]:
    values = params.get(key)
    if not values:
        return default
    return values[0]


def _int_param(params: Dict[str, List[str]], key: str, default: int) -> int:
    try:
        return int(_param(params, key, str(default)) or default)
    except (TypeError, ValueError):
        return default


MOBILE_PAGE = """<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0f9d6b">
<title>Activity Logger</title>
<style>
:root{--bg:#f1f5f9;--surface:#fff;--text:#0f172a;--muted:#64748b;--border:#e2e8f0;
--primary:#0f9d6b;--primary-dark:#0b8457;--soft:#e7f7f0;--danger:#e11d48;--radius:14px}
@media (prefers-color-scheme: dark){:root{--bg:#0b1220;--surface:#111a2b;--text:#e2e8f0;
--muted:#94a3b8;--border:#1e293b;--soft:#0f2a22;--primary:#10b981;--primary-dark:#0d9668}}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
padding:env(safe-area-inset-top) 0 calc(env(safe-area-inset-bottom) + 16px)}
header{position:sticky;top:0;z-index:5;background:var(--surface);border-bottom:1px solid var(--border);
padding:14px 16px;display:flex;align-items:center;gap:10px}
.brand{width:34px;height:34px;border-radius:10px;background:var(--primary);display:grid;place-items:center;
color:#fff;font-weight:700;font-size:15px}
h1{font-size:16px;margin:0;font-weight:650}
.sub{font-size:12px;color:var(--muted)}
main{padding:16px;display:grid;gap:14px;max-width:640px;margin:0 auto}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px}
form{display:flex;gap:8px}
input[type=text]{flex:1;min-width:0;padding:12px 14px;border-radius:10px;border:1px solid var(--border);
background:var(--bg);color:var(--text);font-size:16px}
input[type=text]:focus{outline:2px solid var(--primary);outline-offset:1px}
button{border:0;border-radius:10px;padding:12px 16px;font-size:15px;font-weight:600;background:var(--primary);
color:#fff;font-family:inherit}
button:active{background:var(--primary-dark)}
button.ghost{background:transparent;color:var(--muted);border:1px solid var(--border);font-weight:500}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:12px}
.stat b{display:block;font-size:22px;line-height:1.2}
.stat span{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.chips{display:flex;gap:8px;overflow-x:auto;padding-bottom:2px;scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chip{white-space:nowrap;padding:8px 14px;border-radius:999px;border:1px solid var(--border);
background:var(--surface);color:var(--muted);font-size:13px;font-weight:600}
.chip.active{background:var(--soft);border-color:var(--primary);color:var(--primary-dark)}
ul{list-style:none;margin:0;padding:0;display:grid;gap:8px}
li{display:flex;gap:10px;align-items:flex-start;padding:11px 12px;border:1px solid var(--border);
border-radius:12px;background:var(--surface)}
li.done .txt{text-decoration:line-through;color:var(--muted)}
.check{flex:0 0 auto;width:22px;height:22px;border-radius:7px;border:1.5px solid var(--border);
display:grid;place-items:center;font-size:13px;color:#fff;margin-top:1px}
.check.on{background:var(--primary);border-color:var(--primary)}
.txt{flex:1;min-width:0;word-break:break-word}
.when{font-size:11px;color:var(--muted);margin-top:2px}
.del{background:transparent;color:var(--danger);font-size:13px;padding:4px 6px}
.empty{text-align:center;color:var(--muted);padding:26px 10px;font-size:14px}
.toast{position:fixed;left:50%;transform:translateX(-50%);bottom:24px;background:#0f172a;color:#fff;
padding:10px 16px;border-radius:999px;font-size:13px;opacity:0;transition:.25s;pointer-events:none}
.toast.show{opacity:1}
</style>
</head>
<body>
<header>
  <div class="brand">AL</div>
  <div><h1>Activity Logger</h1><div class="sub" id="subtitle">Memuat data…</div></div>
</header>
<main>
  <section class="card">
    <form id="form">
      <input id="input" type="text" placeholder="Ketik kegiatan…" autocomplete="off" enterkeyhint="send">
      <button type="submit">Simpan</button>
    </form>
  </section>
  <section class="stats">
    <div class="stat"><b id="s-today">–</b><span>Hari ini</span></div>
    <div class="stat"><b id="s-total">–</b><span id="s-total-label">Periode</span></div>
    <div class="stat"><b id="s-streak">–</b><span>Streak</span></div>
  </section>
  <div class="chips" id="chips">
    <button class="chip active" data-period="today">Hari ini</button>
    <button class="chip" data-period="week">Minggu ini</button>
    <button class="chip" data-period="month">Bulan ini</button>
    <button class="chip" data-period="last30">30 hari</button>
    <button class="chip" data-period="all">Semua</button>
  </div>
  <section class="card"><ul id="list"></ul></section>
</main>
<div class="toast" id="toast"></div>
<script>
const state = {period: 'today', q: ''};
const el = (id) => document.getElementById(id);
function toast(msg){const t=el('toast');t.textContent=msg;t.classList.add('show');
  clearTimeout(t._h);t._h=setTimeout(()=>t.classList.remove('show'),1800);}
function esc(text){return text.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
async function load(){
  const params = new URLSearchParams({period: state.period, q: state.q});
  try{
    const res = await fetch('/api/state?' + params);
    const data = await res.json();
    el('s-today').textContent = data.today_count;
    el('s-total').textContent = data.summary.total;
    el('s-total-label').textContent = data.period.label;
    el('s-streak').textContent = data.summary.current_streak + ' hari';
    el('subtitle').textContent = data.summary.this_month + ' kegiatan bulan ini · total ' + data.total_all;
    const list = el('list');
    if(!data.activities.length){list.innerHTML = '<div class="empty">Belum ada kegiatan pada rentang ini.</div>';return;}
    list.innerHTML = data.activities.map(a => `
      <li class="${a.done ? 'done' : ''}" data-id="${a.id}">
        <span class="check ${a.done ? 'on' : ''}" data-toggle="${a.id}">${a.done ? '✓' : ''}</span>
        <div class="txt">${esc(a.text)}<div class="when">${a.day}, ${a.date} · ${a.time.slice(0,5)}</div></div>
        <button class="del" data-del="${a.id}">✕</button>
      </li>`).join('');
  }catch(err){
    el('subtitle').textContent = 'Koneksi terputus — pastikan HP & komputer di Wi-Fi yang sama.';
  }
}
el('form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const text = el('input').value.trim();
  if(!text){return;}
  el('input').value = '';
  const res = await fetch('/api/activities', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({text})});
  if(res.ok){ state.period = 'today'; syncChips(); toast('Kegiatan tersimpan ✓'); load(); }
  else { toast('Gagal menyimpan'); }
});
el('list').addEventListener('click', async (ev) => {
  const toggle = ev.target.closest('[data-toggle]');
  const del = ev.target.closest('[data-del]');
  if(toggle){ await fetch('/api/activities/' + toggle.dataset.toggle + '/toggle', {method:'POST'}); load(); }
  if(del){ await fetch('/api/activities/' + del.dataset.del, {method:'DELETE'}); load(); }
});
function syncChips(){
  document.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c.dataset.period === state.period));
}
el('chips').addEventListener('click', (ev) => {
  const chip = ev.target.closest('.chip');
  if(!chip){return;}
  state.period = chip.dataset.period; syncChips(); load();
});
load();
setInterval(load, 20000);
</script>
</body>
</html>
"""
