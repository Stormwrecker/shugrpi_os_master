**Developer's Note: This is the active repository for the SHUGRPi project. Still in alpha phase...**
The README will get brought up-to-speed when first release is finished.

# What is a SHUGRPi?
The **S**tormwrecker **H**andheld **U**nleashed **G**aming **R**aspberry **Pi** (or SHUGRPi for short) is a custom handheld gaming console that runs a Pygame-based operating system (i.e. the code in this repo) which, in turn, can launch games, mainly ones built with Pygame. I have, however, broadened support for launching virtually any Linux ARM64 binaries, but it's running raw Python/Pygame that makes this console stand out from the mainline ones. I am currently prototyping on a Raspberry Pi 5 (4GB RAM with an 8GB microSD for storage), but the final plan is to build a custom motherboard based off of the Raspberry Compute Module 5 with custom housing and the works.

## How does it work technically?
This is described in more detail in the Official Guide in the `/docs` folder, but essentially, the OS I'm using is based off of Debian-12 Bookworm for Raspberry Pi. I tweaked the actual startup process to be utterly silent and launch directly into `main.py` running from an umbrella Openbox session. Inside of this Pygame-based "operating system", I have UI elements that individually store their own backend functions. Each backend function is a Python wrapper for Linux calls via subprocess, so yes: This code can be *partially* considered a true operating system, what with managing files, timezones, game installations, updates, etc.

## So how does it work *non-technically*?
This custom OS is basically just a bunch of UI slapped together to navigate/play your games and configure basic settings.


## Screenshots

### Main Menu
<img width="797" height="479" alt="image" src="https://github.com/user-attachments/assets/5773d2e6-a5dd-47cb-af3c-83c0fe65f2a1" />

### Launching a Game
<img width="800" height="479" alt="image" src="https://github.com/user-attachments/assets/7c79d875-103f-48dd-a5be-50af23db1703" />

### Installing a Game
<img width="800" height="479" alt="image" src="https://github.com/user-attachments/assets/54589540-6326-4feb-8213-3b048cc1a761" />

Pretty simple stuff...

## Compatibility
The OS source code is written on a Windows machine and can be run on such. However, all of the Linux calls will be disabled and running `.bin` files won't work either. To be fully able to use everything, follow the instructions mentioned earlier in the README and run this stuff on a Raspberry Pi 5. I do implement delta-time in the source code, so you can get away with a Pi 4 without sacrificing too much of your SHUGRPi experience, but your games will definitely get affected.

## Is RetroPie used for the SHUGRPi?
No. The SHUGRPi OS is independent from RetroPie and any other emulation OS, and although no emulation is involved, SHUGRPi OS is a comparable piece of software. If your goal is to play old retro games, you can either a) use RetroPie instead or b) make retro games in Pygame. 🙂

## How to Build
In the `/docs` folder, I have included a pdf that runs through how to build the SHUGRPi from source. I plan on having a pre-made disk image that you can use to flash the Pi with, but for now, the pdf will have to do. Explanations are a bit scarce in the instructions, so if you run into issues, please report them in the Issues page.

# "I want to add my games to the SHUGRPi!"
Before you do this, there are consideration to keep in mind. When porting your game:
* Call `pygame.event.set_grab(True)` somewhere after you call `pygame.init()`. It helps keep everything robust.
* Pre-initialize your sound before `pygame.init()`:
```
# Example

sound_working = True
# Use a try/except block
try:
    pygame.mixer.pre_init(frequency=48000, size=-16, channels=2, buffer=2048)
except Exception as e:
    sound_working = False
```
* Limit your player/user controls to what's actually available. I plan on having one thumbstick, one d-pad, two start/select buttons, one home button, and four action buttons.
* Scale your display to 800x450 if you want to preserve a 16:9 ratio. Otherwise, using 800x480 for fullscreen works too.
* Call `pygame.quit()` after your main loop. This is a no-brainer, but things will probably break without calling it.
* Create a `game_config.json` file if you want to change how your game is run. Otherwise, the OS will auto-create one with default values.

Here is a template `game_config.json`:
`{"name": Display Name", "thumbnail": "path/to/thumbnail.png", "run_type": ".py", "use_venv": 0, "python_version":"3.13"}`

`name` is what the SHUGRPi calls your game. `thumbnail` is the path to the image you want to have displayed in the UI. `run_type` is the extension of the main app (currently detects `.py` and `.bin`). `use_venv` should be set to `1` if your game has multiple dependencies other than pygame, but keep in mind that if you do, you will need to create a proper `requirements.txt` file for it to work. `python_version` is what version of Python you would like to have your game run in. If set to a version other than `3.13`, it will be installed automatically via `pyenv`. More flags may be added in the future.

# Development
This project is a **work in progress**, so you can expect new features and bugs as I go. Fortunately, the custom OS will pick up on updates as I upload them to this repo, and the OS will prompt you accordingly. Literally almost everything I'm doing for this project is a first for me, except for the Pygame coding, so if you have a suggestion or a fix, please let me know. I have not reached the hardware phase as of yet. Once I do, however, I will document what components I used and add `Section 2: Hardware` to the pdf tutorial.

Stay tuned...
