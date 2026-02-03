**Developer's Note: This is the active repository for the SHUGRPi project.**

# What is a SHUGRPi?
The **S**tormwrecker **H**andheld **U**ndersized **G**aming **R**aspberry **Pi** (or SHUGRPi for short) is a handheld gaming console that runs off of Pygame and runs Pygame games. It uses a Raspberry Pi 5 for computing.

## How does it work technically?
The custom launcher `main.py` runs alongside Openbox (a lightweight window manager) on boot-up via `startx`. From there, you can run your games. If the launcher fails or quits, it simply restarts after a second or two.

## How does it work non-technically?
The custom "OS" basically is a bunch of UI put together to navigate through your games and basic settings:
<img width="975" height="586" alt="image" src="https://github.com/user-attachments/assets/6c4aca03-2137-4482-9a99-fac753ae9539" />

Pretty simple stuff.

## Notes:
While the OS is designed on a Windows machine, there are certain functionalities that will **not** do anything if running on a non-Pi device. The variable `is_shugr_pi` detects if running on an `aarch64` machine (regardless of using Linux or not) and is used for when wanting to run certain commands (e.g. git commands, python commands). There are all sorts of features the SHUGRPi is capable of, such as detecting updates, setting the Pi's clock, configuring network connections, and powering off the system.

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
* Create a `game_config.json` file if you want to change how your game is run.
* Limit your player/user controls to what's actually available. I plan on having one thumbstick, one d-pad, two start/select buttons, one home button, and four action buttons.
* Scale your display to 800x450 if you want to preserve a 16:9 ratio. Otherwise, using 800x480 for fullscreen works too.
* Call `pygame.quit()` after your main loop. This is a no-brainer, but things will probably break without calling it.

Here is a template:
`{"name": Display Name", "thumbnail": "path/to/thumbnail.png", "run_type": ".py", "use_venv": 0, "python_version":"3.13"}`

`name` is what the SHUGRPi calls your game. `thumbnail` is the path to the image you want to have displayed in the UI. `run_type` is the extension of the main app (currently detects `.py` and `.bin`). `use_venv` should be set to `1` if your game has multiple dependencies other than pygame, but keep in mind that if you do, you will need to create a proper `requirements.txt` file for it to work. `python_version` is what version of Python you would like to have your game run in. If set to a version other than `3.13`, it will be installed automatically via `pyenv`. More flags may be added in the future.

# Development
This project is a **work in progress**, so you can expect new features and bugs as I go. Fortunately, the custom OS will pick up on updates as I upload them to this repo, and the OS will prompt you accordingly. Literally almost everything I'm doing for this project is a first for me, except for the Pygame coding, so if you have a suggestion or a fix, please let me know. I have not reached the hardware phase as of yet. Once I do, however, I will document what components I used and add `Section 2: Hardware` to the pdf tutorial.

Stay tuned...
