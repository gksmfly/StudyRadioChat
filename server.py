import socket, threading, base64
from protocol import CMD, State, ERROR_CODE, encode, decode_line
from utils import save_log, load_recent, summarize_chat

HOST = "0.0.0.0"
PORT = 5001

clients = {}        # sock -> {id, room, state}
clients_by_id = {}  # id -> sock
rooms = {}          # room -> {"users": set(), "pin": str, "schedule": list[str]}
send_locks = {}     # sock -> threading.Lock

ALLOWED_CMDS = {
    State.CONNECTED: {CMD.ID_REQ, CMD.QUIT},
    State.IDENTIFIED: {CMD.JOIN, CMD.ROOMS_REQ, CMD.QUIT},
    State.JOINED: {
        CMD.MSG, CMD.WHISPER, CMD.HIST_REQ, CMD.SUM_REQ,
        CMD.FILE_REQ, CMD.FILE_ACK,
        CMD.PIN_SET, CMD.PIN_GET, CMD.PIN_CLEAR,
        CMD.SCHED_ADD, CMD.SCHED_LIST, CMD.SCHED_CLEAR,
        CMD.ROOMS_REQ, CMD.LEAVE, CMD.QUIT
    }
}

ERR_NO_SUCH_USER = "ERR_404_NO_SUCH_USER"
ERR_UNKNOWN_CMD = "ERR_400_UNKNOWN_CMD"
ERR_SENDER_MISMATCH = "ERR_400_SENDER_MISMATCH"

# ---------------- utils ----------------

def _get_lock(sock):
    lk = send_locks.get(sock)
    if lk is None:
        lk = threading.Lock()
        send_locks[sock] = lk
    return lk

def send_line(sock, s: str):
    try:
        with _get_lock(sock):
            sock.sendall(s.encode())
    except:
        pass

def send_error(sock, code):
    if hasattr(code, "value"):
        code = code.value
    send_line(sock, encode(CMD.ERROR, "server", "-", code))

def broadcast(room, msg, exclude=None):
    for uid in rooms.get(room, {}).get("users", set()):
        if uid == exclude:
            continue
        s = clients_by_id.get(uid)
        if s:
            send_line(s, msg)

def recv_line(sock, buf: bytes):
    while b"\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            return None, buf
        buf += chunk
    line, buf = buf.split(b"\n", 1)
    return line.decode(errors="replace"), buf

def cleanup_client(sock):
    if sock not in clients:
        return
    uid = clients[sock]["id"]
    room = clients[sock]["room"]

    if uid and clients_by_id.get(uid) is sock:
        clients_by_id.pop(uid, None)

    if room and room in rooms:
        rooms[room]["users"].discard(uid)
        if not rooms[room]["users"]:
            del rooms[room]

    clients.pop(sock, None)
    send_locks.pop(sock, None)

# ---------------- main handler ----------------

