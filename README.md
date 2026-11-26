# 🤖 Agent Riya 9.0 – AI Voice Assistant

**Agent Riya 9.0** is a Python-based AI Voice Assistant with a modern graphical user interface (GUI) built using Tkinter. It supports voice interaction and text-based task management, helping users perform everyday activities through simple voice commands.

## ✨ Features

- 🎤 **Voice Recognition** – Recognizes user commands using SpeechRecognition.
- 🔊 **Text-to-Speech** – Responds using Windows speech synthesis.
- 💬 **Interactive GUI** – User-friendly interface built with Tkinter.
- 🌐 **Website Navigation** – Opens Google, YouTube, and Gmail using voice commands.
- 📚 **Wikipedia Search** – Provides short explanations and definitions.
- 📝 **To-Do List Management** – Add, complete, remove, and clear tasks.
- 💾 **Task Persistence** – Saves tasks automatically in a JSON file.
- 🧵 **Multithreading** – Handles listening, speech processing, and UI updates.
- 👋 **Exit Commands** – Close the assistant using voice commands.

## 🛠️ Technologies Used

- Python
- Tkinter
- SpeechRecognition
- PyAudio
- pyttsx3
- Wikipedia
- JSON
- Threading
- Windows PowerShell Speech Synthesis

## 📁 Project Structure

```text
Agent-Riya-9.0/
│
├── AgentRiya9.0.py
├── tasks.json          # Created automatically when tasks are saved
├── README.md
└── requirements.txt    # Optional dependency list
```

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/sangameshsajjan/Agent-Riya-9.0-AI-Voice-Assistant.git
```

### 2. Open the Project Folder

```bash
cd Agent-Riya-9.0-AI-Voice-Assistant
```

### 3. Install Required Libraries

```bash
pip install SpeechRecognition pyttsx3 wikipedia pillow
```

Install PyAudio:

```bash
pip install pipwin
pipwin install pyaudio
```

### 4. Run the Application

```bash
python AgentRiya9.0.py
```

## 🎙️ Voice Commands

| Command | Action |
|---|---|
| `Open YouTube` | Opens YouTube |
| `Open Google` | Opens Google |
| `Open Gmail` | Opens Gmail |
| `Open Calculator` | Opens Windows Calculator |
| `Add task Buy groceries` | Adds a task |
| `Complete task 1` | Marks task 1 as completed |
| `Remove task 1` | Removes task 1 |
| `Clear all tasks` | Clears all tasks |
| `What is Python` | Gets a Wikipedia explanation |
| `Exit` / `Quit` / `Bye` | Closes the assistant |

## 💻 Requirements

- Python 3.x
- Windows operating system (for the built-in PowerShell speech synthesis)
- Working microphone
- Internet connection for Google Speech Recognition and Wikipedia lookups

## 🚀 Future Enhancements

- Add AI-powered conversational responses.
- Integrate weather information.
- Add email and calendar automation.
- Support more voice commands.
- Improve the assistant's personalization and user experience.

## 👨‍💻 Author

**Sangamesh Sajjan**

GitHub: [@sangameshsajjan](https://github.com/sangameshsajjan)

## 📜 License

This project is open-source and available for learning and educational purposes. Add a specific license file if you want to formally define reuse and distribution permissions.

---

⭐ If you find this project interesting, consider giving the repository a star!
