import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import random
import time
import threading
import sys
import os
import wave
import struct
import atexit
import winsound
import queue
import math
import webbrowser
import subprocess

# --- Dependencies for Global Input and Overlay ---
# You must install these libraries: pip install pynput pywin32 Pillow pystray
try:
    from pynput import mouse, keyboard
    import win32api
    import win32con
    import win32gui
    import pywintypes
    import pystray
except ImportError:
    print("Required libraries not found. Please run:")
    print("pip install pynput pywin32 Pillow pystray")
    sys.exit(1)

# --- Configuration ---
FPS = 60
BLACK = "#000000"
RED = "#C80000"
WHITE = "#FFFFFF"
CHROMA_KEY = "#FF0080"  # A magenta-like color

# --- Customization ---
DONT_MOVE_TEXT = "DON'T YOU DARE MOVE"
IMAGE_FOLDER = "images"
SOUND_FOLDER = "sounds"
ENTITY_FOLDER = "entities"
FALLBACK_SOUND_FILE = "temp_scream.wav"

# --- Horror Event Probabilities ---
# TEMPORARY DEMO SETTINGS
TYPING_POSSESSION_ON_KEYPRESS_CHANCE = 2 # Was 100
TYPING_POSSESSION_GENERAL_CHANCE = 2     # Was 1300

JUMPSCARE_CHANCE = 2                     # Was 200
DONT_MOVE_CHANCE = 99999                 # Disable this one for the demo
ENTITY_CHANCE = 2                        # Was 600
POPUP_HELL_CHANCE = 3                    # Was 700
RPS_CHANCE = 3                           # 
WINDOW_SWAP_CHANCE = 4                   # Was 900
SCREEN_FLIP_CHANCE = 3                   # Was 1000
TIME_WARP_CHANCE = 99999                 # Disable this
BROWSER_HIJACK_CHANCE = 4                # Was 1200


# --- Asset Creation & Cleanup ---

