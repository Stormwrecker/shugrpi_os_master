# import necessary modules
import os
import pygame

def init_pygame_with_audio_fallback():
    """
    Safe for HDMI displays with no audio device:
    - Runs pygame.init() normally
    - Re-inits mixer separately with fallback drivers
    - Prevents SHUGRPi from crashing on missing ALSA/HDMI audio
    """

    # Hide startup banner
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    # Start with dummy so pygame.init() never hard-fails
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    # Full pygame init (display, font, joystick, etc.)
    pygame.init()

    # Shut down mixer that pygame.init() may have started with dummy
    # pygame.mixer.quit()

    # Preferred real drivers in order
    drivers = ["wasapi", "alsa", "dummy"]

    active_driver = None

    for driver in drivers:
        try:
            # Force SDL backend for this attempt
            os.environ["SDL_AUDIODRIVER"] = driver

            # Make sure previous failed init is cleared
            pygame.mixer.quit()

            # Re-init mixer only
            pygame.mixer.init(
                frequency=44100,
                size=-16,
                channels=2,
                buffer=512
            )

            active_driver = driver
            print(f"Audio initialized with: {pygame.mixer.get_driver()}")
            break

        except pygame.error as e:
            print(f"Failed audio driver: {driver} ({e})")

    # Absolute failsafe
    if active_driver is None:
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.mixer.quit()
        pygame.mixer.init()
        active_driver = "dummy"

    return active_driver


# Example usage
audio_driver = init_pygame_with_audio_fallback()

print("Final audio driver:", audio_driver)
print("Mixer settings:", pygame.mixer.get_init())

# initialize pygame
pygame.init()

# set window/display dimensions
screen_width = 500
screen_height = 500
display_width = 500
display_height = 500
half_screen_width = screen_width // 2
half_screen_height = screen_height // 2

# create window/display
screen = pygame.display.set_mode((screen_width, screen_height))
display = pygame.Surface((display_width, display_height)).convert()

# misc setup
pygame.display.set_caption("Template")
clock = pygame.time.Clock()

# constants
FPS = 60
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (255, 0, 255)

"""define objects/functions here..."""

# main loop
run = True
while run:
    # fill screen
    screen.fill(BLACK)
    display.fill(BLACK)

    """update/render stuff here..."""

    # handle events
    all_events = pygame.event.get()
    for event in all_events:
        if event.type == pygame.QUIT:
            run = False
            break
        if event.type == pygame.KEYDOWN:
            pygame.mixer.Sound("audio/shugrpi.wav").play()

    # render display
    screen.blit(pygame.transform.scale(display, screen.get_size()), (0, 0))
    pygame.display.flip()

    # tick clock
    clock.tick(FPS)

# quit pygame
pygame.quit()
