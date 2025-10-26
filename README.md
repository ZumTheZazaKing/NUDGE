# NUDGE (Nightmarish User-Disruption & Glitch Engine)

## 🛑 Project Goal

**NUDGE** is a utility program designed to help users log off and touch grass by using all sorts of means with the horror theme in mind. Originally made for the **[Delulu Hack 2025](https://delulu.hackerhouse.my/)**.

Set when your productive time is over and let it silently watch 👁️. Once your time is over, it's active and if it detects anything like mouse movement or keystrokes during the active period, you risk triggering a series of digital jump scares and system disturbances.

## ⚠️ WARNING: Use with Caution

This program is designed to create jumpscares and momentary system disruptions (like screen rotation and time changes).

- **DO NOT** run this on critical systems or machines where sudden changes in display settings or application focus could cause data loss or serious interruption.

- **DO NOT** use this on computers that you do not own or have explicit permission to modify.

- **YOU MAY** send this to a friend as a prank if you manage to build this into an executable file but be sure to know your limits.

- Run this script with administrator privileges to ensure the Screen Flip and Time Warp features can function, as they require system-level permissions.

## 🛠️ Installation and Setup

This project is written in Python and is **Windows-only** (for now).

#### 1. Prerequisites

You must have Python 3.x installed and accessible from your command line.

#### 2. Install Dependencies

Certain libraries are required. They are listed in the provided requirements.txt file. I recommend using a virtual environment.



#### 3. Setup Assets (Optional but Recommended)

For the best experience, create and populate these folders with custom media:

| Folder    | Purpose                | Format     | Fallback if empty            |
|-----------|------------------------|------------|------------------------------|
| images/   | Full-screen jumpscares | .jpg,.png  | Procedural red/black screen  |
| sounds/   | Jumpscare audio        | .wav       | Generated static/scream .wav |
| entities/ | Moving entity image    | .png, .jpg | Procedural dark rectangle    |

## ▶️ How to Run

1. Open your terminal or command prompt.

2. Navigate to the project directory.

3. Execute the main script:

```
python nudge.py
```

#### Usage Steps:

1. The NUDGE Control Panel will open.

2. Enter the Hours, Minutes, and Seconds you commit to being focused.

3. Click "Begin..." to start the countdown. NUDGE will hide to the system tray.

4. Once the countdown reaches zero, **NUDGE IS ACTIVE**. Any detected input (mouse move/click, keystroke) has a chance to trigger an event!

## 💥 Events Implemented

|         Event         |                                  Description                                  |                       Risk / Consequence                       |
|:---------------------:|:-----------------------------------------------------------------------------:|:--------------------------------------------------------------:|
| Jumpscare             | A quick, full-screen image flash and sound.                                   | Simple jumpscare.                                              |
| Don't Move            | Text appears demanding you stop all input.                                    | Moving or typing results in a Jumpscare.                       |
| Entity                | A dark entity flies toward the mouse cursor.                                  | Clicking/touching the entity results in a Jumpscare.           |
| Popup Hell            | A swarm of closeable windows appears with a timer.                            | Failure to close them all results in a harder Popup Hell wave. |
| Rock, Paper, Scissors | A time-limited, win-or-else game.                                             | Choosing incorrectly results in a harder Popup Hell wave.      |
| Window Swap           | Instantly switches focus to a random open window with a black screen flicker. | Disrupts current task flow.                                    |
| Screen Flip           | Flips the primary display 180 degrees.                                        | Automatically reverts after 5 seconds.                         |
| Time Warp             | Momentarily changes the system time and displays an ominous notification.     | System time automatically reverts after 8 seconds.             |
| Browser Hijack        | Opens a new tab in the default web browser with a random, distracting link.   | Distracting link exposure.                                     |
| Typing Possession     | Opens Notepad and begins typing a spooky, random message.                     | Causes unexpected text insertion.                              |

## 🤝 Contribution

NUDGE is an open-source project and welcomes community input! I'd love help with new event ideas, cross-platform compatibility, or API optimization.

1. **Fork** the repository.

2. Create your feature branch ```(git checkout -b feature/NewEvent)```.

3. Commit your changes ```(git commit -m 'Feat: Add New Event')```.

4. Push to the branch.

5. Open a **Pull Request**.

## 📜 License

This project is licensed under the MIT License.