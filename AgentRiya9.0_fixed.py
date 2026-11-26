# Agent Riya 9.0 - Fixed replies (voice + chat) and exit command
"""
AI Voice Assistant - Agent Riya 9.0

Dependencies:
    pip install SpeechRecognition pyttsx3 wikipedia pillow
    pip install pipwin
    pipwin install pyaudio

Run:
    python AgentRiya9.0.py
"""

import tkinter as tk
from tkinter import ttk
import threading
import queue
import speech_recognition as sr
import pyttsx3
import webbrowser
import wikipedia
import json
import os
import subprocess
import time
from urllib.parse import quote as urlquote

# --------------------- Configuration ---------------------
ASSISTANT_NAME = "Agent Riya 9.0"
WINDOW_TITLE = "AI Voice Assistant - Agent Riya 9.0"
INITIAL_GREETING = "Hi, How can i help you today?"
TASKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")
LISTEN_TIMEOUT = 6  # seconds for phrase_time_limit

# -------------------- Persistence --------------------

def load_tasks():
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return []
                return [
                    item for item in data
                    if isinstance(item, dict) and isinstance(item.get("text"), str)
                ]
        except Exception:
            return []
    return []


def save_tasks(tasks):
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Failed to save tasks:", e)

# -------------------- Utilities --------------------

def hex_to_rgb(hexstr):
    h = hexstr.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# -------------------- Voice Engine --------------------

class VoiceEngine:
    def __init__(self, on_result_callback):
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        try:
            self.microphone = sr.Microphone()
        except Exception as e:
            print("Microphone initialization failed:", e)
            raise

        self.on_result = on_result_callback
        self._running = False
        self.listen_thread = None
        self._is_speaking = threading.Event()
        self._speech_queue = queue.Queue()

        # One dedicated TTS thread; the engine is created AND used inside it
        threading.Thread(target=self._tts_loop, daemon=True).start()

    # ---------------- Speaking ----------------
    def _speak_blocking(self, text):
        # Windows built-in speech via PowerShell. It runs in its own process, so
        # there are no thread/COM problems, and it returns only when speech ends.
        try:
            env = dict(os.environ, RIYA_TEXT=text)
            script = ("Add-Type -AssemblyName System.Speech; "
                      "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                      "try { $s.SelectVoice('Microsoft Zira Desktop') } catch {}; "
                      "$s.Rate = 0; $s.Volume = 100; "
                      "$s.Speak($env:RIYA_TEXT)")
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-Command", script],
                           env=env, creationflags=0x08000000, timeout=120, check=True)
        except Exception as e:
            print("TTS error:", e)

    def _tts_loop(self):
        while True:
            text, on_done = self._speech_queue.get()
            self._speak_blocking(text)
            time.sleep(0.5)  # let lingering audio die out
            if self._speech_queue.empty():
                self._is_speaking.clear()
            if on_done:
                try:
                    on_done()
                except Exception as e:
                    print("on_done error:", e)

    def speak(self, text, on_done=None):
        self._is_speaking.set()  # mic ignores input immediately
        self._speech_queue.put((text, on_done))

    # ---------------- Listening ----------------
    def start_listening(self):
        if self._running:
            return
        self._running = True
        self.listen_thread = threading.Thread(target=self._background_listen, daemon=True)
        self.listen_thread.start()

    def stop_listening(self):
        self._running = False

    def _background_listen(self):
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception:
            pass

        while self._running:
            if self._is_speaking.is_set():
                time.sleep(0.1)
                continue
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=LISTEN_TIMEOUT)
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print("Listen error:", e)
                time.sleep(0.3)
                continue

            if self._is_speaking.is_set():
                continue  # discard anything captured while Riya was talking
            threading.Thread(target=self._recognize_audio, args=(audio,), daemon=True).start()

    def _recognize_audio(self, audio):
        if self._is_speaking.is_set():
            return
        try:
            text = self.recognizer.recognize_google(audio)
            self.on_result(text)
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print("Speech service error (check internet):", e)

# -------------------- Main Application --------------------