def create_fallback_scream_wav(filename):
    if os.path.exists(filename): return
    duration_ms, frequency, bits, n_channels = 200, 44100, 16, 1
    sample_width = bits // 8
    max_amplitude = 2**(bits - 1) - 1
    total_samples = int(frequency * (duration_ms / 1000.0))
    frames = bytearray()
    for _ in range(total_samples):
        sample = random.randint(-max_amplitude, max_amplitude)
        frames += struct.pack('<h', sample)
    try:
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(n_channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(frequency)
            wf.writeframes(frames)
    except Exception as e:
        print(f"Error creating fallback WAV file: {e}")

def cleanup_temp_files():
    if os.path.exists(FALLBACK_SOUND_FILE):
        try:
            os.remove(FALLBACK_SOUND_FILE)
            print("Cleaned up temporary sound file.")
        except Exception as e:
            print(f"Error cleaning up temporary file: {e}")

atexit.register(cleanup_temp_files)

# --- Business Logic (Thread-Safe) ---

class HorrorManager:
    def __init__(self, gui_queue):
        self.event_lock = threading.Lock()
        self.active_event = None
        self.gui_queue = gui_queue
        
        self.dont_move_data = {'failed': False, 'detection_active': False}
        self.mouse_pos = (0, 0)
        
        # State for the popup hell event
        self.popup_hell_active = False
        self.popup_count = 10
        self.popup_time_limit = 10
        
        self.kb_controller = keyboard.Controller()
        
        self.image_paths, self.sound_paths, self.entity_image_paths = [], [], []
        self.load_assets()
        
        # NUDGE state
        self.is_active = False
        
        print("NUDGE is running. Please use the control panel to start.")

    def arm_nudges(self):
        self.is_active = True
        print("NUDGE: It's time.")

    def load_assets(self):
        # ... (asset loading logic remains the same)
        if os.path.isdir(IMAGE_FOLDER):
            self.image_paths.extend([os.path.join(IMAGE_FOLDER, f) for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))])
        if self.image_paths: print(f"Loaded {len(self.image_paths)} images.")
        else: print(f"Warning: '{IMAGE_FOLDER}' not found or empty. Using procedural jumpscare.")

        if os.path.isdir(SOUND_FOLDER):
            self.sound_paths.extend([os.path.join(SOUND_FOLDER, f) for f in os.listdir(SOUND_FOLDER) if f.lower().endswith('.wav')])
        if self.sound_paths: print(f"Loaded {len(self.sound_paths)} sounds.")
        else:
            print(f"Warning: '{SOUND_FOLDER}' not found or empty. Using generated sound.")
            create_fallback_scream_wav(FALLBACK_SOUND_FILE)
            self.sound_paths.append(FALLBACK_SOUND_FILE)
        
        if os.path.isdir(ENTITY_FOLDER):
            self.entity_image_paths.extend([os.path.join(ENTITY_FOLDER, f) for f in os.listdir(ENTITY_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))])
        if self.entity_image_paths: print(f"Loaded {len(self.entity_image_paths)} entity images.")
        else: print(f"Warning: '{ENTITY_FOLDER}' not found or empty. Using procedural entity.")

    def update_mouse_pos(self, x, y):
        self.mouse_pos = (x, y)

    def on_mouse_input(self):
        """Called by mouse move/click listeners."""
        if not self.is_active:
            return
            
        if self.active_event == "dont_move" and self.dont_move_data.get('detection_active'):
            self.dont_move_data['failed'] = True
        elif self.active_event is None:
            # Check for general random events (excluding typing possession priority)
            self.check_for_random_horror(check_typing_possession=True)

    def on_press(self, key):
        """Called by keyboard listener. Can suppress keys by returning False."""
        if not self.is_active:
            return True
            
        possession_triggered = False

        if self.active_event == "dont_move" and self.dont_move_data.get('detection_active'):
            self.dont_move_data['failed'] = True
            # Allow key press, but register the failure
        
        # --- TYPING POSSESSION CHANGE ---
        # Removed the 'elif self.active_event == 'typing_possession':' block.
        # The event is no longer an active interceptor.
        
        elif self.active_event is None:
            # Priority check for typing possession on key press
            if random.randint(1, TYPING_POSSESSION_ON_KEYPRESS_CHANCE) == 1:
                if self.event_lock.acquire(blocking=False):
                    try:
                        self.active_event = "typing_possession"
                        # --- TYPING POSSESSION CHANGE ---
                        # Only put the event on the queue. No duration, no immediate typing.
                        self.gui_queue.put({'event': 'typing_possession'})
                        possession_triggered = True  # Mark that possession triggered specifically
                        # We no longer type or suppress the key here.
                    except Exception as e:
                        print(f"Error triggering typing possession on keypress: {e}")
                        self.event_lock.release()  # Release lock on error
            
            # If possession wasn't triggered by priority check, do the general check
            if not possession_triggered:
                self.check_for_random_horror(check_typing_possession=True)  # Also check typing possession here, but lower chance

        return True  # Allow key press to go through

    def check_for_random_horror(self, check_typing_possession=False):
        # Use acquire with blocking=False to immediately return if lock is held.
        # This is called by mouse input OR by key press if priority possession didn't trigger.
        if self.event_lock.acquire(blocking=False):
            popup_hell_triggered = False
            try:
                # Conditionally check for typing possession based on caller
                if check_typing_possession and random.randint(1, TYPING_POSSESSION_GENERAL_CHANCE) == 1:
                    self.active_event = "typing_possession"
                    # --- TYPING POSSESSION CHANGE ---
                    # No duration needed
                    self.gui_queue.put({'event': 'typing_possession'})
                elif random.randint(1, BROWSER_HIJACK_CHANCE) == 1:
                    self.active_event = "browser_hijack"
                    self.gui_queue.put({'event': 'browser_hijack'})
                elif random.randint(1, TIME_WARP_CHANCE) == 1:
                    self.active_event = "time_warp"
                    self.gui_queue.put({'event': 'time_warp'})
                elif random.randint(1, SCREEN_FLIP_CHANCE) == 1:
                    self.active_event = "screen_flip"
                    self.gui_queue.put({'event': 'screen_flip'})
                elif random.randint(1, WINDOW_SWAP_CHANCE) == 1:
                    self.active_event = "window_swap"
                    self.gui_queue.put({'event': 'window_swap'})
                elif random.randint(1, RPS_CHANCE) == 1 and not self.popup_hell_active:
                    self.active_event = "rps_game"
                    self.gui_queue.put({'event': 'rps_game'})
                elif random.randint(1, POPUP_HELL_CHANCE) == 1 and not self.popup_hell_active:
                    self.popup_hell_active = True
                    popup_hell_triggered = True
                    self.gui_queue.put({'event': 'popup_hell'})
                elif random.randint(1, DONT_MOVE_CHANCE) == 1:
                    self.active_event = "dont_move"
                    self.dont_move_data = {'failed': False, 'detection_active': False}
                    self.gui_queue.put({'event': 'dont_move'})
                elif random.randint(1, JUMPSCARE_CHANCE) == 1:
                    self.active_event = "jumpscare"
                    self.gui_queue.put({'event': 'jumpscare', 'duration': 0.3})
                elif random.randint(1, ENTITY_CHANCE) == 1:
                    self.active_event = "entity"
                    target_pos = self.mouse_pos
                    self.gui_queue.put({'event': 'entity', 'target': target_pos})
                else:
                    self.event_lock.release()  # No event triggered, release lock
            except Exception as e:
                print(f"Error checking for horror: {e}")
                self.event_lock.release()  # Ensure lock is released on error
            
            if popup_hell_triggered:
                self.event_lock.release()

    def finish_event(self):
        self.active_event = None
        if self.event_lock.locked():
            self.event_lock.release()

    def finish_popup_hell(self):
        self.popup_hell_active = False

