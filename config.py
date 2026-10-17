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

HIGHLIGHT_COLOUR = "#00ff40"

MAX_PAGE_SIZE = 25

CYCLE_INTERVAL_MINUTES = 15