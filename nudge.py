import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import random
import time
import threading
import sys
import os
import wave
import struct
import queue
import math
import webbrowser
import subprocess

try:
    from pynput import mouse, keyboard
    import win32api
    import win32con
    import win32gui
    import pywintypes
    import pystray
except ImportError:
    sys.exit(1)

FPS = 60
BLACK = "#000000"
RED = "#C80000"
WHITE = "#FFFFFF"
KEY = "#FF0080"

MOVE_TEXT = "DON'T MOVE"
IMAGE_DIR = "images"
SOUND_DIR = "sounds"
ENTITY_DIR = "entities"
FALLBACK_FILE = "t_s.wav"

#chances of events happening (the lower the number, the more likely and vice versa)
TYPING_CHANCE_KEY = 100
TYPING_CHANCE_GENERAL = 1300
JUMPSCARE_CHANCE = 200
MOVE_CHANCE = 500
ENTITY_CHANCE = 600
POPUP_CHANCE = 700
RPS_CHANCE = 800
SWAP_CHANCE = 900
FLIP_CHANCE = 1000
TIME_CHANCE = 1100
BROWSER_CHANCE = 1200

def create_temp_wav(f):
    if os.path.exists(f): return
    duration, freq, bits, n_chan = 200, 44100, 16, 1
    s_width = bits // 8
    max_amp = 2**(bits - 1) - 1
    total_samples = int(freq * (duration / 1000.0))
    frames = bytearray()
    for _ in range(total_samples):
        sample = random.randint(-max_amp, max_amp)
        frames += struct.pack('<h', sample)
    try:
        with wave.open(f, 'wb') as wf:
            wf.setnchannels(n_chan)
            wf.setsampwidth(s_width)
            wf.setframerate(freq)
            wf.writeframes(frames)
    except Exception:
        pass


class Manager:
    def __init__(self, q):
        self.lock = threading.Lock()
        self.active = None
        self.q = q
        self.move_data = {'f': False, 'a': False}
        self.mouse_pos = (0, 0)
        self.popup_active = False
        self.popup_count = 10
        self.popup_limit = 10
        self.kb_c = keyboard.Controller()
        self.i_paths, self.s_paths, self.e_paths = [], [], []
        self.load_assets()
        self.is_active = False

    def arm(self):
        self.is_active = True

    def load_assets(self):
        if os.path.isdir(IMAGE_DIR):
            self.i_paths.extend([os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))])
        
        if os.path.isdir(SOUND_DIR):
            self.s_paths.extend([os.path.join(SOUND_DIR, f) for f in os.listdir(SOUND_DIR) if f.lower().endswith('.wav')])
        else:
            create_temp_wav(FALLBACK_FILE)
            self.s_paths.append(FALLBACK_FILE)
        
        if os.path.isdir(ENTITY_DIR):
            self.e_paths.extend([os.path.join(ENTITY_DIR, f) for f in os.listdir(ENTITY_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))])

    def update_mouse_pos(self, x, y):
        self.mouse_pos = (x, y)

    def on_mouse(self):
        if not self.is_active:
            return
            
        if self.active == "dont_move" and self.move_data.get('a'):
            self.move_data['f'] = True
        elif self.active is None:
            self.check_random_horror(check_typing=True)

    def on_press(self, key):
        if not self.is_active:
            return True
            
        triggered = False

        if self.active == "dont_move" and self.move_data.get('a'):
            self.move_data['f'] = True
        
        elif self.active is None:
            if random.randint(1, TYPING_CHANCE_KEY) == 1:
                if self.lock.acquire(blocking=False):
                    try:
                        self.active = "typing_possession"
                        self.q.put({'event': 'typing_possession'})
                        triggered = True
                    except Exception:
                        self.lock.release()
            
            if not triggered:
                self.check_random_horror(check_typing=True)

        return True

    def check_random_horror(self, check_typing=False):
        if self.lock.acquire(blocking=False):
            hell_triggered = False
            try:
                if check_typing and random.randint(1, TYPING_CHANCE_GENERAL) == 1:
                    self.active = "typing_possession"
                    self.q.put({'event': 'typing_possession'})
                elif random.randint(1, BROWSER_CHANCE) == 1:
                    self.active = "browser_hijack"
                    self.q.put({'event': 'browser_hijack'})
                elif random.randint(1, TIME_CHANCE) == 1:
                    self.active = "time_warp"
                    self.q.put({'event': 'time_warp'})
                elif random.randint(1, FLIP_CHANCE) == 1:
                    self.active = "screen_flip"
                    self.q.put({'event': 'screen_flip'})
                elif random.randint(1, SWAP_CHANCE) == 1:
                    self.active = "window_swap"
                    self.q.put({'event': 'window_swap'})
                elif random.randint(1, RPS_CHANCE) == 1 and not self.popup_active:
                    self.active = "rps_game"
                    self.q.put({'event': 'rps_game'})
                elif random.randint(1, POPUP_CHANCE) == 1 and not self.popup_active:
                    self.popup_active = True
                    hell_triggered = True
                    self.q.put({'event': 'popup_hell'})
                elif random.randint(1, MOVE_CHANCE) == 1:
                    self.active = "dont_move"
                    self.move_data = {'f': False, 'a': False}
                    self.q.put({'event': 'dont_move'})
                elif random.randint(1, JUMPSCARE_CHANCE) == 1:
                    self.active = "jumpscare"
                    self.q.put({'event': 'jumpscare', 'duration': 0.3})
                elif random.randint(1, ENTITY_CHANCE) == 1:
                    self.active = "entity"
                    target = self.mouse_pos
                    self.q.put({'event': 'entity', 'target': target})
                else:
                    self.lock.release()
            except Exception:
                self.lock.release()
            
            if hell_triggered:
                self.lock.release()

    def finish_event(self):
        self.active = None
        if self.lock.locked():
            self.lock.release()

    def finish_popup(self):
        self.popup_active = False


