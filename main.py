import tkinter as tk
from PIL import Image, ImageTk
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

# --- Dependencies for Global Input and Overlay ---
# You must install these libraries: pip install pynput pywin32 Pillow
try:
    from pynput import mouse, keyboard
    import win32api
    import win32con
    import win32gui
    import pywintypes
except ImportError:
    print("Required libraries not found. Please run:")
    print("pip install pynput pywin32 Pillow")
    sys.exit(1)

# --- Configuration ---
FPS = 60
BLACK = "#000000"
RED = "#C80000"
WHITE = "#FFFFFF"
CHROMA_KEY = "#FF0080" # A magenta-like color

# --- Customization ---
DONT_MOVE_TEXT = "DON'T YOU DARE MOVE"
IMAGE_FOLDER = "images"
SOUND_FOLDER = "sounds"
ENTITY_FOLDER = "entities"
FALLBACK_SOUND_FILE = "temp_scream.wav"

# --- Horror Event Probabilities ---
JUMPSCARE_CHANCE = 200
DONT_MOVE_CHANCE = 500
ENTITY_CHANCE = 600
POPUP_HELL_CHANCE = 700
RPS_CHANCE = 800
WINDOW_SWAP_CHANCE = 900
SCREEN_FLIP_CHANCE = 1000
TIME_WARP_CHANCE = 1100
BROWSER_HIJACK_CHANCE = 1200 # New event probability

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
        
        self.image_paths, self.sound_paths, self.entity_image_paths = [], [], []
        self.load_assets()
        print("FocusFrame is running in the background. Good luck.")

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

    def on_input(self):
        if self.active_event == "dont_move" and self.dont_move_data.get('detection_active'):
            self.dont_move_data['failed'] = True
        elif self.active_event is None:
            self.check_for_random_horror()

    def check_for_random_horror(self):
        # Use acquire with blocking=False to immediately return if lock is held.
        if self.event_lock.acquire(blocking=False):
            popup_hell_triggered = False
            try:
                if random.randint(1, BROWSER_HIJACK_CHANCE) == 1:
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
                    # This event is special: it's non-blocking to other events.
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
                    self.event_lock.release() # No event triggered, release lock
            except Exception as e:
                print(f"Error checking for horror: {e}")
                self.event_lock.release() # Ensure lock is released on error
            
            if popup_hell_triggered:
                # Immediately release the lock so other events can trigger while popups are active.
                self.event_lock.release()

    def finish_event(self):
        self.active_event = None
        if self.event_lock.locked():
            self.event_lock.release()

    def finish_popup_hell(self):
        self.popup_hell_active = False

# --- GUI Manager (Runs in Main Thread) ---

