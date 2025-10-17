import cv2
import time
import requests
from ultralytics import YOLO

# ---------------- CONFIG ----------------
ESP32_IP = "192.168.1.32"  # replace with your ESP32 IP
BASE_URL = f"http://{ESP32_IP}"

# Movement endpoints
END_F = "/F"
END_B = "/B"
END_L = "/L"
END_R = "/R"
END_S = "/S"

# Behavior tuning
SLOW_SPEED = 20           # slow approach
HOLD_SEND_INTERVAL = 0.5   # resend same command periodically
STOP_BOX_HEIGHT = 200      # stop if person bbox height >= this
CENTER_TOLERANCE = 0.2     # fraction of width to consider "centered"
FRAME_WIDTH = 640

# ---------------- Face Detection Model ----------------
model = YOLO("yolov8n.pt")  # YOLOv8 model for face detection

# ---------------- Camera ----------------
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)

last_sent_cmd = None
last_sent_time = 0

def send_cmd(path, params=None):
    url = BASE_URL + path
    try:
        if params:
            r = requests.get(url, params=params, timeout=1)
        else:
            r = requests.get(url, timeout=1)
        return True
    except requests.RequestException as e:
        print("Network error:", e)
        return False

print("Starting camera and face detection...")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # resize for consistent detection
        h0, w0 = frame.shape[:2]
        scale = FRAME_WIDTH / w0
        frame_resized = cv2.resize(frame, (FRAME_WIDTH, int(h0*scale)))

        # YOLO inference for face detection
        results = model(frame_resized)
        # results[0] contains detections
        faces = []
        for r in results[0].boxes:
            cls = int(r.cls[0])
            conf = float(r.conf[0])
            x1, y1, x2, y2 = map(int, r.xyxy[0])
            if cls == 0 and conf > 0.5:  # class 0 = face
                faces.append((x1, y1, x2, y2))

        print(f"Detected {len(faces)} faces")

        if faces:
            # pick largest (closest) face
            best = max(faces, key=lambda b: b[3]-b[1])
            x1, y1, x2, y2 = best
            w, h = x2-x1, y2-y1
            cx = x1 + w/2
            frame_cx = FRAME_WIDTH/2
            dx = (cx - frame_cx)/FRAME_WIDTH  # normalized offset

            # draw bbox
            cv2.rectangle(frame_resized, (x1,y1), (x2,y2), (0,255,0), 2)
            cv2.putText(frame_resized, f"h={h}", (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

            now = time.time()
            cmd = "F"
            params = {"spd": SLOW_SPEED}

            print(f"dx={dx:.2f}, h={h}, cmd={cmd}")

            if last_sent_cmd != cmd or (now - last_sent_time) > HOLD_SEND_INTERVAL:
                send_cmd("/" + cmd, params)
                last_sent_cmd = cmd
                last_sent_time = now
                print(f"Sent {cmd} {'params='+str(params) if params else ''}")
        else:
            # no face detected
            cmd = "S"
            now = time.time()
            print(f"No face detected, cmd={cmd}")
            if last_sent_cmd != cmd or (now - last_sent_time) > HOLD_SEND_INTERVAL:
                send_cmd("/S")
                last_sent_cmd = "S"
                last_sent_time = now
                print("Sent S (no face)")

        # show frame
        cv2.imshow("Face Follow", frame_resized)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            send_cmd("/S")
            break

except KeyboardInterrupt:
    send_cmd("/S")

finally:
    cap.release()
    cv2.destroyAllWindows()
    print("Exiting, robot stopped.")