class GUI:
    def __init__(self, m, ml, kl):
        self.m = m
        self.ml = ml
        self.kl = kl
        self.root = tk.Tk()
        self.w = self.root.winfo_screenwidth()
        self.h = self.root.winfo_screenheight()
        self.popups = []
        self.timer_id = None
        self.countdown = 0
        self.tray = None
        self.setup_panel()

    def setup_panel(self):
        self.root.title("Control Panel")
        frame = tk.Frame(self.root, padx=20, pady=15)
        frame.pack()
        tk.Label(frame, text="NUDGE", font=("Arial", 16, "bold")).pack(pady=(0, 10))
        tk.Label(frame, text="Stop yourself after...", wraplength=250).pack(pady=(0, 15))

        e_f = tk.Frame(frame)
        e_f.pack(pady=5)
        
        h_f = tk.Frame(e_f); h_f.pack(side='left', padx=5)
        tk.Label(h_f, text="Hours:").pack(side='top')
        self.e_h = tk.Entry(h_f, width=5); self.e_h.pack(side='bottom'); self.e_h.insert(0, "0")

        m_f = tk.Frame(e_f); m_f.pack(side='left', padx=5)
        tk.Label(m_f, text="Minutes:").pack(side='top')
        self.e_m = tk.Entry(m_f, width=5); self.e_m.pack(side='bottom'); self.e_m.insert(0, "15")

        s_f = tk.Frame(e_f); s_f.pack(side='left', padx=5)
        tk.Label(s_f, text="Seconds:").pack(side='top')
        self.e_s = tk.Entry(s_f, width=5); self.e_s.pack(side='bottom'); self.e_s.insert(0, "0")

        self.btn = tk.Button(frame, text="Begin...", command=self.start_countdown, font=("Arial", 10, "bold"), bg="#C80000", fg="white", relief="raised")
        self.btn.pack(pady=10, fill='x')
        self.err_l = tk.Label(frame, text="", fg="red"); self.err_l.pack(pady=(5, 0))

        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x, y = (self.w // 2) - (w // 2), (self.h // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')
        self.root.resizable(False, False)

    def start_countdown(self):
        h_s, m_s, s_s = self.e_h.get(), self.e_m.get(), self.e_s.get()
        try:
            h = float(h_s) if h_s else 0
            m = float(m_s) if m_s else 0
            s = float(s_s) if s_s else 0
            total = (h * 3600) + (m * 60) + s
            if total <= 0:
                raise ValueError
            self.err_l.config(text="")
            self.countdown = int(total)
            self.root.withdraw()
            self.ml.start()
            self.kl.start()
            threading.Thread(target=self.start_tray, daemon=True).start()
            self.root.after(1000, self.update_countdown)
        except ValueError:
            self.err_l.config(text="Please enter valid, positive numbers.")

    def create_tray_img(self):
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        dc = ImageDraw.Draw(img)
        dc.ellipse((2, 2, 62, 62), fill=RED, outline=WHITE, width=4)
        dc.text((16, 18), "FF", fill=WHITE, font_size=32)
        return img

    def start_tray(self):
        def on_quit(icon, item):
            icon.stop()
            self.root.quit()

        img = self.create_tray_img()
        menu = pystray.Menu(pystray.MenuItem('Quit NUDGE', on_quit))
        self.tray = pystray.Icon("NUDGE", img, "NUDGE", menu)
        h = self.countdown // 3600
        m = (self.countdown % 3600) // 60
        s = self.countdown % 60
        self.tray.title = f"NUDGE starts in {h}:{m:02d}:{s:02d}"
        self.tray.run()

    def update_countdown(self):
        if self.countdown > 0:
            self.countdown -= 1
            h = self.countdown // 3600
            m = (self.countdown % 3600) // 60
            s = self.countdown % 60
            new_title = f"NUDGE starts in {h}:{m:02d}:{s:02d}"
            if self.tray:
                self.tray.title = new_title
            self.root.after(1000, self.update_countdown)
        else:
            if self.tray:
                self.tray.title = "NUDGE IS ACTIVE"
            self.m.arm()

    def run(self):
        self.process_queue()
        self.root.mainloop()

    def process_queue(self):
        try:
            task = self.m.q.get_nowait()
            event = task.get('event')
            if event == 'jumpscare':
                self.create_jumpscare(task['duration'])
            elif event == 'dont_move':
                self.create_dont_move()
            elif event == 'entity':
                self.create_entity(task.get('target', (self.w / 2, self.h / 2)))
            elif event == 'popup_hell':
                self.create_popup_hell()
            elif event == 'rps_game':
                self.create_rps_game()
            elif event == 'window_swap':
                self.create_window_swap()
            elif event == 'screen_flip':
                self.create_screen_flip()
            elif event == 'time_warp':
                self.create_time_warp()
            elif event == 'browser_hijack':
                self.create_browser_hijack()
            elif event == 'typing_possession':
                self.create_typing_possession()
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.process_queue)

    def create_overlay(self):
        o = tk.Toplevel(self.root)
        o.geometry(f"{self.w}x{self.h}+0+0")
        o.overrideredirect(True)
        o.wm_attributes("-topmost", True)
        o.wm_attributes("-transparentcolor", KEY)
        o.config(bg=KEY)
        c = tk.Canvas(o, width=self.w, height=self.h, bg=KEY, highlightthickness=0)
        c.pack()
        return o, c

    def play_sound(self):
        if self.m.s_paths:
            f = random.choice(self.m.s_paths)
            winsound.PlaySound(f, winsound.SND_FILENAME | winsound.SND_ASYNC)

    def show_content(self, c):
        c.delete("all")
        if not self.m.i_paths:
            c.config(bg=BLACK)
            w, h = self.w, self.h
            r = w // 8
            c.create_oval(w//4 - r, h//3 - r, w//4 + r, h//3 + r, fill=RED, outline="")
            c.create_oval(w*3//4 - r, h//3 - r, w*3//4 + r, h//3 + r, fill=RED, outline="")
            mouth = [w//4, h*2//3, w*3//4, h*2//3, w//2, h*5//6]
            c.create_polygon(mouth, fill=RED, outline="")
        else:
            try:
                p = random.choice(self.m.i_paths)
                img = Image.open(p)
                w, h = img.size
                a_s = self.w / self.h
                a_i = w / h
                if a_i > a_s:
                    n_h = self.h
                    n_w = int(n_h * a_i)
                else:
                    n_w = self.w
                    n_h = int(n_w / a_i)
                img = img.resize((n_w, n_h), Image.Resampling.LANCZOS)
                self.photo = ImageTk.PhotoImage(img)
                c.config(bg=BLACK)
                c.create_image(self.w//2, self.h//2, image=self.photo)
            except Exception:
                self.m.i_paths.clear()
                self.show_content(c)

    def create_jumpscare(self, duration, is_consequence=False):
        o, c = self.create_overlay()
        self.play_sound()
        self.show_content(c)
        if not is_consequence:
            self.root.after(int(duration * 1000), lambda: [o.destroy(), winsound.PlaySound(None, winsound.SND_PURGE), self.m.finish_event()])
        else:
            self.root.after(int(duration * 1000), lambda: [o.destroy(), winsound.PlaySound(None, winsound.SND_PURGE)])

    def create_dont_move(self):
        o, c = self.create_overlay()
        c.create_text(self.w/2, self.h/2, text=MOVE_TEXT, fill=RED, font=("Arial", 60, "bold"))
        
        def start_d():
            self.m.move_data['a'] = True
            check_f(time.time() + 3)
            
        def check_f(end_time):
            if not o.winfo_exists():
                self.m.finish_event()
                return
            if self.m.move_data['f']:
                self.play_sound()
                self.show_content(c)
                self.root.after(500, lambda: [o.destroy(), winsound.PlaySound(None, winsound.SND_PURGE), self.m.finish_event()])
            elif time.time() >= end_time:
                o.destroy()
                self.m.finish_event()
            else:
                self.root.after(1000//FPS, lambda: check_f(end_time))
                
        self.root.after(1000, start_d)

    def create_entity(self, target_pos):
        o, c = self.create_overlay()
        h_w = o.winfo_id()
        style = win32gui.GetWindowLong(h_w, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(h_w, win32con.GWL_EXSTYLE, style | win32con.WS_EX_TRANSPARENT)
        w, h = 100, 200
        speed = random.randint(8, 12)
        edge = random.randint(0, 3)
        if edge == 0: start_x, start_y = random.randint(0, self.w - w), -h
        elif edge == 1: start_x, start_y = self.w, random.randint(0, self.h - h)
        elif edge == 2: start_x, start_y = random.randint(0, self.w - w), self.h
        else: start_x, start_y = -w, random.randint(0, self.h - h)
        t_x, t_y = target_pos
        angle = math.atan2(t_y - (start_y + h / 2), t_x - (start_x + w / 2))
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        body = None
        if self.m.e_paths:
            try:
                p = random.choice(self.m.e_paths)
                img = Image.open(p).resize((w, h), Image.Resampling.LANCZOS)
                self.e_photo = ImageTk.PhotoImage(img)
                body = c.create_image(start_x, start_y, image=self.e_photo, anchor='nw')
            except Exception: self.m.e_paths.clear()
        if body is None: body = c.create_rectangle(start_x, start_y, start_x + w, start_y + h, fill="#141414", outline="")
        
        def animate():
            if not o.winfo_exists(): self.m.finish_event(); return
            c.move(body, vx, vy)
            coords = c.coords(body)
            if not coords: o.destroy(); self.m.finish_event(); return
            ex, ey = coords[0], coords[1]
            ex2, ey2 = ex + w, ey + h
            mx, my = o.winfo_pointerxy()
            if ex < mx < ex2 and ey < my < ey2:
                self.play_sound()
                self.show_content(c)
                win32gui.SetWindowLong(h_w, win32con.GWL_EXSTYLE, style & ~win32con.WS_EX_TRANSPARENT)
                self.root.after(500, lambda: [o.destroy(), winsound.PlaySound(None, winsound.SND_PURGE), self.m.finish_event()])
                return
            if ex + w/2 < -w or ex + w/2 > self.w + w or ey + h/2 < -h or ey + h/2 > self.h + h:
                o.destroy(); self.m.finish_event(); return
            self.root.after(1000//FPS, animate)
            
        animate()

    def create_popup_hell(self):
        t_left = self.m.popup_limit
        
        def on_close(p):
            if p in self.popups:
                self.popups.remove(p)
            p.destroy()
            if not self.popups:
                if self.timer_id:
                    self.root.after_cancel(self.timer_id)
                    self.timer_id = None
                self.m.popup_count = 10
                self.m.popup_limit = 10
                self.m.finish_popup()

        for _ in range(self.m.popup_count):
            p = tk.Toplevel(self.root)
            p.geometry(f"200x100+{random.randint(0, self.w-200)}+{random.randint(0, self.h-100)}")
            p.wm_attributes("-topmost", True)
            p.title("Close It")
            p.protocol("WM_DELETE_WINDOW", lambda p=p: on_close(p))
            tk.Label(p, text=f"{t_left}", font=("Arial", 16), fg='red').pack(pady=5)
            tk.Button(p, text="Close", command=lambda p=p: on_close(p)).pack(pady=5)
            self.popups.append(p)

        def update_timer(current_time):
            if not self.popups: return
            for p in self.popups:
                if p.winfo_exists():
                    for w in p.winfo_children():
                        if isinstance(w, tk.Label):
                            w.config(text=f"{current_time}", fg='red')

            if current_time <= 0:
                self.m.popup_count += 5
                self.m.popup_limit += 5
                while self.popups:
                    p = self.popups.pop()
                    if p.winfo_exists():
                        p.destroy()
                self.timer_id = None
                self.create_jumpscare(0.5, is_consequence=True)
                self.root.after(500, self.create_popup_hell)
                return

            self.timer_id = self.root.after(1000, lambda: update_timer(current_time - 1))

        update_timer(t_left)

    def create_rps_game(self):
        p = tk.Toplevel(self.root)
        p.geometry(f"300x150+{random.randint(0, self.w - 300)}+{random.randint(0, self.h - 150)}")
        p.wm_attributes("-topmost", True)
        p.title("CHOOSE")
        p.resizable(False, False)

        correct = random.choice(['rock', 'paper', 'scissors'])
        info_l = tk.Label(p, text="Make the right choice, or else.", font=("Arial", 12))
        info_l.pack(pady=5)
        timer_l = tk.Label(p, text="", font=("Arial", 10))
        timer_l.pack(pady=5)
        btn_f = tk.Frame(p); btn_f.pack(pady=10)
        rps_id = [None]

        def handle_choice(c):
            if rps_id[0]: self.root.after_cancel(rps_id[0]); rps_id[0] = None
            for child in btn_f.winfo_children(): child.config(state='disabled')

            if c == correct:
                p.destroy()
                self.m.finish_event()
            else:
                info_l.config(text="YOU LOST", fg=RED, font=("Arial", 24, "bold"))
                def consequence():
                    p.destroy()
                    self.m.popup_count = 20
                    self.m.popup_limit = 20
                    if not self.m.popup_active:
                        self.m.popup_active = True
                        self.m.q.put({'event': 'popup_hell'})
                    self.m.finish_event()
                self.root.after(1000, consequence)

        def update_timer(t):
            if not p.winfo_exists():
                if rps_id[0]: self.root.after_cancel(rps_id[0])
                self.m.finish_event()
                return
            if t < 0:
                handle_choice(None)
                return
            timer_l.config(text=f"Time remaining: {t}", fg='red')
            rps_id[0] = self.root.after(1000, lambda: update_timer(t - 1))

        tk.Button(btn_f, text="Rock", command=lambda: handle_choice('rock')).pack(side='left', padx=5)
        tk.Button(btn_f, text="Paper", command=lambda: handle_choice('paper')).pack(side='left', padx=5)
        tk.Button(btn_f, text="Scissors", command=lambda: handle_choice('scissors')).pack(side='left', padx=5)
        update_timer(10)

    def create_window_swap(self):
        windows = []
        def win_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) != '' and "NUDGE" not in win32gui.GetWindowText(hwnd):
                windows.append(hwnd)
        
        win32gui.EnumWindows(win_handler, None)
        foreground = win32gui.GetForegroundWindow()
        others = [hwnd for hwnd in windows if hwnd != foreground]
        
        if others:
            o, c = self.create_overlay()
            c.config(bg=BLACK)
            
            def do_swap():
                new_hwnd = random.choice(others)
                try:
                    win32gui.ShowWindow(new_hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(new_hwnd)
                except pywintypes.error:
                    pass
                except Exception:
                    pass

                o.destroy()
                self.m.finish_event()
            self.root.after(100, do_swap)
        else:
            self.m.finish_event()

    def create_screen_flip(self):
        try:
            device = win32api.EnumDisplayDevices(None, 0)
            dm = win32api.EnumDisplaySettings(device.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
            original = dm.DisplayOrientation
            new = win32con.DMDO_180 if original == win32con.DMDO_DEFAULT else win32con.DMDO_DEFAULT
            dm.DisplayOrientation = new
            dm.Fields = dm.Fields | win32con.DM_DISPLAYORIENTATION
            win32api.ChangeDisplaySettingsEx(device.DeviceName, dm)

            def revert():
                try:
                    current = win32api.EnumDisplaySettings(device.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
                    if current.DisplayOrientation != original:
                        current.DisplayOrientation = original
                        current.Fields = current.Fields | win32con.DM_DISPLAYORIENTATION
                        win32api.ChangeDisplaySettingsEx(device.DeviceName, current)
                except Exception:
                    pass
                finally:
                    self.m.finish_event()
            
            self.root.after(5000, revert)
        except Exception:
            self.m.finish_event()

    def create_time_warp(self):
        original = win32api.GetLocalTime()
        try:
            new = (
                original[0] + random.randint(-5, 5),
                random.randint(1, 12),
                original[2],
                random.randint(1, 28),
                random.randint(0, 23),
                random.randint(0, 59),
                random.randint(0, 59),
                original[7]
            )
            win32api.SetSystemTime(*new)
            
            def revert_time():
                try:
                    win32api.SetSystemTime(*original)
                except pywintypes.error as e:
                    if e.winerror == 1314:
                        pass
                except Exception:
                    pass
            self.root.after(8000, revert_time)

        except pywintypes.error as e:
            if e.winerror == 1314:
                pass
        except Exception:
            pass

        noti = tk.Toplevel(self.root)
        w, h = 300, 100
        x = self.w - w - 10
        y = self.h - h - 40
        noti.geometry(f"{w}x{h}+{x}+{y}")
        noti.overrideredirect(True)
        noti.wm_attributes("-topmost", True)
        noti.config(bg="#333333", borderwidth=1, relief="solid")

        #messages to display
        msgs = [
            "Logging off", 
            "Your soul is due", 
            "Touching grass", 
            "I'm watching you", 
            "Standing behind you", 
            "Sleep"
        ]
        tk.Label(noti, text="Upcoming Event", bg="#333333", fg=WHITE, font=("Arial", 10, "bold"), anchor="w").pack(fill="x", padx=5, pady=(5, 0))
        tk.Label(noti, text=random.choice(msgs), bg="#333333", fg=WHITE, font=("Arial", 12), anchor="w", justify="left").pack(fill="x", padx=5, pady=(0, 5))

        def close_noti():
            if noti.winfo_exists():
                noti.destroy()
            self.m.finish_event()
        self.root.after(7000, close_noti)

    def create_browser_hijack(self):
        #urls to open
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", 
            "https://www.nyan.cat/", 
            "https://pointerpointer.com/", 
            "https://www.lomando.com/main.html", 
            "https://en.wikipedia.org/wiki/Special:Random"
        ]
        try:
            webbrowser.open_new_tab(random.choice(urls))
        except Exception:
            pass
        finally:
            self.m.finish_event()

    def create_typing_possession(self):
        try:
            subprocess.Popen(['notepad.exe'])
        except Exception:
            self.m.finish_event()
            return

        def type_msg():
            try:
                #text to type in notepad
                msgs = [
                    "I see you.", 
                    "You aren't safe.", 
                    "Look behind you.", 
                    "Why did you let this happen?", 
                    "It's all your fault.", 
                    "He is coming.", 
                    "You can't escape me.", 
                    "RUN.",
                    "Turn it off",
                    "Visit zumthezazaking.com",
                ]
                msg = random.choice(msgs)
                self.m.kb_c.type(msg)
            except Exception:
                pass
            finally:
                self.m.finish_event()

        self.root.after(1000, type_msg)


def run():
    if sys.platform != "win32":
        sys.exit(1)
    
    q = queue.Queue()
    m = Manager(q)

    def on_move_w(x, y): 
        m.update_mouse_pos(x, y)
        m.on_mouse()
    def on_click_w(x, y, button, pressed): 
        m.update_mouse_pos(x, y)
        m.on_mouse()
    
    ml = mouse.Listener(on_move=on_move_w, on_click=on_click_w)
    kl = keyboard.Listener(on_press=m.on_press, suppress=False)
    gui = GUI(m, ml, kl)
    
    try:
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        if ml.is_alive(): ml.stop()
        if kl.is_alive(): kl.stop()
        if gui.tray: gui.tray.stop()
        ml.join()
        kl.join()

if __name__ == "__main__":
    run()