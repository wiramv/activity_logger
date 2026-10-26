"""Tes server mobile (API JSON + halaman HTML)."""

import json
import socket
import urllib.error
import urllib.request

import pytest

from activity_logger.core.mobile_server import MobileServer, lan_ip
from activity_logger.core.storage import ActivityStore


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture()
def server(tmp_path):
    store = ActivityStore(str(tmp_path / "kegiatan.json"))
    store.add("Olahraga pagi")
    instance = MobileServer(store, port=free_port())
    url = instance.start()
    yield instance, url
    instance.stop()


def request(url, method="GET", payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=5) as response:
        return response.status, response.read().decode("utf-8"), response.headers


def test_start_and_stop_idempotent(server):
    instance, url = server
    assert instance.running is True
    assert instance.start() == url  # memanggil dua kali aman
    assert url.startswith("http://")
    assert instance.actual_port > 0


def test_home_page(server):
    _, url = server
    status, body, headers = request(url + "/")
    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    assert "Activity Logger" in body
    assert "/api/state" in body


def test_state_endpoint(server):
    instance, url = server
    status, body, _ = request(url + "/api/state?period=month")
    assert status == 200
    payload = json.loads(body)
    assert payload["summary"]["total"] == 1
    assert payload["activities"][0]["text"] == "Olahraga pagi"
    assert payload["period"]["key"] == "month"
    assert payload["revision"] == instance.revision


def test_state_search_filters(server):
    _, url = server
    _, body, _ = request(url + "/api/state?period=all&q=tidak-ada")
    assert json.loads(body)["activities"] == []


def test_post_activity(server):
    instance, url = server
    status, body, _ = request(url + "/api/activities", "POST", {"text": "  Menulis laporan  "})
    assert status == 201
    payload = json.loads(body)
    assert payload["activity"]["text"] == "Menulis laporan"
    assert instance.store.count() == 2
    assert instance.revision == 1


def test_post_empty_text(server):
    _, url = server
    with pytest.raises(urllib.error.HTTPError) as error:
        request(url + "/api/activities", "POST", {"text": "   "})
    assert error.value.code == 400


def test_toggle_and_delete(server):
    instance, url = server
    activity_id = instance.store.all()[0].id

    status, body, _ = request(url + "/api/activities/{}/toggle".format(activity_id), "POST")
    assert status == 200
    assert json.loads(body)["activity"]["done"] is True

    status, body, _ = request(url + "/api/activities/{}".format(activity_id), "DELETE")
    assert status == 200
    assert instance.store.count() == 0

    with pytest.raises(urllib.error.HTTPError) as error:
        request(url + "/api/activities/nope", "DELETE")
    assert error.value.code == 404


def test_health_and_unknown(server):
    _, url = server
    status, body, _ = request(url + "/health")
    assert status == 200 and json.loads(body)["ok"] is True

    with pytest.raises(urllib.error.HTTPError) as error:
        request(url + "/tidak-ada")
    assert error.value.code == 404


def test_port_fallback_when_busy(tmp_path):
    busy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    busy.bind(("0.0.0.0", 0))
    busy.listen(1)
    port = busy.getsockname()[1]

    store = ActivityStore(str(tmp_path / "kegiatan.json"))
    instance = MobileServer(store, port=port)
    try:
        instance.start()
        assert instance.actual_port != port
        assert instance.running
    finally:
        instance.stop()
        busy.close()


def test_lan_ip_returns_string():
    ip = lan_ip()
    assert isinstance(ip, str) and ip.count(".") == 3