# --- GUI Manager (Runs in Main Thread) ---

class HorrorGUI:
    def __init__(self, manager, mouse_listener, keyboard_listener):
        self.manager = manager
        self.mouse_listener = mouse_listener
        self.keyboard_listener = keyboard_listener
        
        self.root = tk.Tk()
        # self.root.withdraw() # Don't withdraw yet
        
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.active_popups = []
        self.popup_timer_id = None
        
        self.countdown_seconds = 0
        self.tray_icon = None
        
        self.setup_control_panel()

    def setup_control_panel(self):
        self.root.title("NUDGE Control Panel")
        
        frame = tk.Frame(self.root, padx=20, pady=15)
        frame.pack()

        title_label = tk.Label(frame, text="NUDGE", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))

        info_label = tk.Label(frame, text="Stop yourself after...", wraplength=250)
        info_label.pack(pady=(0, 15))

        entry_frame = tk.Frame(frame)
        entry_frame.pack(pady=5)
        
        # --- NEW: Hours Entry ---
        h_frame = tk.Frame(entry_frame)
        h_frame.pack(side='left', padx=5)
        h_label = tk.Label(h_frame, text="Hours:")
        h_label.pack(side='top')
        self.entry_h = tk.Entry(h_frame, width=5)
        self.entry_h.pack(side='bottom')
        self.entry_h.insert(0, "0")

        # --- MODIFIED: Minutes Entry ---
        m_frame = tk.Frame(entry_frame)
        m_frame.pack(side='left', padx=5)
        m_label = tk.Label(m_frame, text="Minutes:")
        m_label.pack(side='top')
        self.entry_m = tk.Entry(m_frame, width=5)
        self.entry_m.pack(side='bottom')
        self.entry_m.insert(0, "15") # Default value

        # --- NEW: Seconds Entry ---
        s_frame = tk.Frame(entry_frame)
        s_frame.pack(side='left', padx=5)
        s_label = tk.Label(s_frame, text="Seconds:")
        s_label.pack(side='top')
        self.entry_s = tk.Entry(s_frame, width=5)
        self.entry_s.pack(side='bottom')
        self.entry_s.insert(0, "0")

        self.button = tk.Button(frame, text="Begin...", command=self.start_countdown, font=("Arial", 10, "bold"), bg="#C80000", fg="white", relief="raised")
        self.button.pack(pady=10, fill='x')
        
        self.error_label = tk.Label(frame, text="", fg="red")
        self.error_label.pack(pady=(5, 0))

        # Center the window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.screen_width // 2) - (width // 2)
        y = (self.screen_height // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        self.root.resizable(False, False)

    def start_countdown(self):
        # --- MODIFIED: Get all three values ---
        hours_str = self.entry_h.get()
        minutes_str = self.entry_m.get()
        seconds_str = self.entry_s.get()
        
        try:
            # Default to 0 if field is empty
            hours = float(hours_str) if hours_str else 0
            minutes = float(minutes_str) if minutes_str else 0
            seconds = float(seconds_str) if seconds_str else 0
            
            total_seconds = (hours * 3600) + (minutes * 60) + seconds
            
            if total_seconds <= 0:
                raise ValueError("Time must be positive")
            
            self.error_label.config(text="")
            self.countdown_seconds = int(total_seconds)
            
            # Hide control panel
            self.root.withdraw()
            
            # Start the listeners
            print("Listeners started. Countdown beginning.")
            self.mouse_listener.start()
            self.keyboard_listener.start()
            
            # Start tray icon thread
            threading.Thread(target=self.start_tray_icon, daemon=True).start()
            
            # Start countdown loop
            self.root.after(1000, self.update_countdown)
            
        except ValueError:
            self.error_label.config(text="Please enter valid, positive numbers.")

    def create_tray_icon_image(self):
        # Create a simple 64x64 icon
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0)) # Transparent
        dc = ImageDraw.Draw(image)
        # Draw a red circle with 'FF'
        dc.ellipse((2, 2, 62, 62), fill=RED, outline=WHITE, width=4)
        dc.text((16, 18), "FF", fill=WHITE, font_size=32)
        return image

    def start_tray_icon(self):
        def on_quit_clicked(icon, item):
            print("Quit clicked from tray icon.")
            icon.stop()
            self.root.quit() # This will stop mainloop

        image = self.create_tray_icon_image()
        menu = pystray.Menu(pystray.MenuItem('Quit NUDGE', on_quit_clicked))
        
        self.tray_icon = pystray.Icon("NUDGE", image, "NUDGE", menu)
        
        # --- MODIFIED: Update countdown format ---
        hours = self.countdown_seconds // 3600
        mins = (self.countdown_seconds % 3600) // 60
        secs = self.countdown_seconds % 60
        self.tray_icon.title = f"NUDGE starts in {hours}:{mins:02d}:{secs:02d}"
        
        self.tray_icon.run() # This is a blocking call, hence the thread

    def update_countdown(self):
        if self.countdown_seconds > 0:
            self.countdown_seconds -= 1
            
            # --- MODIFIED: Update countdown format ---
            hours = self.countdown_seconds // 3600
            mins = (self.countdown_seconds % 3600) // 60
            secs = self.countdown_seconds % 60
            new_title = f"NUDGE starts in {hours}:{mins:02d}:{secs:02d}"
            
            if self.tray_icon:
                self.tray_icon.title = new_title
                
            self.root.after(1000, self.update_countdown)
        else:
            # Countdown finished!
            if self.tray_icon:
                self.tray_icon.title = "NUDGE is active!"
                # We stop the icon thread, but it will be replaced by a new one
                # A bit clunky, but pystray title update from main thread is iffy
                # Better: just update title and leave it.
            
            # --- MODIFIED: Update title on finish ---
            if self.tray_icon:
                self.tray_icon.title = "NUDGE is Active!"
            
            self.manager.arm_nudges() # Arm the horror

    def run(self):
        self.process_queue()
        self.root.mainloop()

    def process_queue(self):
        try:
            task = self.manager.gui_queue.get_nowait()
            event = task.get('event')
            if event == 'jumpscare':
                self.create_jumpscare(task['duration'])
            elif event == 'dont_move':
                self.create_dont_move()
            elif event == 'entity':
                self.create_entity(task.get('target', (self.screen_width / 2, self.screen_height / 2)))
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
                # --- TYPING POSSESSION CHANGE ---
                # No longer takes duration
                self.create_typing_possession()
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.process_queue)  # Check queue every 50ms

    def create_overlay(self):
        overlay = tk.Toplevel(self.root)
        overlay.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        overlay.overrideredirect(True)
        overlay.wm_attributes("-topmost", True)
        overlay.wm_attributes("-transparentcolor", CHROMA_KEY)
        overlay.config(bg=CHROMA_KEY)
        canvas = tk.Canvas(overlay, width=self.screen_width, height=self.screen_height, bg=CHROMA_KEY, highlightthickness=0)
        canvas.pack()
        return overlay, canvas

    def play_jumpscare_sound(self):
        if self.manager.sound_paths:
            sound_file = random.choice(self.manager.sound_paths)
            winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)

    def show_jumpscare_content(self, canvas):
        canvas.delete("all")
        if not self.manager.image_paths:
            canvas.config(bg=BLACK)
            w, h = self.screen_width, self.screen_height
            eye_r = w // 8; canvas.create_oval(w//4 - eye_r, h//3 - eye_r, w//4 + eye_r, h//3 + eye_r, fill=RED, outline=""); canvas.create_oval(w*3//4 - eye_r, h//3 - eye_r, w*3//4 + eye_r, h//3 + eye_r, fill=RED, outline=""); mouth = [w//4, h*2//3, w*3//4, h*2//3, w//2, h*5//6]; canvas.create_polygon(mouth, fill=RED, outline="")
        else:
            try:
                img_path = random.choice(self.manager.image_paths)
                img = Image.open(img_path)
                
                # --- object-fit: cover logic ---
                img_width, img_height = img.size
                screen_aspect = self.screen_width / self.screen_height
                img_aspect = img_width / img_height

                if img_aspect > screen_aspect:
                    # Image is wider than screen, scale by height
                    new_height = self.screen_height
                    new_width = int(new_height * img_aspect)
                else:
                    # Image is taller or same aspect, scale by width
                    new_width = self.screen_width
                    new_height = int(new_width / img_aspect)
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                # --- end of logic ---

                self.photo_image = ImageTk.PhotoImage(img)  # Must hold reference
                canvas.config(bg=BLACK)
                canvas.create_image(self.screen_width//2, self.screen_height//2, image=self.photo_image)
            except Exception as e:
                print(f"Error loading image {img_path}: {e}")
                self.manager.image_paths.clear()
                self.show_jumpscare_content(canvas)

    def create_jumpscare(self, duration, is_consequence=False):
        overlay, canvas = self.create_overlay()
        self.play_jumpscare_sound()
        self.show_jumpscare_content(canvas)
        
        if not is_consequence:
            self.root.after(int(duration * 1000), lambda: [overlay.destroy(), winsound.PlaySound(None, winsound.SND_PURGE), self.manager.finish_event()])
        else:
            self.root.after(int(duration * 1000), lambda: [overlay.destroy(), winsound.PlaySound(None, winsound.SND_PURGE)])

    def create_dont_move(self):
        overlay, canvas = self.create_overlay()
        canvas.create_text(self.screen_width/2, self.screen_height/2, text=DONT_MOVE_TEXT, fill=RED, font=("Arial", 60, "bold"))
        def start_detection():
            self.manager.dont_move_data['detection_active'] = True
            check_failure(time.time() + 3)  # 3 seconds to stay still
        def check_failure(end_time):
            if not overlay.winfo_exists():
                self.manager.finish_event()
                return
            if self.manager.dont_move_data['failed']:
                self.play_jumpscare_sound()
                self.show_jumpscare_content(canvas)
                self.root.after(500, lambda: [overlay.destroy(), winsound.PlaySound(None, winsound.SND_PURGE), self.manager.finish_event()])
            elif time.time() >= end_time:
                overlay.destroy()
                self.manager.finish_event()
            else:
                self.root.after(1000//FPS, lambda: check_failure(end_time))
        self.root.after(1000, start_detection)  # 1s grace period

    def create_entity(self, target_pos):
        overlay, canvas = self.create_overlay()
        hwnd = overlay.winfo_id()
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style | win32con.WS_EX_TRANSPARENT)
        width, height = 100, 200
        speed = random.randint(8, 12)
        edge = random.randint(0, 3)
        if edge == 0: start_x, start_y = random.randint(0, self.screen_width - width), -height
        elif edge == 1: start_x, start_y = self.screen_width, random.randint(0, self.screen_height - height)
        elif edge == 2: start_x, start_y = random.randint(0, self.screen_width - width), self.screen_height
        else: start_x, start_y = -width, random.randint(0, self.screen_height - height)
        target_x, target_y = target_pos
        angle = math.atan2(target_y - (start_y + height / 2), target_x - (start_x + width / 2))
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        body = None
        if self.manager.entity_image_paths:
            try:
                img_path = random.choice(self.manager.entity_image_paths)
                img = Image.open(img_path).resize((width, height), Image.Resampling.LANCZOS)
                self.entity_photo_image = ImageTk.PhotoImage(img)
                body = canvas.create_image(start_x, start_y, image=self.entity_photo_image, anchor='nw')
            except Exception: self.manager.entity_image_paths.clear()
        if body is None: body = canvas.create_rectangle(start_x, start_y, start_x + width, start_y + height, fill="#141414", outline="")
        def animate():
            if not overlay.winfo_exists(): self.manager.finish_event(); return
            canvas.move(body, vx, vy)
            coords = canvas.coords(body)
            if not coords: overlay.destroy(); self.manager.finish_event(); return
            ex, ey = coords[0], coords[1]
            ex2, ey2 = ex + width, ey + height
            center_x, center_y = ex + width / 2, ey + height / 2
            mx, my = overlay.winfo_pointerxy()
            if ex < mx < ex2 and ey < my < ey2:
                self.play_jumpscare_sound()
                self.show_jumpscare_content(canvas)
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style & ~win32con.WS_EX_TRANSPARENT)
                self.root.after(500, lambda: [overlay.destroy(), winsound.PlaySound(None, winsound.SND_PURGE), self.manager.finish_event()])
                return
            if center_x < -width or center_x > self.screen_width + width or center_y < -height or center_y > self.screen_height + height:
                overlay.destroy(); self.manager.finish_event(); return
            self.root.after(1000//FPS, animate)
        animate()

    def create_popup_hell(self):
        print("EVENT: Popup Hell triggered!")
        time_left = self.manager.popup_time_limit
        
        def on_popup_close(popup):
            if popup in self.active_popups:
                self.active_popups.remove(popup)
            popup.destroy()
            if not self.active_popups:  # Player won
                if self.popup_timer_id:
                    self.root.after_cancel(self.popup_timer_id)
                    self.popup_timer_id = None
                print("Popup Hell: SUCCESS")
                self.manager.popup_count = 10  # Reset
                self.manager.popup_time_limit = 10  # Reset
                self.manager.finish_popup_hell()

        for _ in range(self.manager.popup_count):
            popup = tk.Toplevel(self.root)
            popup.geometry(f"200x100+{random.randint(0, self.screen_width-200)}+{random.randint(0, self.screen_height-100)}")
            popup.wm_attributes("-topmost", True)
            popup.title("Close Me!")
            popup.protocol("WM_DELETE_WINDOW", lambda p=popup: on_popup_close(p))
            
            timer_label = tk.Label(popup, text=f"{time_left}", font=("Arial", 16), fg='red')
            timer_label.pack(pady=5)
            
            close_button = tk.Button(popup, text="Close", command=lambda p=popup: on_popup_close(p))
            close_button.pack(pady=5)
            
            self.active_popups.append(popup)

        def update_timer(current_time):
            if not self.active_popups: return  # Game already won
            
            for popup in self.active_popups:
                if popup.winfo_exists():
                    for widget in popup.winfo_children():
                        if isinstance(widget, tk.Label):
                            widget.config(text=f"{current_time}", fg='red')

            if current_time <= 0:  # Timer ran out, player lost
                print("Popup Hell: FAILED")
                self.manager.popup_count += 5  # Increase difficulty
                self.manager.popup_time_limit += 5  # Increase difficulty
                
                while self.active_popups:
                    popup = self.active_popups.pop()
                    if popup.winfo_exists():
                        popup.destroy()
                self.popup_timer_id = None

                # Trigger jumpscare, then immediately start the next wave.
                self.create_jumpscare(0.5, is_consequence=True)
                self.root.after(500, self.create_popup_hell)  # 500ms matches jumpscare
                return

            self.popup_timer_id = self.root.after(1000, lambda: update_timer(current_time - 1))

        update_timer(time_left)

    def create_rps_game(self):
        print("EVENT: Rock Paper Scissors triggered!")
        popup = tk.Toplevel(self.root)
        popup.geometry(f"300x150+{random.randint(0, self.screen_width - 300)}+{random.randint(0, self.screen_height - 150)}")
        popup.wm_attributes("-topmost", True)
        popup.title("Choose Wisely...")
        popup.resizable(False, False)

        correct_choice = random.choice(['rock', 'paper', 'scissors'])
        
        info_label = tk.Label(popup, text="Make the right choice, or else.", font=("Arial", 12))
        info_label.pack(pady=5)
        
        timer_label = tk.Label(popup, text="", font=("Arial", 10))
        timer_label.pack(pady=5)

        button_frame = tk.Frame(popup)
        button_frame.pack(pady=10)

        rps_timer_id = [None]  # Use a list to make it mutable in nested functions

        def handle_choice(user_choice):
            # Stop the timer
            if rps_timer_id[0]:
                self.root.after_cancel(rps_timer_id[0])
                rps_timer_id[0] = None

            # Disable buttons
            for child in button_frame.winfo_children():
                child.config(state='disabled')

            if user_choice == correct_choice:
                popup.destroy()
                self.manager.finish_event()
            else:  # Wrong choice or timeout
                info_label.config(text="YOU LOST", fg=RED, font=("Arial", 24, "bold"))
                
                def consequence():
                    popup.destroy()
                    self.manager.popup_count = 20
                    self.manager.popup_time_limit = 20
                    if not self.manager.popup_hell_active:
                        self.manager.popup_hell_active = True
                        self.manager.gui_queue.put({'event': 'popup_hell'})
                    self.manager.finish_event()

                self.root.after(1000, consequence)

        def update_timer(time_left):
            if not popup.winfo_exists():
                if rps_timer_id[0]: self.root.after_cancel(rps_timer_id[0])
                self.manager.finish_event()
                return

            if time_left < 0:
                handle_choice(None)  # Timeout is a loss
                return
            
            timer_label.config(text=f"Time remaining: {time_left}", fg='red')
            rps_timer_id[0] = self.root.after(1000, lambda: update_timer(time_left - 1))

        rock_btn = tk.Button(button_frame, text="Rock", command=lambda: handle_choice('rock'))
        rock_btn.pack(side='left', padx=5)
        paper_btn = tk.Button(button_frame, text="Paper", command=lambda: handle_choice('paper'))
        paper_btn.pack(side='left', padx=5)
        scissors_btn = tk.Button(button_frame, text="Scissors", command=lambda: handle_choice('scissors'))
        scissors_btn.pack(side='left', padx=5)
        
        update_timer(10)

    def create_window_swap(self):
        print("EVENT: Window Swap triggered!")
        
        windows = []
        def winEnumHandler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) != '' and "NUDGE" not in win32gui.GetWindowText(hwnd):
                windows.append(hwnd)
        
        win32gui.EnumWindows(winEnumHandler, None)
        
        foreground_hwnd = win32gui.GetForegroundWindow()
        other_windows = [hwnd for hwnd in windows if hwnd != foreground_hwnd]
        
        if other_windows:
            overlay, canvas = self.create_overlay()
            canvas.config(bg=BLACK)
            
            def do_the_swap():
                new_window_hwnd = random.choice(other_windows)
                try:
                    # Attempt to bring the window to the foreground
                    win32gui.ShowWindow(new_window_hwnd, win32con.SW_RESTORE)  # Restore if minimized
                    win32gui.SetForegroundWindow(new_window_hwnd)
                except pywintypes.error as e:
                    # Specific error code 1400: Invalid window handle (often happens with background processes)
                    # Specific error code 5: Access denied (might happen with elevated processes)
                    if e.winerror != 1400 and e.winerror != 5:
                        print(f"Could not swap window (HWND: {new_window_hwnd}): {e}")
                    # Silently ignore common errors for non-interactive windows
                except Exception as e:
                    print(f"Could not swap window (HWND: {new_window_hwnd}): Unexpected error {e}")

                overlay.destroy()
                self.manager.finish_event()

            self.root.after(100, do_the_swap)  # Flicker for 100ms
        else:
            print("Window Swap: No other eligible windows found.")
            self.manager.finish_event()

    def create_screen_flip(self):
        print("EVENT: Screen Flip triggered!")
        try:
            device = win32api.EnumDisplayDevices(None, 0)
            dm = win32api.EnumDisplaySettings(device.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
            
            original_orientation = dm.DisplayOrientation
            
            # Flip the screen (180 degrees)
            new_orientation = win32con.DMDO_180 if original_orientation == win32con.DMDO_DEFAULT else win32con.DMDO_DEFAULT
            
            dm.DisplayOrientation = new_orientation
            dm.Fields = dm.Fields | win32con.DM_DISPLAYORIENTATION
            win32api.ChangeDisplaySettingsEx(device.DeviceName, dm)

            def revert_screen():
                try:
                    # Need to fetch current settings again in case something else changed it
                    current_dm = win32api.EnumDisplaySettings(device.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
                    if current_dm.DisplayOrientation != original_orientation:
                        current_dm.DisplayOrientation = original_orientation
                        current_dm.Fields = current_dm.Fields | win32con.DM_DISPLAYORIENTATION
                        win32api.ChangeDisplaySettingsEx(device.DeviceName, current_dm)
                except Exception as e:
                    print(f"Could not revert screen flip: {e}")
                finally:
                    self.manager.finish_event()
            
            self.root.after(5000, revert_screen)  # Revert after 5 seconds
        except Exception as e:
            print(f"Could not perform screen flip: {e}")
            self.manager.finish_event()

    def create_time_warp(self):
        print("EVENT: Time Warp triggered!")

        # 1. Attempt to change system time (requires admin)
        original_time_tuple = win32api.GetLocalTime()
        try:
            # Construct a time tuple for SetSystemTime
            # (Year, Month, DayOfWeek, Day, Hour, Minute, Second, Milliseconds)
            new_time_tuple = (
                original_time_tuple[0] + random.randint(-5, 5),  # Year
                random.randint(1, 12),                       # Month
                original_time_tuple[2],                      # Day of week (keep original)
                random.randint(1, 28),                       # Day (simplification, avoids month length issues)
                random.randint(0, 23),                       # Hour
                random.randint(0, 59),                       # Minute
                random.randint(0, 59),                       # Second
                original_time_tuple[7]                       # Milliseconds
            )
            win32api.SetSystemTime(*new_time_tuple)
            print("Time Warp: System time altered.")
            
            # Schedule the time revert using the original tuple
            def revert_time():
                try:
                    win32api.SetSystemTime(*original_time_tuple)
                    print("Time Warp: System time restored.")
                except pywintypes.error as e:
                    # Error code 1314: A required privilege is not held by the client
                    if e.winerror == 1314:
                        print("Time Warp: Could not restore time - Lacking administrator privileges.")
                    else:
                        print(f"Time Warp: Could not restore time - {e}")

            self.root.after(8000, revert_time)  # Revert after 8 seconds

        except pywintypes.error as e:
            if e.winerror == 1314:
                print("Time Warp: Could not change system time - Lacking administrator privileges.")
            else:
                print(f"Time Warp: Could not change system time - {e}")
        except Exception as e:
            print(f"Time Warp: Unexpected error changing system time - {e}")


        # 2. Create fake calendar notification (Independent of time change success)
        notification = tk.Toplevel(self.root)
        # Position bottom right
        noti_width = 300
        noti_height = 100
        noti_x = self.screen_width - noti_width - 10
        noti_y = self.screen_height - noti_height - 40  # Adjust for taskbar roughly
        notification.geometry(f"{noti_width}x{noti_height}+{noti_x}+{noti_y}")
        notification.overrideredirect(True)
        notification.wm_attributes("-topmost", True)
        notification.config(bg="#333333", borderwidth=1, relief="solid")

        messages = [
            "Meeting with The Entity", "Your soul is due.", "Appointment: Final Breath",
            "Reminder: They are watching.", "Event: The Reaping", "Task: Embrace the void."
        ]
        
        title_label = tk.Label(notification, text="Upcoming Event", bg="#333333", fg=WHITE, font=("Arial", 10, "bold"), anchor="w")
        title_label.pack(fill="x", padx=5, pady=(5, 0))

        msg_label = tk.Label(notification, text=random.choice(messages), bg="#333333", fg=WHITE, font=("Arial", 12), anchor="w", justify="left")
        msg_label.pack(fill="x", padx=5, pady=(0, 5))

        def close_notification():
            if notification.winfo_exists():
                notification.destroy()
            self.manager.finish_event()  # Finish the overall Time Warp event

        # Close notification after 7 seconds. Time revert is scheduled separately.
        self.root.after(7000, close_notification) 
        
    def create_browser_hijack(self):
        print("EVENT: Browser Hijack triggered!")
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",   # Rickroll
            "https://www.nyan.cat/",
            "https://pointerpointer.com/",
            "https://www.lomando.com/main.html",
            "https://en.wikipedia.org/wiki/Special:Random"
        ]
        try:
            webbrowser.open_new_tab(random.choice(urls))
        except Exception as e:
            print(f"Browser Hijack: Could not open browser tab - {e}")
        finally:
            self.manager.finish_event()

    # --- TYPING POSSESSION CHANGE ---
    # This function is now completely different.
    def create_typing_possession(self):
        print("EVENT: Typing Possession triggered!")
        
        try:
            # 1. Open notepad
            subprocess.Popen(['notepad.exe'])
        except Exception as e:
            print(f"Typing Possession: Could not open notepad - {e}")
            self.manager.finish_event()
            return

        def type_message():
            try:
                # 2. Define messages
                messages = [
                    "I see you.",
                    "You aren't safe.",
                    "Look behind you.",
                    "Why did you let this happen?",
                    "It's all your fault.",
                    "He is coming.",
                    "You can't escape me.",
                    "RUN."
                ]
                message = random.choice(messages)
                
                # 3. Type the message using the manager's controller
                self.manager.kb_controller.type(message)
            except Exception as e:
                print(f"Typing Possession: Error typing message - {e}")
            finally:
                # 4. Finish the event
                self.manager.finish_event()

        # 5. Wait 1 second for notepad to open before typing
        self.root.after(1000, type_message)


def main():
    if sys.platform != "win32":
        print("This script currently only supports Windows for creating overlays.")
        sys.exit(1)
    
    gui_queue = queue.Queue()
    manager = HorrorManager(gui_queue)

    def on_move_wrapper(x, y): 
        manager.update_mouse_pos(x, y)
        manager.on_mouse_input()
    def on_click_wrapper(x, y, button, pressed): 
        manager.update_mouse_pos(x, y)
        manager.on_mouse_input()
    
    # Create listeners but don't start them
    mouse_listener = mouse.Listener(
        on_move=on_move_wrapper,
        on_click=on_click_wrapper)
    
    keyboard_listener = keyboard.Listener(
        on_press=manager.on_press, 
        suppress=False) 
    
    # Pass listeners to GUI
    gui = HorrorGUI(manager, mouse_listener, keyboard_listener)
    
    try:
        gui.run()  # This blocks and runs the Tkinter main loop
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Ensure listeners are stopped cleanly
        if mouse_listener.is_alive():
            mouse_listener.stop()
        if keyboard_listener.is_alive():
            keyboard_listener.stop()
            
        # Stop tray icon if it's alive
        if gui.tray_icon:
            gui.tray_icon.stop()
        
        # Explicitly wait for listener threads to finish
        mouse_listener.join()
        keyboard_listener.join()
        print("NUDGE has exited.")

if __name__ == "__main__":
    main()

