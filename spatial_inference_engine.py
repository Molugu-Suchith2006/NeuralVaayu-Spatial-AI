import cv2
import mediapipe as mp
import math
import pyautogui
import time
import multiprocessing
import threading
import queue
import os
import socket
import struct
import subprocess

# ==========================================
# NETWORK CONFIGURATION (CHANGE THIS!)
# ==========================================
TARGET_IP = "10.236.107.35"
NETWORK_PORT = 5005

# ==========================================
# OS SYSTEM HELPERS
# ==========================================
def copy_to_clipboard(filepath):
    """Silently injects an image into the Windows Clipboard using PowerShell"""
    try:
        abs_path = os.path.abspath(filepath)
        cmd = f'powershell -command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile(\'{abs_path}\'))"'
        subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"Clipboard injection failed: {e}")

def trigger_windows_notification():
    """Pops a native OS notification from the system tray when a file arrives."""
    ps_script = """
    Add-Type -AssemblyName System.Windows.Forms
    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.SystemIcons]::Information
    $notify.BalloonTipTitle = 'Vaayu Spatial Engine'
    $notify.BalloonTipText = 'New payload received! Ready to Drop.'
    $notify.Visible = $True
    $notify.ShowBalloonTip(3000)
    Start-Sleep -Seconds 3
    $notify.Dispose()
    """
    try:
        subprocess.Popen(["powershell", "-command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass

# ==========================================
# BRAIN 3: THE NETWORK BRIDGE
# ==========================================
def network_listener_worker(inbound_queue):
    """Runs continuously in the background, listening for incoming spatial data."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', NETWORK_PORT))
    server.listen(5)
    
    SAVE_DIR = "received"
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
        
    print(f"[*] Vaayu Network Bridge Listening on Port {NETWORK_PORT}...")
    
    while True:
        try:
            conn, addr = server.accept()
            
            raw_header = conn.recv(12)
            if not raw_header or len(raw_header) < 12:
                conn.close()
                continue
            msg_len, orig_w, orig_h = struct.unpack('>I I I', raw_header)
            
            data = bytearray()
            while len(data) < msg_len:
                packet = conn.recv(4096)
                if not packet:
                    break
                data.extend(packet)
                
            from PIL import Image
            import io
            
            buf = io.BytesIO(data)
            compressed_img = Image.open(buf)
            restored_img = compressed_img.resize((orig_w, orig_h), Image.Resampling.LANCZOS)
            
            inverted_timestamp = int(10000000000 - time.time())
            filepath = os.path.join(SAVE_DIR, f"vaayudrop_{inverted_timestamp}.jpg")
            
            restored_img.save(filepath, format='JPEG', quality=95)
                
            inbound_queue.put(filepath)
            trigger_windows_notification()
            
            conn.close()
        except Exception:
            pass

def send_payload_async(filepath):
    """Compresses and shoots the image across the Wi-Fi with Auto-Retry logic."""
    def task():
        try:
            from PIL import Image
            import io
            
            img = Image.open(filepath)
            orig_w, orig_h = img.size
            
            compressed_img = img.resize((orig_w // 2, orig_h // 2), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            compressed_img.save(buf, format='JPEG', quality=55)
            data = buf.getvalue()
            
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client.settimeout(4.0) 
                    client.connect((TARGET_IP, NETWORK_PORT))
                    
                    client.sendall(struct.pack('>I I I', len(data), orig_w, orig_h))
                    client.sendall(data)
                    client.close()
                    print(f"[+] Compressed Payload ({len(data)//1024} KB) successfully delivered to {TARGET_IP}")
                    return 
                    
                except socket.timeout:
                    print(f"[*] Network Timeout on attempt {attempt + 1}... retrying.")
                except Exception as e:
                    print(f"[-] Connection failed: {e}")
                    break
                    
            print(f"[-] FATAL: Could not deliver payload to {TARGET_IP}")
        except Exception as e:
            print(f"[-] Payload preparation failed: {e}")
            
    threading.Thread(target=task, daemon=True).start()

# ==========================================
# BRAIN 2: ASYNCHRONOUS UI ENGINE
# ==========================================
def animation_worker(cmd_queue):
    import tkinter as tk
    from PIL import Image, ImageTk

    root = tk.Tk()
    root.withdraw()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    TARGET_SIZE = 150  
    
    wake_win_ref = [None]

    def make_transparent_sticker(img_path, size):
        try:
            img = Image.open(img_path).convert("RGBA")
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            datas = img.getdata()
            new_data = []
            bg_color = datas[0]
            threshold = 45
            for item in datas:
                if abs(item[0]-bg_color[0]) < threshold and abs(item[1]-bg_color[1]) < threshold and abs(item[2]-bg_color[2]) < threshold:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            img.putdata(new_data)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    tk_mascot = make_transparent_sticker("WhatsApp Image 2026-07-17 at 23.22.22.jpeg", TARGET_SIZE)

    def animate(window, start, end, steps, delay, ease_type, on_complete=None):
        def step(current=0):
            if not window.winfo_exists(): return
            if current <= steps:
                progress = current / steps
                e = 1 - math.pow(1 - progress, 3) if ease_type == 'out' else math.pow(progress, 2)
                curr_x = int(start[0] + (end[0] - start[0]) * e)
                curr_y = int(start[1] + (end[1] - start[1]) * e)
                window.geometry(f"+{curr_x}+{curr_y}")
                window.after(delay, step, current + 1)
            else:
                if on_complete: on_complete()
        step()

    def check_queue():
        try:
            cmd_data = cmd_queue.get_nowait()
            if cmd_data == "QUIT":
                root.destroy()
                return
                
            action, filepath = cmd_data
            center_x, center_y = (sw // 2) - (TARGET_SIZE // 2), (sh // 2) - (TARGET_SIZE // 2)
            left_x, left_y = 20, (sh // 2) - (TARGET_SIZE // 2)
            bottom_y = sh - TARGET_SIZE - 60

            # ---------------------------------------------------------
            # LIDAR SWEEP WAKE & SLEEP (TRIGGERS FOR BOTH MODES)
            # ---------------------------------------------------------
            if action == 'WAKE':
                if wake_win_ref[0] and wake_win_ref[0].winfo_exists():
                    wake_win_ref[0].destroy()
                
                wake_win = tk.Toplevel(root)
                wake_win.overrideredirect(True)
                wake_win.geometry(f"{sw}x{sh}+0+0")
                wake_win.attributes('-alpha', 0.25)
                wake_win.attributes('-topmost', True)
                wake_win.configure(bg='#021a1a')
                
                canvas = tk.Canvas(wake_win, width=sw, height=sh, bg='#021a1a', highlightthickness=0)
                canvas.pack()
                
                laser = canvas.create_rectangle(0, 0, sw, 8, fill='#00ffff', outline='#00ffff')
                
                def sweep(y):
                    if wake_win.winfo_exists():
                        if y < sh:
                            canvas.coords(laser, 0, y, sw, y + 8)
                            wake_win.after(12, sweep, y + 50)
                        else:
                            canvas.delete(laser)
                
                sweep(0)
                wake_win_ref[0] = wake_win

            elif action == 'SLEEP':
                if wake_win_ref[0] and wake_win_ref[0].winfo_exists():
                    wake_win_ref[0].destroy()
                    wake_win_ref[0] = None

            # ---------------------------------------------------------
            # GRAB: FILE SELECTION TRIGGER
            # ---------------------------------------------------------
            elif action == 'GRAB_FILE':
                if wake_win_ref[0] and wake_win_ref[0].winfo_exists():
                    wake_win_ref[0].destroy()
                    wake_win_ref[0] = None
                    
                from tkinter import filedialog
                import shutil
                
                root.attributes('-topmost', True)
                selected_file = filedialog.askopenfilename(
                    title="Vaayu - Select a File to Share", 
                    filetypes=[("Image Files", "*.jpg *.jpeg *.png")]
                )
                root.attributes('-topmost', False)
                
                if selected_file:
                    shutil.copy(selected_file, filepath)
                    send_payload_async(filepath) 
                    
                    flash = tk.Toplevel(root)
                    flash.overrideredirect(True)
                    flash.geometry(f"{sw}x{sh}+0+0")
                    flash.attributes('-alpha', 0.45)
                    flash.configure(bg='white')
                    flash.attributes('-topmost', True)

                    def start_grab_anim():
                        flash.destroy()
                        try:
                            img = Image.open(filepath)
                            img.thumbnail((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
                            tk_img = ImageTk.PhotoImage(img)
                        except Exception:
                            return

                        thumb_win = tk.Toplevel(root)
                        thumb_win.overrideredirect(True)
                        thumb_win.attributes('-topmost', True)
                        thumb_win.attributes('-transparentcolor', '#010101')
                        thumb_win.configure(bg='#010101')
                        lbl_thumb = tk.Label(thumb_win, image=tk_img, bg='#010101')
                        lbl_thumb.image = tk_img
                        lbl_thumb.pack()

                        bin_win = tk.Toplevel(root)
                        bin_win.overrideredirect(True)
                        bin_win.attributes('-topmost', True)
                        bin_win.attributes('-transparentcolor', '#010101')
                        bin_win.configure(bg='#010101')
                        if tk_mascot:
                            lbl_bin = tk.Label(bin_win, image=tk_mascot, bg='#010101')
                            lbl_bin.image = tk_mascot
                            lbl_bin.pack()
                        
                        thumb_win.geometry(f"+{center_x}+{center_y}")
                        bin_win.geometry(f"+{left_x}+{sh}")

                        def stage4(): animate(bin_win, (left_x, bottom_y), (left_x, sh), 20, 15, 'in', bin_win.destroy)
                        def stage3():
                            if thumb_win.winfo_exists(): thumb_win.destroy()
                            if bin_win.winfo_exists(): bin_win.after(300, stage4)
                        def stage2():
                            bin_win.lift()
                            animate(thumb_win, (left_x, left_y), (left_x, bottom_y), 15, 12, 'in', stage3)
                        def stage1(): animate(bin_win, (left_x, sh), (left_x, bottom_y), 20, 15, 'out', stage2)
                        def stage0(): animate(thumb_win, (center_x, center_y), (left_x, left_y), 25, 15, 'out', stage1)
                        stage0()
                    
                    flash.after(180, start_grab_anim)

            # ---------------------------------------------------------
            # GRAB: SCREENSHOT ANIMATION TRIGGER
            # ---------------------------------------------------------
            elif action == 'GRAB_ANIM':
                if wake_win_ref[0] and wake_win_ref[0].winfo_exists():
                    wake_win_ref[0].destroy()
                    wake_win_ref[0] = None

                flash = tk.Toplevel(root)
                flash.overrideredirect(True)
                flash.geometry(f"{sw}x{sh}+0+0")
                flash.attributes('-alpha', 0.45)
                flash.configure(bg='white')
                flash.attributes('-topmost', True)

                def start_screenshot_anim():
                    flash.destroy()
                    try:
                        img = Image.open(filepath)
                        img.thumbnail((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
                        tk_img = ImageTk.PhotoImage(img)
                    except Exception:
                        return

                    thumb_win = tk.Toplevel(root)
                    thumb_win.overrideredirect(True)
                    thumb_win.attributes('-topmost', True)
                    thumb_win.attributes('-transparentcolor', '#010101')
                    thumb_win.configure(bg='#010101')
                    lbl_thumb = tk.Label(thumb_win, image=tk_img, bg='#010101')
                    lbl_thumb.image = tk_img
                    lbl_thumb.pack()

                    bin_win = tk.Toplevel(root)
                    bin_win.overrideredirect(True)
                    bin_win.attributes('-topmost', True)
                    bin_win.attributes('-transparentcolor', '#010101')
                    bin_win.configure(bg='#010101')
                    if tk_mascot:
                        lbl_bin = tk.Label(bin_win, image=tk_mascot, bg='#010101')
                        lbl_bin.image = tk_mascot
                        lbl_bin.pack()
                    
                    thumb_win.geometry(f"+{center_x}+{center_y}")
                    bin_win.geometry(f"+{left_x}+{sh}")

                    def stage4(): animate(bin_win, (left_x, bottom_y), (left_x, sh), 20, 15, 'in', bin_win.destroy)
                    def stage3():
                        if thumb_win.winfo_exists(): thumb_win.destroy()
                        if bin_win.winfo_exists(): bin_win.after(300, stage4)
                    def stage2():
                        bin_win.lift()
                        animate(thumb_win, (left_x, left_y), (left_x, bottom_y), 15, 12, 'in', stage3)
                    def stage1(): animate(bin_win, (left_x, sh), (left_x, bottom_y), 20, 15, 'out', stage2)
                    def stage0(): animate(thumb_win, (center_x, center_y), (left_x, left_y), 25, 15, 'out', stage1)
                    stage0()
                
                flash.after(180, start_screenshot_anim)

            # ---------------------------------------------------------
            # THE DROP SEQUENCE 
            # ---------------------------------------------------------
            elif action == 'DROP':
                if wake_win_ref[0] and wake_win_ref[0].winfo_exists():
                    wake_win_ref[0].destroy()
                    wake_win_ref[0] = None
                    
                hud = tk.Toplevel(root)
                hud.overrideredirect(True)
                hud.geometry(f"{sw}x{sh}+0+0")
                hud.attributes('-transparentcolor', 'black')
                hud.configure(bg='black')
                hud.attributes('-topmost', True)
                canvas = tk.Canvas(hud, width=sw, height=sh, bg='black', highlightthickness=0)
                canvas.pack()
                canvas.create_rectangle(10, 10, sw-10, sh-10, outline='cyan', width=20)

                def start_drop_anim():
                    hud.destroy()
                    
                    try:
                        img = Image.open(filepath)
                        img.thumbnail((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
                        tk_img = ImageTk.PhotoImage(img)
                    except Exception:
                        return

                    bin_win = tk.Toplevel(root)
                    bin_win.overrideredirect(True)
                    bin_win.attributes('-topmost', True)
                    bin_win.attributes('-transparentcolor', '#010101')
                    bin_win.configure(bg='#010101')
                    if tk_mascot:
                        lbl_bin = tk.Label(bin_win, image=tk_mascot, bg='#010101')
                        lbl_bin.image = tk_mascot
                        lbl_bin.pack()

                    thumb_win = tk.Toplevel(root)
                    thumb_win.overrideredirect(True)
                    thumb_win.attributes('-topmost', True)
                    thumb_win.attributes('-transparentcolor', '#010101')
                    thumb_win.configure(bg='#010101')
                    lbl_thumb = tk.Label(thumb_win, image=tk_img, bg='#010101')
                    lbl_thumb.image = tk_img
                    lbl_thumb.pack(expand=True)

                    bin_win.geometry(f"+{left_x}+{sh}")
                    thumb_win.geometry(f"+{left_x}+{sh}") 

                    def stage4_cleanup():
                        if thumb_win.winfo_exists(): thumb_win.destroy()
                        if bin_win.winfo_exists(): bin_win.destroy()

                    def stage3_fullscreen():
                        thumb_win.attributes('-transparentcolor', '') 
                        thumb_win.configure(bg='black')
                        thumb_win.geometry(f"{sw}x{sh}+0+0")
                        
                        full_img = Image.open(filepath)
                        full_img.thumbnail((sw, sh), Image.Resampling.LANCZOS)
                        tk_full = ImageTk.PhotoImage(full_img)
                        
                        lbl_thumb.configure(image=tk_full, bg='black')
                        lbl_thumb.image = tk_full
                        
                        threading.Thread(target=copy_to_clipboard, args=(filepath,), daemon=True).start()
                        
                        close_btn = tk.Button(thumb_win, text="✕", font=("Segoe UI", 12), 
                                              bg="black", fg="white", bd=0, relief="flat",
                                              activebackground="#E81123", activeforeground="white",
                                              cursor="hand2", command=stage4_cleanup)
                        close_btn.place(x=sw-45, y=0, width=45, height=30)
                        
                        def on_enter(e): close_btn.config(bg="#E81123")
                        def on_leave(e): close_btn.config(bg="black")
                        close_btn.bind("<Enter>", on_enter)
                        close_btn.bind("<Leave>", on_leave)

                    def stage2_glide_center():
                        animate(bin_win, (left_x, bottom_y), (left_x, sh), 20, 15, 'in') 
                        animate(thumb_win, (left_x, left_y), (center_x, center_y), 25, 12, 'out', stage3_fullscreen)

                    def stage1_eject():
                        thumb_win.lift()
                        animate(thumb_win, (left_x, bottom_y), (left_x, left_y), 15, 12, 'out', stage2_glide_center)

                    def stage0_bin_rise():
                        animate(bin_win, (left_x, sh), (left_x, bottom_y), 20, 15, 'out', stage1_eject)

                    stage0_bin_rise()

                hud.after(300, start_drop_anim)

        except queue.Empty:
            pass
        root.after(10, check_queue)

    root.after(10, check_queue)
    root.mainloop()

# ==========================================
# BRAIN 1: AI VISION & MAIN PIPELINE
# ==========================================
def draw_sci_fi_corners(img, bbox, color, length=20, thickness=3):
    x, y, w_box, h_box = bbox
    cv2.line(img, (x, y), (x + length, y), color, thickness)
    cv2.line(img, (x, y), (x, y + length), color, thickness)
    cv2.line(img, (x + w_box, y), (x + w_box - length, y), color, thickness)
    cv2.line(img, (x + w_box, y), (x + w_box, y + length), color, thickness)
    cv2.line(img, (x, y + h_box), (x + length, y + h_box), color, thickness)
    cv2.line(img, (x, y + h_box), (x, y + h_box - length), color, thickness)
    cv2.line(img, (x + w_box, y + h_box), (x + w_box - length, y + h_box), color, thickness)
    cv2.line(img, (x + w_box, y + h_box), (x + w_box, y + h_box - length), color, thickness)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    
    SAVE_DIR_OUTBOUND = "spatial_screenshots"
    if not os.path.exists(SAVE_DIR_OUTBOUND): os.makedirs(SAVE_DIR_OUTBOUND)

    ui_queue = multiprocessing.Queue()
    anim_process = multiprocessing.Process(target=animation_worker, args=(ui_queue,))
    anim_process.start()
    
    network_inbound_queue = multiprocessing.Queue()
    net_thread = threading.Thread(target=network_listener_worker, args=(network_inbound_queue,), daemon=True)
    net_thread.start()

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.8, min_tracking_confidence=0.8)
    mp_draw = mp.solutions.drawing_utils

    MIN_PALM_DISTANCE = 60  
    MAX_PALM_DISTANCE = 200  
    TIP_IDS = [8, 12, 16, 20]  

    last_action_time = 0
    COOLDOWN_SECONDS = 3.5  
    system_awake = False
    awake_mode = None  
    was_awake = False 
    awake_until = 0
    AWAKE_DURATION = 4.0  
    
    active_payload = None

    cap = cv2.VideoCapture(0)
    print("[*] Vaayu Spatial Engine Active (Dual-Trigger & Lidar Sweep Enabled)...")

    while cap.isOpened():
        success, frame = cap.read()
        if not success: break
            
        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape  
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        current_time = time.time()
        
        try:
            active_payload = network_inbound_queue.get_nowait()
            print(f"[!] New Network Payload buffered in memory: {active_payload}")
        except queue.Empty:
            pass

        if system_awake and current_time > awake_until: 
            system_awake = False  
            awake_mode = None
        
        status_text, status_color = "Status: STANDBY", (150, 150, 150)  
        gesture_text, gesture_color = "Gesture: None", (0, 255, 255)
        
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                x_max = y_max = 0
                x_min, y_min = w, h
                for lm in hand_landmarks.landmark:
                    x_px, y_px = int(lm.x * w), int(lm.y * h)
                    if x_px > x_max: x_max = x_px
                    if x_px < x_min: x_min = x_px
                    if y_px > y_max: y_max = y_px
                    if y_px < y_min: y_min = y_px
                
                pad = 20
                hand_bbox = (max(0, x_min-pad), max(0, y_min-pad), min(w, x_max-x_min+(pad*2)), min(h, y_max-y_min+(pad*2)))
                
                wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
                middle_base = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                
                x1, y1 = int(wrist.x * w), int(wrist.y * h)
                x2, y2 = int(middle_base.x * w), int(middle_base.y * h)
                palm_distance = max(math.sqrt((x2 - x1)**2 + (y2 - y1)**2), 1.0)
                
                if MIN_PALM_DISTANCE <= palm_distance <= MAX_PALM_DISTANCE:
                    status_text, status_color = "Status: ACTIVE ZONE", (0, 255, 0)  
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    
                    tight_closed_fingers = open_fingers = 0
                    finger_states = {}
                    
                    for tip_id in TIP_IDS:
                        tip = hand_landmarks.landmark[tip_id]
                        pip = hand_landmarks.landmark[tip_id - 2]
                        mcp = hand_landmarks.landmark[tip_id - 3]
                        
                        if tip.y < pip.y:
                            open_fingers += 1
                            finger_states[tip_id] = "OPEN"
                        elif tip.y > mcp.y: 
                            tight_closed_fingers += 1
                            finger_states[tip_id] = "CLOSED"
                        else:
                            finger_states[tip_id] = "PARTIAL"
                            
                    # 1. SCREENSHOT WAKE TRIGGER (Peace Sign)
                    if (finger_states.get(8) == "OPEN" and finger_states.get(12) == "OPEN" and
                        finger_states.get(16) == "CLOSED" and finger_states.get(20) == "CLOSED"):
                        system_awake = True
                        awake_mode = 'SCREENSHOT'
                        awake_until = current_time + AWAKE_DURATION
                        gesture_text, gesture_color = "AWAKE: Screenshot Mode", (255, 105, 180)
                    
                    # 2. FILE SHARING WAKE TRIGGER (3 Fingers: Index, Middle, Ring OPEN)
                    elif (finger_states.get(8) == "OPEN" and finger_states.get(12) == "OPEN" and
                          finger_states.get(16) == "OPEN" and finger_states.get(20) == "CLOSED"):
                        system_awake = True
                        awake_mode = 'FILE'
                        awake_until = current_time + AWAKE_DURATION
                        gesture_text, gesture_color = "AWAKE: File Sharing Mode", (0, 255, 255)
                    
                    elif system_awake:
                        draw_sci_fi_corners(frame, hand_bbox, (255, 200, 0), length=30, thickness=2)
                        
                        # --- THE GRAB GESTURE ---
                        if tight_closed_fingers == 4:
                            if current_time - last_action_time > COOLDOWN_SECONDS:
                                inverted_timestamp = int(10000000000 - time.time())
                                
                                if awake_mode == 'SCREENSHOT':
                                    gesture_text, gesture_color = "Action: CAPTURE SCREENSHOT", (255, 0, 255)
                                    filepath = os.path.join(SAVE_DIR_OUTBOUND, f"vaayu_screenshot_{inverted_timestamp}.png")
                                    
                                    try:
                                        screenshot = pyautogui.screenshot()
                                        screenshot.save(filepath)
                                        send_payload_async(filepath)
                                        active_payload = filepath
                                        ui_queue.put(('GRAB_ANIM', filepath))
                                    except Exception as e:
                                        print(f"Screenshot failed: {e}")
                                        
                                elif awake_mode == 'FILE':
                                    gesture_text, gesture_color = "Action: SELECT FILE", (0, 255, 255)
                                    filepath = os.path.join(SAVE_DIR_OUTBOUND, f"vaayu_file_{inverted_timestamp}.png")
                                    
                                    ui_queue.put(('GRAB_FILE', filepath))
                                    active_payload = filepath
                                
                                last_action_time = current_time
                                system_awake = False
                                awake_mode = None
                                
                        # --- THE DROP GESTURE ---
                        elif open_fingers == 4:
                            gesture_text, gesture_color = "Action: DROP", (255, 255, 0)
                            if current_time - last_action_time > COOLDOWN_SECONDS:
                                if active_payload is not None:
                                    ui_queue.put(('DROP', active_payload))
                                    
                                    last_action_time = current_time
                                    system_awake = False
                                    awake_mode = None
                                else:
                                    gesture_text, gesture_color = "Buffer Empty", (0, 0, 255)
                                    
                        else:
                            mode_label = "Screenshot" if awake_mode == 'SCREENSHOT' else "File"
                            gesture_text, gesture_color = f"LISTENING [{mode_label}] ({round(awake_until - current_time, 1)}s)", (255, 200, 0)
                    else:
                        gesture_text, gesture_color = "STANDBY (Peace=Screen | 3-Finger=File)", (150, 150, 150)
                else:
                    status_text, status_color = "Status: OUT OF RANGE", (0, 165, 255)
                    system_awake = False
                    awake_mode = None
        else:
            system_awake = False
            awake_mode = None
                
        cv2.putText(frame, status_text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 1, cv2.LINE_AA)
        cv2.putText(frame, gesture_text, (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, gesture_color, 2, cv2.LINE_AA)
        
        if active_payload:
            cv2.putText(frame, "PAYLOAD READY TO DROP", (w - 280, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
            
        if system_awake: cv2.rectangle(frame, (0,0), (w,h), (255, 200, 0), 4)
        
        if system_awake and not was_awake:
            ui_queue.put(('WAKE', None))
        elif not system_awake and was_awake:
            ui_queue.put(('SLEEP', None))
            
        was_awake = system_awake
        
        cv2.imshow("Vaayu Spatial Engine", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            ui_queue.put("QUIT")
            break

    cap.release()
    cv2.destroyAllWindows()