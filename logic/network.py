"""Multiplayer transport.

Primary path: TCP over the local network / phone hotspot (always works on
stock Android).  When Android grants Bluetooth permissions we additionally
offer an RFCOMM link through pyjnius.  The UI labels both as
"Bluetooth / Wi-Fi mode".
"""
from __future__ import annotations

import json
import os
import socket
import threading
import time
import uuid

from config import BT_SERVICE_NAME, BT_SERVICE_UUID, DISCOVERY_MAGIC, DISCOVERY_PORT, TCP_PORT


# --------------------------------------------------------------------------
# Android helpers (pyjnius).  Imported lazily because pyjnius on Android needs
# SDL (Kivy) to be loaded first.
# --------------------------------------------------------------------------
def _jnius():
    try:
        import jnius  # noqa: F401
        from jnius import autoclass
        return autoclass
    except Exception:
        return None


def get_activity():
    autoclass = _jnius()
    if not autoclass:
        return None
    try:
        return autoclass("org.kivy.android.PythonActivity").mActivity
    except Exception:
        pass
    try:
        return autoclass("android.app.ActivityThread").currentActivity()
    except Exception:
        return None


def android_toast(message: str):
    autoclass = _jnius()
    act = get_activity()
    if not autoclass or act is None:
        return False
    try:
        Toast = autoclass("android.widget.Toast")
        PythonActivity = act
        Toast.makeText(PythonActivity, message, Toast.LENGTH_SHORT).show()
        return True
    except Exception:
        return False


def vibrate(ms: int = 40):
    autoclass = _jnius()
    act = get_activity()
    if not autoclass or act is None:
        return False
    try:
        Context = autoclass("android.content.Context")
        vibrator = act.getSystemService(Context.VIBRATOR_SERVICE)
        if vibrator is None:
            return False
        vibrator.vibrate(int(ms))
        return True
    except Exception:
        return False


def request_storage_permissions() -> bool:
    """Ask for legacy shared-storage access on Android (no-op elsewhere)."""
    autoclass = _jnius()
    act = get_activity()
    if not autoclass or act is None:
        return False
    try:
        version = int(autoclass("android.os.Build$VERSION").SDK_INT)
        if version > 32:
            return False
        perms = ["android.permission.READ_EXTERNAL_STORAGE",
                 "android.permission.WRITE_EXTERNAL_STORAGE"]
        try:
            from jnius import cast
            array = cast("[Ljava.lang.String;", perms)
            act.requestPermissions(array, 4712)
        except Exception:
            act.requestPermissions(perms, 4712)
        return True
    except Exception:
        return False


def request_portrait():
    try:
        act = get_activity()
        if act is not None:
            act.setRequestedOrientation(1)  # SCREEN_ORIENTATION_PORTRAIT
            return True
    except Exception:
        pass
    return False


def device_label() -> str:
    autoclass = _jnius()
    act = get_activity()
    if autoclass and act:
        try:
            BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
            ad = BluetoothAdapter.getDefaultAdapter()
            if ad is not None:
                name = ad.getName()
                if name:
                    return str(name)
        except Exception:
            pass
    try:
        return os.uname().nodename or "RPS Player"
    except Exception:
        return "RPS Player"


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


# --------------------------------------------------------------------------
# Bluetooth
# --------------------------------------------------------------------------
BT_PERMISSIONS = (
    "android.permission.BLUETOOTH_CONNECT",
    "android.permission.BLUETOOTH_SCAN",
    "android.permission.BLUETOOTH",
    "android.permission.BLUETOOTH_ADMIN",
)


def bt_adapter():
    autoclass = _jnius()
    if not autoclass:
        return None
    try:
        return autoclass("android.bluetooth.BluetoothAdapter").getDefaultAdapter()
    except Exception:
        return None


def bt_available() -> bool:
    try:
        ad = bt_adapter()
        return bool(ad is not None and ad.isEnabled())
    except Exception:
        return False


def request_bt_permissions() -> list:
    autoclass = _jnius()
    act = get_activity()
    if not autoclass or act is None:
        return []
    try:
        version = autoclass("android.os.Build$VERSION").SDK_INT
        wanted = ([BT_PERMISSIONS[0], BT_PERMISSIONS[1]] if int(version) >= 31
                  else [BT_PERMISSIONS[2], BT_PERMISSIONS[3]])
        String = autoclass("java.lang.String")
        arr = [String(x) for x in wanted]
        act.requestPermissions(arr, 0x5250)
        return wanted
    except Exception:
        return []


