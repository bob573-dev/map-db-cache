class TouchCalibrationPostproc:
    """
    Corrects raw touchscreen coordinates for windowed (non-fullscreen) Desktop Mode use.
    """

    def __init__(self, screen_size, window, device='touch'):
        self._screen_w, self._screen_h = screen_size
        self._window = window
        self._device = device

    def process(self, events):
        window = self._window
        for etype, event in events:
            if event.device != self._device:
                continue
            screen_x = event.sx * self._screen_w
            screen_y_from_top = (1 - event.sy) * self._screen_h
            event.sx = (screen_x - window.left) / window.width
            event.sy = 1 - (screen_y_from_top - window.top) / window.height
        return events
