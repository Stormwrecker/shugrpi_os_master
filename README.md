**Developer's Note: This is the active repository for the SHUGRPi project.**

# What is a SHUGRPi?
The Stormwrecker Handheld Undersized Gaming Raspberry Pi is a handheld gaming console that runs off of Pygame and runs Pygame (and possibly other kinds of) games. It uses a Raspberry Pi 5 for computing.

## How does it work technically?
The custom launcher `main.py` runs alongside Openbox (a lightweight window manager) on boot-up via `startx`. If the launcher fails or quits, it simply restarts after a second or two.

## How does it work non-technically?
The custom "OS" basically is a bunch of UI put together to navigate through your games and basic settings:
<img width="975" height="586" alt="image" src="https://github.com/user-attachments/assets/6c4aca03-2137-4482-9a99-fac753ae9539" />

Pretty simple stuff.

## Notes:
While the OS is designed on a Windows machine, there are certain functionalities that will **not** do anything if running on a non-Pi device. The variable `is_shugr_pi` detects if running on an `aarch64` machine (regardless of using Linux or not) and is used for when wanting to run certain commands (e.g. git commands, python commands). There are all sorts of features the SHUGRPi is capable of, such as detecting updates, setting the Pi's clock, configuring network connections, and powering off the system.