def bt_has_permissions() -> bool:
    try:
        act = get_activity()
        if act is None:
            return False
        for perm in ("android.permission.BLUETOOTH_CONNECT", "android.permission.BLUETOOTH"):
            try:
                if int(act.checkSelfPermission(perm)) == 0:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def bt_paired_devices() -> list:
    ad = bt_adapter()
    if ad is None:
        return []
    result = []
    try:
        bonded = ad.getBondedDevices()
        if bonded is None:
            return []
        for dev in bonded.toArray():
            try:
                result.append({"name": str(dev.getName() or "Unknown"), "address": str(dev.getAddress())})
            except Exception:
                continue
    except Exception:
        return result
    return result


def bt_ensure_discoverable(seconds: int = 120):
    autoclass = _jnius()
    act = get_activity()
    if not autoclass or act is None:
        return False
    try:
        BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
        Intent = autoclass("android.content.Intent")
        intent = Intent(BluetoothAdapter.ACTION_REQUEST_DISCOVERABLE)
        intent.putExtra(BluetoothAdapter.EXTRA_DISCOVERABLE_DURATION, int(seconds))
        act.startActivity(intent)
        return True
    except Exception:
        return False


class JavaRfcommSocket:
    """Make a Java BluetoothSocket behave like a tiny Python socket."""

    def __init__(self, jsock):
        self.jsock = jsock
        self._in = jsock.getInputStream()
        self._out = jsock.getOutputStream()
        self._closed = False

    def recv(self, _n=1):
        try:
            b = int(self._in.read())
        except Exception:
            return b""
        if b < 0:
            return b""
        return bytes((b,))

    def sendall(self, data):
        if self._closed:
            raise OSError("closed")
        for byte in data:
            self._out.write(int(byte))
        self._out.flush()

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.jsock.close()
        except Exception:
            pass


def _bt_uuid():
    autoclass = _jnius()
    if not autoclass:
        raise RuntimeError("pyjnius unavailable")
    return autoclass("java.util.UUID").fromString(BT_SERVICE_UUID)


def bt_host(on_link, on_error=None):
    """Open an RFCOMM server in a background thread. Returns a stopper."""
    stop = threading.Event()
    holder = {"server": None}

    def run():
        try:
            autoclass = _jnius()
            if not autoclass:
                raise RuntimeError("pyjnius unavailable")
            ad = bt_adapter()
            if ad is None:
                raise RuntimeError("no bluetooth adapter")
            if not ad.isEnabled():
                raise RuntimeError("bluetooth is off")
            server = ad.listenUsingRfcommWithServiceRecord(BT_SERVICE_NAME, _bt_uuid())
            holder["server"] = server
            bt_ensure_discoverable(120)
            sock = server.accept()
            if sock is None:
                raise RuntimeError("accept failed")
            link = Link(JavaRfcommSocket(sock), transport="bluetooth")
            on_link(link)
        except Exception as exc:  # noqa: BLE001
            if not stop.is_set() and on_error:
                on_error(exc)

    t = threading.Thread(target=run, daemon=True)
    t.start()

    def stopper():
        stop.set()
        try:
            if holder["server"] is not None:
                holder["server"].close()
        except Exception:
            pass

    return stopper


def bt_join(address, on_link, on_error=None):
    def run():
        try:
            autoclass = _jnius()
            if not autoclass:
                raise RuntimeError("pyjnius unavailable")
            ad = bt_adapter()
            if ad is None:
                raise RuntimeError("no bluetooth adapter")
            try:
                ad.cancelDiscovery()
            except Exception:
                pass
            remote = ad.getRemoteDevice(str(address))
            sock = remote.createRfcommSocketToServiceRecord(_bt_uuid())
            sock.connect()
            link = Link(JavaRfcommSocket(sock), transport="bluetooth")
            on_link(link)
        except Exception as exc:  # noqa: BLE001
            if on_error:
                on_error(exc)

    threading.Thread(target=run, daemon=True).start()


# --------------------------------------------------------------------------
# Line protocol
# --------------------------------------------------------------------------
class Link:
    """JSON-lines duplex link. Callbacks arrive on a worker thread."""

    def __init__(self, sock, transport="wifi", peer=None):
        self.sock = sock
        self.transport = transport
        self.peer = peer or {}
        self.on_message = None
        self.on_close = None
        self.alive = True
        self._buffer = b""
        self._send_lock = threading.Lock()
        self._closed = False
        threading.Thread(target=self._reader, daemon=True).start()

    def send(self, obj) -> bool:
        if not self.alive:
            return False
        try:
            data = (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
        except Exception:
            return False
        try:
            with self._send_lock:
                self.sock.sendall(data)
            return True
        except Exception:
            self.close(notify=True)
            return False

    def _reader(self):
        while self.alive:
            try:
                chunk = self.sock.recv(2048)
            except Exception:
                break
            if not chunk:
                break
            self._buffer += chunk
            while b"\n" in self._buffer:
                line, self._buffer = self._buffer.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line.decode("utf-8", "replace"))
                except Exception:
                    continue
                if isinstance(msg, dict) and self.on_message:
                    try:
                        self.on_message(msg)
                    except Exception:
                        pass
        self.close(notify=True)

    def close(self, notify: bool = False):
        if self._closed:
            return
        self._closed = True
        self.alive = False
        try:
            shutdown = getattr(self.sock, "shutdown", None)
            if shutdown:
                shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass
        if notify and self.on_close:
            try:
                self.on_close()
            except Exception:
                pass


