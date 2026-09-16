from kivy.clock import Clock


class TouchDedupFilter:
    """Filters Window touch events down to an allow-list of devices, and
    de-duplicates a physical tap that arrives twice: once as a real touch
    event from `devices` and once as the OS/compositor's single-point mouse
    synthesis of that same tap (`mouse_device`).

    Two complementary mechanisms handle this, per phase (down/move/up):
    - Block: the moment a real (non-`mouse_device`) event of a phase passes
      through, a same-phase `mouse_device` event is blocked outright for
      `delay` seconds -- it's a duplicate of the tap that just went through,
      arriving slightly late. This is what a single-shot phase (down happens
      once per tap, so does up) needs: there is no *later* same-phase real
      event left to cancel a mouse event that slips in after it.
    - Hold-and-cancel: absent that, a `mouse_device` event is held for
      `delay` seconds and dropped if a real event of that phase arrives in
      the meantime; otherwise it's dispatched after the delay (tagged
      'filtered' so re-dispatch isn't re-intercepted). This is what makes a
      genuine standalone mouse (no competing touch device at all) still
      work, and covers `mouse_device` events that arrive *before* their
      real counterpart.

    Multi-finger touches (any device other than `mouse_device`, e.g. a pinch
    gesture) are never delayed -- only `mouse_device` events are held or
    blocked, since only those can collide with a real touch of the same tap.
    """

    def __init__(self, window, devices, mouse_device='mouse', delay=0.05, on_drop=None):
        """`on_drop(event, phase)` is called for every event this filter
        drops (never dispatched to Window), `phase` being one of
        'down'/'move'/'up' -- e.g. to register a dropped 'down' touch into
        FocusBehavior.ignored_touch (see app.py), since it will never
        register itself there the normal way.
        """
        self._window = window
        self._devices = set()
        self._mouse_device = mouse_device
        self._on_drop = on_drop

        self._delayed_down = None
        self._trigger_down = Clock.create_trigger(self._dispatch_delayed_down, delay)
        self._delayed_move = None
        self._trigger_move = Clock.create_trigger(self._dispatch_delayed_move, delay)
        self._delayed_up = None
        self._trigger_up = Clock.create_trigger(self._dispatch_delayed_up, delay)

        self._block_down = False
        self._trigger_unblock_down = Clock.create_trigger(self._unblock_down, delay)
        self._block_move = False
        self._trigger_unblock_move = Clock.create_trigger(self._unblock_move, delay)
        self._block_up = False
        self._trigger_unblock_up = Clock.create_trigger(self._unblock_up, delay)

        self.set_devices(devices)

    def set_devices(self, devices):
        self._window.unbind(
            on_touch_down=self._filter_touch_down,
            on_touch_move=self._filter_touch_move,
            on_touch_up=self._filter_touch_up,
        )
        self._delayed_down = None
        self._trigger_down.cancel()
        self._delayed_move = None
        self._trigger_move.cancel()
        self._delayed_up = None
        self._trigger_up.cancel()

        self._block_down = False
        self._trigger_unblock_down.cancel()
        self._block_move = False
        self._trigger_unblock_move.cancel()
        self._block_up = False
        self._trigger_unblock_up.cancel()

        self._devices = set(devices)
        if self._devices:
            self._window.bind(
                on_touch_down=self._filter_touch_down,
                on_touch_move=self._filter_touch_move,
                on_touch_up=self._filter_touch_up,
            )

    def _drop(self, event, phase):
        if self._on_drop:
            self._on_drop(event, phase)

    def _filter_touch_down(self, _window, event):
        if event.device not in self._devices:
            self._drop(event, 'down')
            return True  # stop further event processing
        if event.device != self._mouse_device:
            if self._delayed_down is not None:
                self._drop(self._delayed_down, 'down')
                self._delayed_down = None
                self._trigger_down.cancel()
            self._block_down = True
            self._trigger_unblock_down()
            return False  # allow further event processing
        if 'filtered' in event.profile:
            return False  # allow further event processing (our own re-dispatch)
        if self._block_down:
            self._drop(event, 'down')
            return True  # a real touch-down just passed -- this is its late duplicate
        self._delayed_down = event
        self._trigger_down()
        return True  # held for now -- stop further event processing

    def _unblock_down(self, _dt):
        self._block_down = False

    def _dispatch_delayed_down(self, _dt):
        event = self._delayed_down
        self._delayed_down = None
        if event:
            event.profile.append('filtered')
            self._window.dispatch('on_touch_down', event)

    def _filter_touch_move(self, _window, event):
        if event.device not in self._devices:
            self._drop(event, 'move')
            return True  # stop further event processing
        if event.device != self._mouse_device:
            if self._delayed_move is not None:
                self._drop(self._delayed_move, 'move')
                self._delayed_move = None
                self._trigger_move.cancel()
            self._block_move = True
            self._trigger_unblock_move()
            return False  # allow further event processing
        if 'filtered' in event.profile:
            return False  # allow further event processing (our own re-dispatch)
        if self._block_move:
            self._drop(event, 'move')
            return True  # a real touch-move just passed -- this is its late duplicate
        self._delayed_move = event
        self._trigger_move()
        return True  # held for now -- stop further event processing

    def _unblock_move(self, _dt):
        self._block_move = False

    def _dispatch_delayed_move(self, _dt):
        event = self._delayed_move
        self._delayed_move = None
        if event:
            event.profile.append('filtered')
            self._window.dispatch('on_touch_move', event)

    def _filter_touch_up(self, _window, event):
        if event.device not in self._devices:
            self._drop(event, 'up')
            return True  # stop further event processing
        if event.device != self._mouse_device:
            if self._delayed_up is not None:
                self._drop(self._delayed_up, 'up')
                self._delayed_up = None
                self._trigger_up.cancel()
            self._block_up = True
            self._trigger_unblock_up()
            return False  # allow further event processing
        if 'filtered' in event.profile:
            return False  # allow further event processing (our own re-dispatch)
        if self._block_up:
            self._drop(event, 'up')
            return True  # a real touch-up just passed -- this is its late duplicate
        self._delayed_up = event
        self._trigger_up()
        return True  # held for now -- stop further event processing

    def _unblock_up(self, _dt):
        self._block_up = False

    def _dispatch_delayed_up(self, _dt):
        event = self._delayed_up
        self._delayed_up = None
        if event:
            event.profile.append('filtered')
            self._window.dispatch('on_touch_up', event)