class HorrorGUI:
    def __init__(self, manager):
        self.manager = manager
        self.root = tk.Tk()
        self.root.withdraw() # Hide the main window
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.active_popups = []
        self.popup_timer_id = None

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
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.process_queue) # Check queue every 50ms

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

                self.photo_image = ImageTk.PhotoImage(img) # Must hold reference
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
            check_failure(time.time() + 3) # 3 seconds to stay still
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
        self.root.after(1000, start_detection) # 1s grace period

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
            if not self.active_popups: # Player won
                if self.popup_timer_id:
                    self.root.after_cancel(self.popup_timer_id)
                    self.popup_timer_id = None
                print("Popup Hell: SUCCESS")
                self.manager.popup_count = 10 # Reset
                self.manager.popup_time_limit = 10 # Reset
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
            if not self.active_popups: return # Game already won
            
            for popup in self.active_popups:
                if popup.winfo_exists():
                    for widget in popup.winfo_children():
                        if isinstance(widget, tk.Label):
                            widget.config(text=f"Time: {current_time}")

            if current_time <= 0: # Timer ran out, player lost
                print("Popup Hell: FAILED")
                self.manager.popup_count += 5 # Increase difficulty
                self.manager.popup_time_limit += 5 # Increase difficulty
                
                while self.active_popups:
                    popup = self.active_popups.pop()
                    if popup.winfo_exists():
                        popup.destroy()
                self.popup_timer_id = None

                # Trigger jumpscare, then immediately start the next wave.
                self.create_jumpscare(0.5, is_consequence=True)
                self.root.after(500, self.create_popup_hell) # 500ms matches jumpscare
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

        rps_timer_id = [None] # Use a list to make it mutable in nested functions

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
            else: # Wrong choice or timeout
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
                handle_choice(None) # Timeout is a loss
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
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) != '' and "FocusFrame" not in win32gui.GetWindowText(hwnd):
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
                    win32gui.SetForegroundWindow(new_window_hwnd)
                except Exception as e:
                    print(f"Could not swap window: {e}")
                
                overlay.destroy()
                self.manager.finish_event()

            self.root.after(100, do_the_swap) # Flicker for 100ms
        else:
            print("Window Swap: No other eligible windows found.")
            self.manager.finish_event()

    def create_screen_flip(self):
        print("EVENT: Screen Flip triggered!")
        try:
            device = win32api.EnumDisplayDevices(None, 0)
            dm = win32api.EnumDisplaySettings(device.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
            
            original_orientation = dm.DisplayOrientation
            
            # Flip the screen
            if dm.DisplayOrientation == win32con.DMDO_DEFAULT:
                dm.DisplayOrientation = win32con.DMDO_180
            else:
                dm.DisplayOrientation = win32con.DMDO_DEFAULT
            
            dm.Fields = dm.Fields | win32con.DM_DISPLAYORIENTATION
            win32api.ChangeDisplaySettingsEx(device.DeviceName, dm)

            def revert_screen():
                try:
                    dm.DisplayOrientation = original_orientation
                    dm.Fields = dm.Fields | win32con.DM_DISPLAYORIENTATION
                    win32api.ChangeDisplaySettingsEx(device.DeviceName, dm)
                except Exception as e:
                    print(f"Could not revert screen flip: {e}")
                finally:
                    self.manager.finish_event()
            
            self.root.after(5000, revert_screen) # Revert after 5 seconds
        except Exception as e:
            print(f"Could not perform screen flip: {e}")
            self.manager.finish_event()

    def create_time_warp(self):
        print("EVENT: Time Warp triggered!")

        # 1. Attempt to change system time (requires admin)
        original_time = win32api.GetLocalTime()
        try:
            new_time_tuple = (
                original_time[0] + random.randint(-5, 5), # Year
                random.randint(1, 12),                    # Month
                original_time[2],                         # Day of week
                random.randint(1, 28),                    # Day
                random.randint(0, 23),                    # Hour
                random.randint(0, 59),                    # Minute
                random.randint(0, 59),                    # Second
                original_time[7]                          # Milliseconds
            )
            win32api.SetSystemTime(*new_time_tuple)
            print("Time Warp: System time altered.")
            
            def revert_time():
                try:
                    win32api.SetSystemTime(*original_time)
                    print("Time Warp: System time restored.")
                except pywintypes.error as e:
                    print(f"Time Warp: Could not restore time - {e}")

            self.root.after(8000, revert_time) # Revert after 8 seconds

        except pywintypes.error:
            print("Time Warp: Could not change system time. Run as administrator for this effect.")

        # 2. Create fake calendar notification
        notification = tk.Toplevel(self.root)
        notification.geometry(f"300x100+{self.screen_width - 310}+{self.screen_height - 140}")
        notification.overrideredirect(True)
        notification.wm_attributes("-topmost", True)
        notification.config(bg="#333333", borderwidth=1, relief="solid")

        messages = [
            "Meeting with The Entity", "Your soul is due.", "Appointment: Final Breath",
            "Reminder: They are watching.", "Event: The Reaping", "Task: Embrace the void."
        ]
        
        title_label = tk.Label(notification, text="Upcoming Event", bg="#333333", fg=WHITE, font=("Arial", 10, "bold"))
        title_label.pack(anchor="w", padx=5, pady=(5, 0))

        msg_label = tk.Label(notification, text=random.choice(messages), bg="#333333", fg=WHITE, font=("Arial", 12))
        msg_label.pack(anchor="w", padx=5, pady=(0, 5))

        def close_notification():
            notification.destroy()
            self.manager.finish_event()

        self.root.after(7000, close_notification) # Notification lasts 7 seconds
        
    def create_browser_hijack(self):
        print("EVENT: Browser Hijack triggered!")
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rickroll
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


def main():
    if sys.platform != "win32":
        print("This script currently only supports Windows for creating overlays.")
        sys.exit(1)
    
    gui_queue = queue.Queue()
    manager = HorrorManager(gui_queue)
    gui = HorrorGUI(manager)

    def on_move_wrapper(x, y): 
        manager.update_mouse_pos(x, y)
        manager.on_input()
    def on_click_wrapper(x, y, button, pressed): 
        manager.update_mouse_pos(x, y)
        manager.on_input()
    def on_press_wrapper(key): 
        manager.on_input()

    mouse_listener = mouse.Listener(
        on_move=on_move_wrapper,
        on_click=on_click_wrapper)
    keyboard_listener = keyboard.Listener(
        on_press=on_press_wrapper)
    
    mouse_listener.start()
    keyboard_listener.start()
    
    print("Listeners started. Press Ctrl+C in this terminal to exit.")
    
    try:
        gui.run() # This blocks and runs the Tkinter main loop
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        mouse_listener.stop()
        keyboard_listener.stop()

if __name__ == "__main__":
    main()