def _prepare(sock):
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        pass
    try:
        sock.settimeout(None)
    except Exception:
        pass
    return sock


class TcpHost:
    def __init__(self, port=TCP_PORT):
        self.port = port
        self.ip = get_local_ip()
        self.on_link = None
        self.on_error = None
        self._server = None
        self._stopped = False

    def start(self, on_link, on_error=None):
        self.on_link = on_link
        self.on_error = on_error

        def run():
            try:
                srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind(("0.0.0.0", self.port))
                srv.listen(2)
                srv.settimeout(0.5)
                self._server = srv
                while not self._stopped:
                    try:
                        conn, addr = srv.accept()
                    except socket.timeout:
                        continue
                    except Exception:
                        break
                    _prepare(conn)
                    link = Link(conn, transport="wifi", peer={"ip": addr[0]})
                    self.on_link and self.on_link(link)
                    break
            except Exception as exc:  # noqa: BLE001
                if not self._stopped and self.on_error:
                    self.on_error(exc)
            finally:
                try:
                    if self._server:
                        self._server.close()
                except Exception:
                    pass

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self._stopped = True
        try:
            if self._server:
                self._server.close()
        except Exception:
            pass


def join_tcp(ip, port, on_link, on_error=None, timeout=9.0):
    def run():
        try:
            sock = socket.create_connection((str(ip).strip(), int(port)), timeout=timeout)
            _prepare(sock)
            link = Link(sock, transport="wifi", peer={"ip": str(ip).strip()})
            on_link(link)
        except Exception as exc:  # noqa: BLE001
            if on_error:
                on_error(exc)

    threading.Thread(target=run, daemon=True).start()


# --------------------------------------------------------------------------
# UDP discovery
# --------------------------------------------------------------------------
class DiscoveryResponder:
    def __init__(self, port=DISCOVERY_PORT, game_port=TCP_PORT, name="RPS Arena"):
        self.port = port
        self.game_port = game_port
        self.name = name
        self._sock = None
        self._stop = False

    def start(self):
        def run():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("", self.port))
                s.settimeout(0.6)
                self._sock = s
                while not self._stop:
                    try:
                        data, addr = s.recvfrom(512)
                    except socket.timeout:
                        continue
                    except Exception:
                        break
                    if not data.startswith(DISCOVERY_MAGIC.encode()):
                        continue
                    payload = json.dumps({
                        "magic": DISCOVERY_MAGIC,
                        "name": self.name,
                        "port": self.game_port,
                        "ip": get_local_ip(),
                    }).encode()
                    try:
                        s.sendto(payload, addr)
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                try:
                    if self._sock:
                        self._sock.close()
                except Exception:
                    pass

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self._stop = True
        try:
            if self._sock:
                self._sock.close()
        except Exception:
            pass


def discover_games(timeout=2.6, port=DISCOVERY_PORT):
    found = []
    seen = set()

    def run():
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(0.35)
            msg = (DISCOVERY_MAGIC + "?").encode()
            targets = ["255.255.255.255", "<broadcast>", "127.0.0.1"]
            for target in targets:
                try:
                    s.sendto(msg, (target, port))
                except Exception:
                    pass
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    data, addr = s.recvfrom(1024)
                except socket.timeout:
                    continue
                except Exception:
                    break
                try:
                    obj = json.loads(data.decode("utf-8", "replace"))
                except Exception:
                    continue
                if obj.get("magic") != DISCOVERY_MAGIC:
                    continue
                ip = obj.get("ip") or addr[0]
                key = (ip, obj.get("port"))
                if key in seen:
                    continue
                seen.add(key)
                found.append({
                    "name": obj.get("name", "RPS Arena"),
                    "ip": ip,
                    "port": int(obj.get("port", TCP_PORT)),
                })
        except Exception:
            pass
        finally:
            try:
                if s:
                    s.close()
            except Exception:
                pass

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout + 1.5)
    return found