class AgentRiyaApp:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("1100x640")
        self.root.minsize(980, 540)

        # Theme colors
        self.bg_top = "#0b1220"
        self.bg_bottom = "#071021"
        self.panel = "#0f1724"
        self.accent = "#6dd3ff"
        self.fg = "#e6eef8"
        self.muted = "#9aa7b2"

        # load tasks
        self.tasks = load_tasks()

        # Thread-safe UI update queue (all widget changes run on the main thread)
        self._ui_queue = queue.Queue()

        # Build UI
        self._build_ui()
        self._pump_ui()

        # Voice engine
        try:
            self.voice = VoiceEngine(self.on_speech_recognized)
        except Exception:
            self.voice = None
            self._append_message(ASSISTANT_NAME, "Microphone not available. Voice features disabled.")

        # greet
        self._append_message(ASSISTANT_NAME, INITIAL_GREETING)
        if self.voice:
            self.voice.speak(INITIAL_GREETING)
            self.voice.start_listening()
            self._set_listening(True)

    # -------------------- UI --------------------
    def _create_gradient_bg(self):
        self.bg_canvas = tk.Canvas(self.root, highlightthickness=0, bd=0, bg=self.bg_bottom)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        def draw(event=None):
            self.bg_canvas.delete("grad")
            w = event.width if event else self.bg_canvas.winfo_width()
            h = event.height if event else self.bg_canvas.winfo_height()
            if w < 2 or h < 2:
                return
            r1, g1, b1 = hex_to_rgb(self.bg_top)
            r2, g2, b2 = hex_to_rgb(self.bg_bottom)
            band = 4
            steps = max(h // band, 1)
            for i in range(steps + 1):
                ratio = i / steps
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                y0 = i * band
                self.bg_canvas.create_rectangle(
                    0, y0, w, y0 + band,
                    outline="", fill=f"#{r:02x}{g:02x}{b:02x}", tags="grad"
                )

        # bind on the canvas itself so child widgets don't trigger redraws
        self.bg_canvas.bind("<Configure>", draw)

    def _build_ui(self):
        self._create_gradient_bg()

        main = tk.Frame(self.root, bg=self.panel)
        main.place(relx=0.03, rely=0.03, relwidth=0.94, relheight=0.94)

        # Title bar
        title_frame = tk.Frame(main, bg=self.panel)
        title_frame.place(relx=0.01, rely=0.01, relwidth=0.98, relheight=0.08)
        title_lbl = tk.Label(title_frame, text=WINDOW_TITLE, bg=self.panel, fg=self.accent,
                             font=("Segoe UI", 18, 'bold'))
        title_lbl.pack(anchor='w', padx=12, pady=6)

        # Listening indicator on title bar (pulsing dot)
        self.listen_canvas = tk.Canvas(title_frame, width=22, height=22, bg=self.panel, highlightthickness=0)
        self.listen_canvas.pack(anchor='e', padx=12)
        self._listening_dot = self.listen_canvas.create_oval(3, 3, 19, 19, fill=self.accent)
        self._listening_pulse = 0
        self._listening_active = False
        self._animate_listening()

        # Left: conversation
        left = tk.Frame(main, bg=self.panel)
        left.place(relx=0.01, rely=0.11, relwidth=0.66, relheight=0.86)

        conv_header = tk.Label(left, text="Agent Riya 9.0", bg=self.panel, fg=self.fg, font=("Segoe UI", 13, 'bold'))
        conv_header.pack(anchor='nw', padx=14, pady=(12, 6))

        conv_container = tk.Frame(left, bg=self.bg_bottom, bd=0)
        conv_container.pack(fill='both', expand=True, padx=12, pady=(4, 12))

        self.conv_canvas = tk.Canvas(conv_container, bg=self.bg_bottom, bd=0, highlightthickness=0)
        self.conv_scroll = ttk.Scrollbar(conv_container, orient='vertical', command=self.conv_canvas.yview)
        self.conv_frame = tk.Frame(self.conv_canvas, bg=self.bg_bottom)

        self.conv_frame.bind("<Configure>", lambda e: self.conv_canvas.configure(scrollregion=self.conv_canvas.bbox("all")))
        self.conv_canvas.create_window((0, 0), window=self.conv_frame, anchor='nw')
        self.conv_canvas.configure(yscrollcommand=self.conv_scroll.set)

        self.conv_canvas.pack(side='left', fill='both', expand=True)
        self.conv_scroll.pack(side='right', fill='y')

        # Right: To-do list
        right = tk.Frame(main, bg=self.panel)
        right.place(relx=0.69, rely=0.11, relwidth=0.30, relheight=0.86)

        t_header = tk.Label(right, text="To-Do Task Management", bg=self.panel, fg=self.fg, font=("Segoe UI", 13, 'bold'))
        t_header.pack(anchor='nw', padx=12, pady=(12, 6))

        todo_container = tk.Frame(right, bg=self.bg_bottom)
        todo_container.pack(fill='both', expand=True, padx=12, pady=(4, 12))

        self.task_listbox = tk.Listbox(todo_container, bg=self.bg_bottom, fg=self.fg, bd=0, highlightthickness=0,
                                       font=("Segoe UI", 11), activestyle='none')
        self.task_listbox.pack(fill='both', expand=True, side='left')
        self.task_scroll = ttk.Scrollbar(todo_container, orient='vertical', command=self.task_listbox.yview)
        self.task_listbox.configure(yscrollcommand=self.task_scroll.set)
        self.task_scroll.pack(side='right', fill='y')

        # Task entry and buttons (works even when microphone is unavailable)
        task_controls = tk.Frame(right, bg=self.panel)
        task_controls.pack(fill='x', padx=12, pady=(0, 12))

        self.task_entry = tk.Entry(
            task_controls, bg="#162338", fg=self.fg, insertbackground=self.fg,
            relief='flat', font=("Segoe UI", 10)
        )
        self.task_entry.pack(fill='x', pady=(0, 8), ipady=7)
        self.task_entry.insert(0, "Type a task and press Enter")
        self.task_entry.bind("<FocusIn>", self._clear_task_placeholder)
        self.task_entry.bind("<Return>", lambda event: self._add_task_from_entry())

        task_buttons = tk.Frame(task_controls, bg=self.panel)
        task_buttons.pack(fill='x')
        tk.Button(task_buttons, text="Add", command=self._add_task_from_entry,
                  bg=self.accent, fg=self.bg_bottom, relief='flat').pack(side='left', expand=True, fill='x', padx=(0, 4))
        tk.Button(task_buttons, text="Complete selected", command=self._complete_selected_task,
                  bg="#1f6f5c", fg="white", relief='flat').pack(side='left', expand=True, fill='x', padx=4)
        tk.Button(task_buttons, text="Remove selected", command=self._remove_selected_task,
                  bg="#8b3945", fg="white", relief='flat').pack(side='left', expand=True, fill='x', padx=(4, 0))

        tk.Button(task_controls, text="Clear all tasks", command=self._clear_tasks_from_button,
                  bg="#344256", fg=self.fg, relief='flat').pack(fill='x', pady=(7, 0))

        self._refresh_task_list_ui()

        footer = tk.Label(self.root, text="Try: 'add task buy milk', 'complete task 1', 'remove task 1' — or use the task buttons",
                          bg=self.bg_bottom, fg=self.muted, font=("Segoe UI", 9))
        footer.place(relx=0.03, rely=0.97, anchor='sw')

    # -------------------- Thread-safe UI plumbing --------------------
    def _pump_ui(self):
        try:
            while True:
                self._ui_queue.get_nowait()()
        except queue.Empty:
            pass
        except Exception as e:
            print("UI error:", e)
        try:
            self.root.after(50, self._pump_ui)
        except Exception:
            pass  # window already closed

    def _append_message(self, sender, message):
        self._ui_queue.put(lambda: self._append_message_ui(sender, message))

    def _refresh_task_list(self):
        self._ui_queue.put(self._refresh_task_list_ui)

    # -------------------- Conversation helpers (message bubbles) --------------------
    def _append_message_ui(self, sender, message):
        bubble = tk.Frame(self.conv_frame, bg=self.bg_bottom)
        if sender == 'You':
            b = tk.Label(bubble, text=message, bg=self.accent, fg=self.bg_bottom, justify='left', wraplength=420,
                         font=("Segoe UI", 10), padx=10, pady=8)
            b.pack(anchor='e')
            bubble.pack(fill='x', anchor='e', pady=6, padx=(60, 10))
        else:
            b = tk.Label(bubble, text=message, bg="#0e1b29", fg=self.fg, justify='left', wraplength=420,
                         font=("Segoe UI", 10), padx=10, pady=8)
            b.pack(anchor='w')
            s = tk.Label(bubble, text=sender, bg=self.bg_bottom, fg=self.muted, font=("Segoe UI", 8))
            s.pack(anchor='w', pady=(4, 0))
            bubble.pack(fill='x', anchor='w', pady=6, padx=(10, 60))

        self.conv_canvas.update_idletasks()
        self.conv_canvas.yview_moveto(1.0)

    # -------------------- Task management --------------------
    def _clear_task_placeholder(self, event=None):
        if self.task_entry.get() == "Type a task and press Enter":
            self.task_entry.delete(0, 'end')

    def _add_task_from_entry(self):
        task_text = self.task_entry.get().strip()
        if not task_text or task_text == "Type a task and press Enter":
            return
        if self.add_task(task_text):
            self.task_entry.delete(0, 'end')
            self._say(f"Added task: {task_text}")

    def _selected_task_index(self):
        selection = self.task_listbox.curselection()
        return selection[0] if selection else None

    def _complete_selected_task(self):
        index = self._selected_task_index()
        if index is None:
            self._say("Select a task first.")
            return
        ok, task = self.complete_task(str(index + 1))
        if ok:
            self._say(f"Marked as completed: {task['text']}")

    def _remove_selected_task(self):
        index = self._selected_task_index()
        if index is None:
            self._say("Select a task first.")
            return
        ok, task = self.remove_task(str(index + 1))
        if ok:
            self._say(f"Removed task: {task['text']}")

    def _clear_tasks_from_button(self):
        if not self.tasks:
            self._say("There are no tasks to clear.")
            return
        self.clear_all_tasks()
        self._say("All tasks cleared.")

    def _refresh_task_list_ui(self):
        self.task_listbox.delete(0, 'end')
        for i, t in enumerate(self.tasks, 1):
            text = t.get('text')
            if t.get('done'):
                display = f"{i}. ✓ {text}"
            else:
                display = f"{i}. {text}"
            self.task_listbox.insert('end', display)

    def add_task(self, text):
        text = text.strip()
        if not text:
            return False
        self.tasks.append({"text": text, "done": False})
        save_tasks(self.tasks)
        self._refresh_task_list()
        return True

    def remove_task(self, identifier):
        removed = None
        try:
            idx = int(identifier) - 1
            if 0 <= idx < len(self.tasks):
                removed = self.tasks.pop(idx)
        except Exception:
            for i, t in enumerate(self.tasks):
                if identifier.casefold() in t['text'].casefold():
                    removed = self.tasks.pop(i)
                    break
        if removed:
            save_tasks(self.tasks)
            self._refresh_task_list()
            return True, removed
        return False, None

    def complete_task(self, identifier):
        completed = None
        try:
            idx = int(identifier) - 1
            if 0 <= idx < len(self.tasks):
                self.tasks[idx]['done'] = True
                completed = self.tasks[idx]
        except Exception:
            for t in self.tasks:
                if identifier.casefold() in t['text'].casefold():
                    t['done'] = True
                    completed = t
                    break
        if completed:
            save_tasks(self.tasks)
            self._refresh_task_list()
            return True, completed
        return False, None

    def clear_all_tasks(self):
        self.tasks = []
        save_tasks(self.tasks)
        self._refresh_task_list()

    # -------------------- Listening indicator --------------------
    def _animate_listening(self):
        if self._listening_active:
            self._listening_pulse = (self._listening_pulse + 1) % 30
            scale = 1 + (self._listening_pulse / 90)
            x0, y0, x1, y1 = 3, 3, 19, 19
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            r = 8 * scale
            self.listen_canvas.coords(self._listening_dot, cx - r/2, cy - r/2, cx + r/2, cy + r/2)
            self.listen_canvas.itemconfig(self._listening_dot, fill=self.accent)
        else:
            self.listen_canvas.coords(self._listening_dot, 3, 3, 19, 19)
            self.listen_canvas.itemconfig(self._listening_dot, fill="#4b5870")
        self.root.after(80, self._animate_listening)

    def _set_listening(self, val: bool):
        self._listening_active = val

    # -------------------- Reply helper --------------------
    def _say(self, resp):
        """Show a reply in the chat and speak it."""
        self._append_message(ASSISTANT_NAME, resp)
        if self.voice:
            self.voice.speak(resp)

    # -------------------- Command processing --------------------
    def on_speech_recognized(self, text):
        user_text = text.strip()
        print("Recognized:", user_text)
        self._append_message('You', user_text)
        threading.Thread(target=self._process_command, args=(user_text,), daemon=True).start()

    def _process_command(self, text):
        t = text.lower().strip()

        # exit command (highest priority) - whole words only
        if {'exit', 'quit', 'bye'} & set(t.split()):
            resp = 'have a good day'
            self._append_message(ASSISTANT_NAME, resp)
            if self.voice:
                self.voice.speak(resp, on_done=lambda: self._ui_queue.put(self._safe_close))
            else:
                self._ui_queue.put(self._safe_close)
            return

        # important commands
        if t.startswith('open youtube') or t == 'youtube':
            self._reply_and_open('Opening YouTube.', 'https://www.youtube.com')
            return
        if t.startswith('open google') or t == 'google':
            self._reply_and_open('Opening Google.', 'https://www.google.com')
            return
        if t.startswith('open gmail') or t == 'gmail':
            self._reply_and_open('Opening Gmail.', 'https://mail.google.com')
            return
        if 'calculator' in t or 'open calc' in t:
            self._say('Opening calculator.')
            try:
                subprocess.Popen('calc.exe')
            except Exception as e:
                print('Failed to open calculator:', e)
            return

        # tasks
        if t.startswith('add task'):
            task_text = text[len('add task'):].strip()
            if not task_text:
                self._say("I didn't hear the task description. Say: add task followed by the task name.")
                return
            ok = self.add_task(task_text)
            self._say(f'Added task: {task_text}' if ok else "Couldn't add the task.")
            return

        if t.startswith('remove task'):
            identifier = text[len('remove task'):].strip()
            if not identifier:
                self._say('Please say the task number or the task text to remove.')
                return
            ok, removed = self.remove_task(identifier)
            self._say(f"Removed task: {removed['text']}" if ok else "Couldn't find that task to remove.")
            return

        if (t.startswith('task completed') or t.startswith('complete task')
                or t.startswith('completed task') or t.startswith('mark task')):
            parts = text.split(maxsplit=2)
            identifier = parts[2].strip() if len(parts) >= 3 else ''
            if not identifier:
                self._say('Please say the task number or text that is completed.')
                return
            ok, completed = self.complete_task(identifier)
            self._say(f"Marked as completed: {completed['text']}" if ok else "Couldn't find that task to mark completed.")
            return

        if t.startswith('clear all tasks') or t == 'clear tasks':
            self.clear_all_tasks()
            self._say('All tasks cleared.')
            return

        # info commands
        for prefix in ('what is', 'explain', 'define'):
            if t.startswith(prefix):
                query = text[len(prefix):].strip()
                if not query:
                    self._say('Please say what you want me to explain or define.')
                    return
                try:
                    summary = wikipedia.summary(query, sentences=2, auto_suggest=False, redirect=True)
                    self._say(summary)
                except Exception:
                    self._say(f"I couldn't fetch a concise explanation. Searching the web for {query}.")
                    webbrowser.open(f'https://www.google.com/search?q={urlquote(query)}')
                return

        # fallback
        self._say("Sorry, I didn't understand that.")
        try:
            webbrowser.open(f'https://www.google.com/search?q={urlquote(text)}')
        except Exception:
            pass

    def _reply_and_open(self, resp, url):
        self._say(resp)
        webbrowser.open(url)

    def _safe_close(self):
        try:
            if getattr(self, 'voice', None):
                self.voice.stop_listening()
        except Exception:
            pass
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

# -------------------- Run --------------------

def main():
    root = tk.Tk()
    app = AgentRiyaApp(root)
    root.protocol('WM_DELETE_WINDOW', app._safe_close)
    root.mainloop()

if __name__ == '__main__':
    main()