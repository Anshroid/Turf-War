from util import OwnedBy

MAP_COLOURS = {
    OwnedBy.YELLOW: "#ffd600",
    OwnedBy.RED: "#ff5252",
    OwnedBy.UNOWNED: "#ffffff",
}

MAP_COLOURS_DARK = {
    OwnedBy.YELLOW: "#665500",
    OwnedBy.RED: "#8a0000",
    OwnedBy.UNOWNED: "#000000" # should never be used?
}

HIGHLIGHT_1_COLOUR = "#00ff40"
HIGHLIGHT_2_COLOUR = "#1500ff"

MAX_PAGE_SIZE = 25

CYCLE_INTERVAL_MINUTES = 15
GAME_DURATION_MINUTES = 120