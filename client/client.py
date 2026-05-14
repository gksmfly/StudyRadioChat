import socket, threading, sys, os, base64
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol import encode, decode_line, CMD

HOST = "127.0.0.1"
PORT = 5001
current_id, current_room = "-", "-"

send_lock = threading.Lock()

pending_file = {}
recv_fp = None
recv_remaining = 0

def send_line(sock, s: str):
    with send_lock:
        sock.sendall((s + "\n").encode())

def recv_line(sock, buf: bytes):
    while b"\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            return None, buf
        buf += chunk
    line, buf = buf.split(b"\n", 1)
    return line.decode(errors="replace"), buf


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def print_commands():
    print("명령어:")
    print("/id <name>")
    print("/join <room>")
    print("/leave")
    print("/rooms")
    print("/msg <text>")
    print("/whisper <id> <text>")
    print("/hist")
    print("/summary")
    print("/pin_set <text>")
    print("/pin /pin_clear")
    print("/sched_add <text>")
    print("/sched /sched_clear")
    print("/file <to> <path>")
    print("/file_ack <sender> <accept|reject>")
    print("/quit")
    print()


def listen(sock):
    global current_id
    buf = b""

    while True:
        line, buf = recv_line(sock, buf)
        if line is None:
            break

        parsed = decode_line(line)
        if not parsed:
            print("[SERVER]", line)
            continue

        try:
            cmd = CMD(parsed["cmd"])
        except ValueError:
            print("[SERVER] UNKNOWN CMD:", parsed["cmd"])
            continue

        frm = parsed["from"]
        payload = parsed["payload"]

        if cmd == CMD.ERROR:
            print("❗ ERROR:", payload)
            continue

        if cmd == CMD.NOTICE:
            print("📢", payload)
            continue

        if cmd == CMD.ID_RES and payload == "fail":
            print("⚠️ ID 중복/실패. 다시 /id 입력하세요.")
            current_id = "-"
            continue

        if cmd == CMD.ROOMS_RES:
            print("🏷 rooms:", payload)
            continue

        if cmd == CMD.LEAVE_ACK:
            print("👋 leave:", payload)
            continue

        if cmd == CMD.PIN_ACK:
            print("📌 pin:", payload)
            continue

        if cmd == CMD.SCHED_ACK:
            print("🗓 sched:", payload)
            continue

        if cmd == CMD.HIST_RES:
            try:
                text = base64.b64decode(payload.encode("ascii")).decode("utf-8", errors="replace")
            except:
                text = payload
            print("🕘 HISTORY:\n" + text)
            continue

        if cmd == CMD.SUM_RES:
            print("🧠", payload)
            continue

        if cmd == CMD.FILE_OFFER:
            print(f"파일 요청: {frm} → {payload}")
            print(f"/file_ack {frm} accept  또는  /file_ack {frm} reject")
            continue

        print("[SERVER]", line)


def main():
    global current_id, current_room

    sock = socket.socket()
    sock.connect((HOST, PORT))

    threading.Thread(target=listen, args=(sock,), daemon=True).start()

    print_commands()  # 실행 시 딱 한 번

    while True:
        user_cmd = input("> ").strip()

        # ID 설정 (이미 있으면 차단)
        if user_cmd.startswith("/id "):
            if current_id != "-":
                print("이미 ID가 설정되어 있습니다.")
                print("ID 변경은 지원하지 않습니다. 새로 실행하세요.")
                continue

            new_id = user_cmd[4:].strip()
            if not new_id:
                print("ID가 비어 있습니다.")
                continue

            current_id = new_id
            send_line(sock, encode(CMD.ID_REQ, "-", "-", new_id))

        elif user_cmd.startswith("/join "):
            current_room = user_cmd[6:].strip()
            send_line(sock, encode(CMD.JOIN, current_id, current_room, "-"))

        elif user_cmd == "/leave":
            send_line(sock, encode(CMD.LEAVE, current_id, current_room, "-"))
            current_room = "-"

        elif user_cmd == "/rooms":
            send_line(sock, encode(CMD.ROOMS_REQ, current_id, "-", "-"))

        elif user_cmd.startswith("/msg "):
            send_line(sock, encode(CMD.MSG, current_id, current_room, user_cmd[5:]))

        elif user_cmd.startswith("/whisper "):
            _, t, m = user_cmd.split(" ", 2)
            send_line(sock, encode(CMD.WHISPER, current_id, t, m))

        elif user_cmd == "/hist":
            send_line(sock, encode(CMD.HIST_REQ, current_id, current_room, "20"))

        elif user_cmd == "/summary":
            send_line(sock, encode(CMD.SUM_REQ, current_id, current_room, "-"))

        elif user_cmd.startswith("/pin_set "):
            send_line(sock, encode(CMD.PIN_SET, current_id, current_room, user_cmd[9:]))

        elif user_cmd.startswith("/sched_add "):
            send_line(sock, encode(CMD.SCHED_ADD, current_id, current_room, user_cmd[11:]))

        elif user_cmd.startswith("/file "):
            _, to, path = user_cmd.split(" ", 2)
            pending_file[to] = path
            send_line(sock, encode(CMD.FILE_REQ, current_id, to, os.path.basename(path)))
            print("파일 요청 전송 완료")

        elif user_cmd.startswith("/file_ack "):
            _, sender, decision = user_cmd.split(" ", 2)
            send_line(sock, encode(CMD.FILE_ACK, current_id, sender, decision))

        elif user_cmd == "/quit":
            send_line(sock, encode(CMD.QUIT, current_id, "-", "-"))
            break

    sock.close()


if __name__ == "__main__":
    main()