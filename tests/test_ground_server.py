import json, threading, urllib.request
from ground.receiver import GroundView
from ground.server import make_server


def test_api_view_serves_geojson_ready_data():
    v = GroundView()
    v.ingest({"type": "hello", "p": {"o": [36.9324355, 10.2695094]}})
    v.ingest({"type": "rep", "p": {"h": [1, 0, 1], "d": [[1, 2, 10.0, 20.0, 93], [2, 0, 5.0, 5.0, 88]],
                                   "i": [1, [[7, 30.0, 40.0, 9, 0]]]}})
    srv = make_server(v, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        data = json.load(urllib.request.urlopen(base + "/api/view"))
        assert {"origin", "drone", "weapon", "litter", "mine", "injured"} <= set(data)
        assert len(data["mine"]) == 1 and len(data["weapon"]) == 1 and data["injured"][0]["priority"] == 9
        assert all("lat" in p and "lon" in p for k in ("weapon", "litter", "mine", "injured") for p in data[k])
        html = urllib.request.urlopen(base + "/").read().decode()
        for i in ("map-weapon", "map-injured", "map-litter", "map-mine"):
            assert f'id="{i}"' in html
    finally:
        srv.shutdown()