def handle_client(sock, addr):
    clients[sock] = {"id": None, "room": None, "state": State.CONNECTED}
    send_locks[sock] = threading.Lock()
    buf = b""
    print("Connected:", addr)

    try:
        while True:
            line, buf = recv_line(sock, buf)
            if line is None:
                break

            parsed = decode_line(line)
            if not parsed:
                continue

            try:
                cmd = CMD(parsed["cmd"])
            except ValueError:
                send_error(sock, ERR_UNKNOWN_CMD)
                continue

            client = clients[sock]
            raw_from = parsed["from"]
            target = parsed["target"]
            payload = parsed["payload"]

            if cmd not in ALLOWED_CMDS.get(client["state"], set()):
                send_error(sock, ERROR_CODE.INVALID_STATE)
                continue

            # ---------- ID ----------
            if cmd == CMD.ID_REQ:
                new_id = payload
                if not new_id or new_id == "-" or new_id in clients_by_id:
                    send_line(sock, encode(CMD.ID_RES, "server", new_id, "fail"))
                    continue
                client["id"] = new_id
                client["state"] = State.IDENTIFIED
                clients_by_id[new_id] = sock
                send_line(sock, encode(CMD.ID_RES, "server", new_id, "ok"))
                continue

            uid = client["id"]
            if raw_from not in ("-", uid):
                send_error(sock, ERR_SENDER_MISMATCH)
                continue

            # ---------- JOIN ----------
            if cmd == CMD.JOIN:
                if not target or target == "-":
                    send_line(sock, encode(CMD.JOIN_ACK, "server", uid, "fail"))
                    send_error(sock, ERROR_CODE.INVALID_ROOM)
                    continue

                rooms.setdefault(target, {"users": set(), "pin": "", "schedule": []})
                rooms[target]["users"].add(uid)
                client["room"] = target
                client["state"] = State.JOINED

                broadcast(target, encode(CMD.NOTICE, "server", target, f"{uid} joined"), exclude=uid)
                send_line(sock, encode(CMD.JOIN_ACK, "server", uid, "success"))

            # ---------- LEAVE ----------
            elif cmd == CMD.LEAVE:
                room = client["room"]
                if room and room in rooms:
                    rooms[room]["users"].discard(uid)
                    broadcast(room, encode(CMD.NOTICE, "server", room, f"{uid} left"), exclude=uid)
                    if not rooms[room]["users"]:
                        del rooms[room]

                client["room"] = None
                client["state"] = State.IDENTIFIED
                send_line(sock, encode(CMD.LEAVE_ACK, "server", uid, "ok"))

            # ---------- QUIT ----------
            elif cmd == CMD.QUIT:
                room = client["room"]
                if room and room in rooms:
                    rooms[room]["users"].discard(uid)
                    broadcast(room, encode(CMD.NOTICE, "server", room, f"{uid} disconnected"), exclude=uid)
                    if not rooms[room]["users"]:
                        del rooms[room]
                break

            # ---------- ROOMS ----------
            elif cmd == CMD.ROOMS_REQ:
                send_line(sock, encode(CMD.ROOMS_RES, "server", uid, ",".join(rooms.keys())))

            # ---------- MSG ----------
            elif cmd == CMD.MSG:
                room = client["room"]
                save_log(room, f"[{uid}] {payload}")
                broadcast(room, encode(CMD.MSG, uid, room, payload))
                send_line(sock, encode(CMD.MSG_ACK, "server", uid, "delivered"))

            # ---------- WHISPER (비공개) ----------
            elif cmd == CMD.WHISPER:
                t = clients_by_id.get(target)
                if not t:
                    send_error(sock, ERR_NO_SUCH_USER)
                    continue
                send_line(t, encode(CMD.WHISPER, uid, target, payload))
                send_line(sock, encode(CMD.WHISPER_ACK, "server", uid, "delivered"))

            # ---------- HIST ----------
            elif cmd == CMD.HIST_REQ:
                logs = load_recent(client["room"], 20)
                text = "".join(logs)
                b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
                send_line(sock, encode(CMD.HIST_RES, "server", uid, b64))

            # ---------- SUMMARY ----------
            elif cmd == CMD.SUM_REQ:
                logs = load_recent(client["room"], 20)
                send_line(sock, encode(CMD.SUM_ACK, "server", uid, "processing"))
                send_line(sock, encode(CMD.SUM_RES, "server", uid, summarize_chat(logs)))

            # ---------- PIN ----------
            elif cmd == CMD.PIN_SET:
                room = client["room"]
                rooms[room]["pin"] = payload
                send_line(sock, encode(CMD.PIN_ACK, "server", uid, "success"))
                broadcast(room, encode(CMD.NOTICE, "server", room, f"PIN updated by {uid}"), exclude=uid)

            elif cmd == CMD.PIN_GET:
                room = client["room"]
                pin = rooms.get(room, {}).get("pin", "")
                send_line(sock, encode(CMD.PIN_RES, "server", uid, pin if pin else "-"))

            elif cmd == CMD.PIN_CLEAR:
                room = client["room"]
                rooms[room]["pin"] = ""
                send_line(sock, encode(CMD.PIN_ACK, "server", uid, "success"))
                broadcast(room, encode(CMD.NOTICE, "server", room, f"PIN cleared by {uid}"), exclude=uid)

            # ---------- SCHEDULE ----------
            elif cmd == CMD.SCHED_ADD:
                room = client["room"]
                rooms[room]["schedule"].append(payload)
                send_line(sock, encode(CMD.SCHED_ACK, "server", uid, "success"))
                broadcast(room, encode(CMD.NOTICE, "server", room, f"Schedule updated by {uid}"), exclude=uid)

            elif cmd == CMD.SCHED_LIST:
                room = client["room"]
                items = rooms.get(room, {}).get("schedule", [])
                send_line(sock, encode(CMD.SCHED_RES, "server", uid, ";;".join(items) if items else "-"))

            elif cmd == CMD.SCHED_CLEAR:
                room = client["room"]
                rooms[room]["schedule"] = []
                send_line(sock, encode(CMD.SCHED_ACK, "server", uid, "success"))
                broadcast(room, encode(CMD.NOTICE, "server", room, f"Schedule cleared by {uid}"), exclude=uid)

    finally:
        cleanup_client(sock)
        try:
            sock.close()
        except:
            pass
        print("Disconnected:", addr)

# ---------------- server start ----------------

def main():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print("Server started")
    while True:
        sock, addr = s.accept()
        threading.Thread(target=handle_client, args=(sock, addr), daemon=True).start()

if __name__ == "__main__":
    main()