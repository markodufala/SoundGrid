import wx
from pyo import Server, Mix, Compress, Fader
from camera_utils import CameraManager
from sound_synthesis import INSTRUMENT_NAMES, create_instrument

class SoundGrid(wx.Frame):
    def __init__(self, parent, title):
        super(SoundGrid, self).__init__(parent, title=title, size=(1200, 950))

        # ----- Overall Dark Frame Background -----
        self.SetBackgroundColour(wx.Colour(40, 40, 40))
        
        self.playing = False
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)

        # --- Basic parameters ---
        self.volume = 0.5
        self.hue_volume = 0.5
        self.hue_reverb = 0.5
        self.speed = 100

        # --- Hue detection / color settings ---
        self.color_sensitivity = 5
        self.target_hue = 50
        self.hue_detection_enabled = True

        # --- Filter options ---
        self.filter_enabled = False
        self.filter_frequency = 1000

        # --- Sample selection ---
        self.samples_list = [
            "bass_synth.wav",
            "bass_synth2.wav",
            "drums.wav",
            "guitar.wav",
            "hiphop.wav",
            "kick.wav",
            "reverse_keys.wav",
            "synth.wav",
        ]
        self.selected_sample = self.samples_list[0]

        # Initialize pyo server
        self.s = Server(duplex=0)
        self.s.boot()
        self.s.start()

        # Camera manager for hue detection
        self.camera_mgr = CameraManager(capture_index=0)

        # 2D array: each cell has [pyoObject, faderEnvelope] or None
        self.oscillators = [[None for _ in range(10)] for _ in range(10)]
        # Store which instrument index is playing in each cell
        self.current_instruments = [[-1 for _ in range(10)] for _ in range(10)]

        # Dictionary to hold “hold loop” instruments
        self.instrument_loops = {name: None for name in INSTRUMENT_NAMES}

        # Now each column stores a list [final_output, final_fader] or None
        self.column_mixers = [None for _ in range(10)]

        # A 10-note scale for the rows (for more harmonious pitches)
        # Example: A minor pentatonic spanning multiple octaves
        self.scale_frequencies = [
            220.0,    # A3
            261.63,   # C4
            293.66,   # D4
            329.63,   # E4
            392.0,    # G4
            440.0,    # A4
            523.25,   # C5
            587.33,   # D5
            659.25,   # E5
            784.0     # G5
        ]

        # Build the UI
        self.v_line_pos = 0
        self.prev_line_pos = -1
        self.build_ui()

        # Show the frame
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Show()

    def build_ui(self):
        """
        Sets up the UI so that:
        - The vertical column of “hold” instrument buttons is on the far LEFT.
        - The 10x10 grid is centered.
        - The timeline is below the grid.
        """
        # ------------------------------------------------------------------
        # 1) Build the vertical column of “hold” instrument buttons (left)
        # ------------------------------------------------------------------
        self.instrument_buttons_sizer = wx.BoxSizer(wx.VERTICAL)
        for i, instrument_name in enumerate(INSTRUMENT_NAMES):
            btn = wx.Button(self, label=instrument_name.capitalize(), size=(90, 40))
            inst_color = self.get_instrument_color(i)
            btn.SetBackgroundColour(inst_color)
            btn.SetForegroundColour(wx.Colour(255, 255, 255))

            # Bind press/release
            btn.Bind(wx.EVT_LEFT_DOWN, self.on_instrument_button_down)
            btn.Bind(wx.EVT_LEFT_UP, self.on_instrument_button_up)

            self.instrument_buttons_sizer.Add(btn, 0, wx.ALL, 5)

        # ------------------------------------------------------------------
        # 2) The 10x10 grid (centered)
        # ------------------------------------------------------------------
        self.grid_sizer = wx.GridSizer(10, 10, 0, 0)
        self.buttons = []
        for y in range(10):
            row = []
            for x in range(10):
                label = f"{chr(65 + y)}{x + 1}"  # e.g. A1, B2, ...
                btn = wx.ToggleButton(self, label=label, size=(60, 40))
                btn.SetBackgroundColour(wx.Colour(70, 70, 70))
                btn.SetForegroundColour(wx.Colour(255, 255, 255))
                btn.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle)
                self.grid_sizer.Add(btn, 0, wx.EXPAND)
                row.append(btn)
            self.buttons.append(row)

        # ------------------------------------------------------------------
        # 3) Timeline panel (below the grid)
        # ------------------------------------------------------------------
        self.timeline_panel = wx.Panel(self, size=(600, 100))
        self.timeline_panel.SetBackgroundColour(wx.Colour(50, 50, 50))
        self.timeline_panel.Bind(wx.EVT_PAINT, self.on_paint_timeline)

        # Stack the grid above the timeline in a vertical sizer
        grid_and_timeline_sizer = wx.BoxSizer(wx.VERTICAL)
        grid_and_timeline_sizer.Add(self.grid_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        grid_and_timeline_sizer.Add(self.timeline_panel, 0, wx.ALIGN_CENTER | wx.TOP, 10)

        # ------------------------------------------------------------------
        # 4) Combine (instrument buttons) and (grid+timeline) horizontally
        # ------------------------------------------------------------------
        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        # Left: instrument buttons
        top_hbox.Add(self.instrument_buttons_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        # Right: the vertical stack (grid above timeline)
        top_hbox.Add(grid_and_timeline_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        # ------------------------------------------------------------------
        # 5) Build other controls (play/clear, sliders, camera, hue, etc.)
        # ------------------------------------------------------------------
        play_button = wx.Button(self, label='Play/Pause')
        play_button.Bind(wx.EVT_BUTTON, self.on_play_pause)
        clear_button = wx.Button(self, label='Clear All')
        clear_button.Bind(wx.EVT_BUTTON, self.on_clear_all)

        button_box = wx.BoxSizer(wx.HORIZONTAL)
        button_box.Add(play_button, 0, wx.ALIGN_CENTER | wx.RIGHT, 10)
        button_box.Add(clear_button, 0, wx.ALIGN_CENTER | wx.RIGHT, 10)

        volume_slider = wx.Slider(self, value=5, minValue=0, maxValue=10, style=wx.SL_HORIZONTAL)
        volume_slider.Bind(wx.EVT_SLIDER, self.on_volume_change)
        speed_slider = wx.Slider(self, value=5, minValue=1, maxValue=10, style=wx.SL_HORIZONTAL)
        speed_slider.Bind(wx.EVT_SLIDER, self.on_speed_change)

        sample_choice_label = wx.StaticText(self, label="Samples:")
        sample_choice_label.SetForegroundColour(wx.Colour(255,255,255))
        sample_choice = wx.Choice(self, choices=self.samples_list)
        sample_choice.SetSelection(0)
        sample_choice.Bind(wx.EVT_CHOICE, self.on_sample_choice)

        filter_toggle = wx.ToggleButton(self, label="Enable Filter")
        filter_toggle.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_filter)
        self.filter_slider = wx.Slider(self, value=1000, minValue=100, maxValue=3000, style=wx.SL_HORIZONTAL)
        self.filter_slider.Bind(wx.EVT_SLIDER, self.on_filter_freq_change)

        vol_label = wx.StaticText(self, label="Volume")
        vol_label.SetForegroundColour(wx.Colour(255,255,255))
        speed_label = wx.StaticText(self, label="Speed")
        speed_label.SetForegroundColour(wx.Colour(255,255,255))
        filter_label = wx.StaticText(self, label="Filter Freq")
        filter_label.SetForegroundColour(wx.Colour(255,255,255))

        control_box = wx.BoxSizer(wx.HORIZONTAL)
        control_box.Add(vol_label, 0, wx.ALIGN_CENTER | wx.RIGHT, 5)
        control_box.Add(volume_slider, 0, wx.EXPAND | wx.RIGHT, 10)
        control_box.Add(speed_label, 0, wx.ALIGN_CENTER | wx.RIGHT, 5)
        control_box.Add(speed_slider, 0, wx.EXPAND | wx.RIGHT, 10)
        control_box.Add(sample_choice_label, 0, wx.ALIGN_CENTER | wx.RIGHT, 5)
        control_box.Add(sample_choice, 0, wx.EXPAND | wx.RIGHT, 10)
        control_box.Add(filter_toggle, 0, wx.ALIGN_CENTER | wx.RIGHT, 10)
        control_box.Add(filter_label, 0, wx.ALIGN_CENTER | wx.RIGHT, 5)
        control_box.Add(self.filter_slider, 0, wx.EXPAND | wx.RIGHT, 10)

        # Hue detection
        hue_slider = wx.Slider(self, value=self.target_hue, minValue=0, maxValue=179, style=wx.SL_HORIZONTAL)
        hue_slider.Bind(wx.EVT_SLIDER, self.on_hue_change)
        sensitivity_slider = wx.Slider(self, value=self.color_sensitivity, minValue=1, maxValue=10, style=wx.SL_HORIZONTAL)
        sensitivity_slider.Bind(wx.EVT_SLIDER, self.on_sensitivity_change)
        hue_volume_slider = wx.Slider(self, value=5, minValue=0, maxValue=10, style=wx.SL_HORIZONTAL)
        hue_volume_slider.Bind(wx.EVT_SLIDER, self.on_hue_volume_change)
        hue_reverb_slider = wx.Slider(self, value=5, minValue=0, maxValue=10, style=wx.SL_HORIZONTAL)
        hue_reverb_slider.Bind(wx.EVT_SLIDER, self.on_hue_reverb_change)
        hue_toggle_button = wx.ToggleButton(self, label="Enable Hue Detection")
        hue_toggle_button.SetValue(self.hue_detection_enabled)
        hue_toggle_button.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_hue_detection)

        hue_label = wx.StaticText(self, label="Hue")
        hue_label.SetForegroundColour(wx.Colour(255,255,255))
        sens_label = wx.StaticText(self, label="Sensitivity")
        sens_label.SetForegroundColour(wx.Colour(255,255,255))
        hue_vol_label = wx.StaticText(self, label="Hue Volume")
        hue_vol_label.SetForegroundColour(wx.Colour(255,255,255))
        hue_rev_label = wx.StaticText(self, label="Hue Reverb")
        hue_rev_label.SetForegroundColour(wx.Colour(255,255,255))

        color_control_box = wx.BoxSizer(wx.HORIZONTAL)
        color_control_box.Add(hue_label, 0, wx.ALIGN_CENTER | wx.RIGHT, 5)
        color_control_box.Add(hue_slider, 0, wx.EXPAND | wx.RIGHT, 10)
        color_control_box.Add(sens_label, 0, wx.ALIGN_CENTER | wx.RIGHT, 5)
        color_control_box.Add(sensitivity_slider, 0, wx.EXPAND | wx.RIGHT, 10)
        color_control_box.Add(hue_vol_label, 0, wx.ALIGN_CENTER | wx.RIGHT, 5)
        color_control_box.Add(hue_volume_slider, 0, wx.EXPAND | wx.RIGHT, 10)
        color_control_box.Add(hue_rev_label, 0, wx.ALIGN_CENTER | wx.RIGHT, 5)
        color_control_box.Add(hue_reverb_slider, 0, wx.EXPAND | wx.RIGHT, 10)
        color_control_box.Add(hue_toggle_button, 0, wx.ALIGN_CENTER | wx.RIGHT, 10)

        # Camera
        self.camera_panel = wx.Panel(self, size=(400, 225))
        self.camera_panel.SetBackgroundColour(wx.Colour(30,30,30))
        self.camera_bitmap = wx.StaticBitmap(self.camera_panel, bitmap=wx.Bitmap(400, 225))

        self.edge_panel = wx.Panel(self, size=(400, 225))
        self.edge_panel.SetBackgroundColour(wx.Colour(30,30,30))
        self.edge_bitmap = wx.StaticBitmap(self.edge_panel, bitmap=wx.Bitmap(400, 225))

        self.mask_panel = wx.Panel(self, size=(400, 225))
        self.mask_panel.SetBackgroundColour(wx.Colour(30,30,30))
        self.mask_bitmap = wx.StaticBitmap(self.mask_panel, bitmap=wx.Bitmap(400, 225))

        camera_box = wx.BoxSizer(wx.HORIZONTAL)
        camera_box.Add(self.camera_panel, 0, wx.ALIGN_CENTER | wx.RIGHT, 10)
        camera_box.Add(self.edge_panel, 0, wx.ALIGN_CENTER | wx.RIGHT, 10)
        camera_box.Add(self.mask_panel, 0, wx.ALIGN_CENTER)

        # ------------------------------------------------------------------
        # 6) Main vertical layout
        # ------------------------------------------------------------------
        main_vbox = wx.BoxSizer(wx.VERTICAL)
        main_vbox.Add(top_hbox, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        main_vbox.Add(button_box, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)
        main_vbox.Add(control_box, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)
        main_vbox.Add(camera_box, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)
        main_vbox.Add(color_control_box, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 10)

        self.SetSizer(main_vbox)

    # -------------------------
    # Instrument “Hold” Logic
    # -------------------------
    def on_instrument_button_down(self, event):
        button = event.GetEventObject()
        button.CaptureMouse()  # So we definitely get the LEFT_UP event
        instrument_label = button.GetLabel().lower()

        # If it's already playing, do nothing
        if self.instrument_loops[instrument_label] is not None:
            return

        inst = create_instrument(
            instrument=instrument_label,
            freq=220,  # or any frequency logic you prefer
            volume=self.volume,
            filter_enabled=self.filter_enabled,
            filter_frequency=self.filter_frequency,
            selected_sample=self.selected_sample
        )
        # Start the sound
        inst[0].out()
        self.instrument_loops[instrument_label] = inst

    def on_instrument_button_up(self, event):
        button = event.GetEventObject()
        if button.HasCapture():
            button.ReleaseMouse()
        instrument_label = button.GetLabel().lower()

        inst = self.instrument_loops.get(instrument_label)
        if inst is not None:
            inst[1].stop()
            inst[0].stop()
            self.instrument_loops[instrument_label] = None

    # ---------------------------------
    # Drawing / color routines
    # ---------------------------------
    def get_instrument_color(self, instrument_index):
        """
        Return a color for the instrument based on its index.
        """
        colors = [
            wx.Colour(0, 200, 0),    # Sine: green
            wx.Colour(0, 0, 200),    # Saw: blue
            wx.Colour(200, 200, 0),  # Square: yellow
            wx.Colour(200, 0, 0),    # Samples: red
            wx.Colour(128, 0, 128),  # MySynth: purple
            wx.Colour(255, 0, 255),  # FM: magenta/pink
            wx.Colour(255, 165, 0)   # Drumkit: orange
        ]
        return colors[instrument_index]

    def on_paint_timeline(self, event):
        dc = wx.PaintDC(self.timeline_panel)
        width, height = self.timeline_panel.GetSize()
        grid_width = len(self.buttons[0])  # should be 10
        gap = 2  # gap between columns

        cell_width = (width - (grid_width - 1)*gap) // grid_width

        for x in range(grid_width):
            x_pos = x * (cell_width + gap)
            if x == self.v_line_pos:
                color = wx.Colour(230, 220, 220)
            else:
                color = wx.Colour(105, 100, 100)

            dc.SetBrush(wx.Brush(color))
            dc.SetPen(wx.Pen(color))
            dc.DrawRectangle(x_pos, 0, cell_width, height)

            # Draw a dot for each enabled button in row y
            for y in range(10):
                instrument_index = self.current_instruments[y][x]
                if instrument_index != -1:
                    button_color = self.get_instrument_color(instrument_index)
                    dc.SetBrush(wx.Brush(button_color))
                    circle_x = x_pos + cell_width // 2
                    circle_y = int((y + 0.5) * (height / 10.0))
                    dc.DrawCircle(circle_x, circle_y, 5)

    # ---------------------------------
    # Grid button toggling
    # ---------------------------------
    def on_toggle(self, event):
        button = event.GetEventObject()
        pos = [
            (yy, row.index(button)) 
            for yy, row in enumerate(self.buttons) if button in row
        ][0]
        y, x = pos

        base_name = f"{chr(65 + y)}{x + 1}"

        current = self.current_instruments[y][x]
        if current == -1:
            next_instrument = 0
        else:
            next_instrument = (current + 1) % (len(INSTRUMENT_NAMES) + 1)

        if next_instrument == len(INSTRUMENT_NAMES):
            # Turn off
            button.SetLabel(base_name)
            button.SetBackgroundColour(wx.Colour(70,70,70))
            if self.oscillators[y][x]:
                self.oscillators[y][x][1].stop()
                self.oscillators[y][x][0].stop()
                self.oscillators[y][x] = None
            self.current_instruments[y][x] = -1
        else:
            # Update to the next instrument
            button.SetLabel(INSTRUMENT_NAMES[next_instrument].capitalize())
            color = self.get_instrument_color(next_instrument)
            button.SetBackgroundColour(color)

            if self.oscillators[y][x]:
                self.oscillators[y][x][1].stop()
                self.oscillators[y][x][0].stop()

            # Use a scale frequency for that row
            freq = self.scale_frequencies[y]
            inst = create_instrument(
                instrument=INSTRUMENT_NAMES[next_instrument],
                freq=freq,
                volume=self.volume,
                filter_enabled=self.filter_enabled,
                filter_frequency=self.filter_frequency,
                selected_sample=self.selected_sample
            )
            self.oscillators[y][x] = inst
            self.current_instruments[y][x] = next_instrument

    # ---------------------------------
    # Playback, clearing, etc.
    # ---------------------------------
    def on_play_pause(self, event):
        if not self.playing:
            self.playing = True
            self.timer.Start(self.speed)
        else:
            self.playing = False
            self.camera_mgr.stop_hue_oscillator()
            self.timer.Stop()
            # Stop all columns' final faders & outputs
            for col_index in range(10):
                if self.column_mixers[col_index]:
                    final_out, final_fader = self.column_mixers[col_index]
                    final_fader.stop()  # fade out
                    final_out.stop()    # stop audio
                    self.column_mixers[col_index] = None
            # Also stop any "hold loop" instruments
            for row in self.oscillators:
                for osc in row:
                    if osc:
                        osc[1].stop()
                        osc[0].stop()

    def on_clear_all(self, event):
        if self.playing:
            self.playing = False
            self.camera_mgr.stop_hue_oscillator()
            self.prev_line_pos = -1
            self.v_line_pos = 0
            self.timer.Stop()
            # Stop all column mixers
            for col_index in range(10):
                if self.column_mixers[col_index]:
                    final_out, final_fader = self.column_mixers[col_index]
                    final_fader.stop()
                    final_out.stop()
                    self.column_mixers[col_index] = None
            for row in self.oscillators:
                for osc in row:
                    if osc:
                        osc[1].stop()
                        osc[0].stop()

        for y in range(10):
            for x in range(10):
                self.buttons[y][x].SetValue(False)
                label = f"{chr(65 + y)}{x + 1}"
                self.buttons[y][x].SetLabel(label)
                self.buttons[y][x].SetBackgroundColour(wx.Colour(70,70,70))
                self.current_instruments[y][x] = -1
                if self.oscillators[y][x]:
                    self.oscillators[y][x][1].stop()
                    self.oscillators[y][x][0].stop()
                    self.oscillators[y][x] = None
        self.Refresh()

    def on_volume_change(self, event):
        self.volume = event.GetEventObject().GetValue() / 10.0
        for row in self.oscillators:
            for osc in row:
                if osc:
                    osc[1].setMul(self.volume)
        # Update any “hold” loops
        for name, inst in self.instrument_loops.items():
            if inst is not None:
                inst[1].setMul(self.volume)

    def on_speed_change(self, event):
        self.speed = 50 + (10 - event.GetEventObject().GetValue()) * 20
        if self.playing:
            self.timer.Start(self.speed)

    def on_sample_choice(self, event):
        idx = event.GetEventObject().GetSelection()
        self.selected_sample = self.samples_list[idx]

    def on_toggle_filter(self, event):
        self.filter_enabled = event.GetEventObject().GetValue()

    def on_filter_freq_change(self, event):
        self.filter_frequency = event.GetEventObject().GetValue()

    def on_hue_change(self, event):
        self.target_hue = event.GetEventObject().GetValue()

    def on_sensitivity_change(self, event):
        self.color_sensitivity = event.GetEventObject().GetValue()

    def on_hue_volume_change(self, event):
        self.hue_volume = event.GetEventObject().GetValue() / 10.0

    def on_hue_reverb_change(self, event):
        self.hue_reverb = event.GetEventObject().GetValue() / 10.0

    def on_toggle_hue_detection(self, event):
        self.hue_detection_enabled = event.GetEventObject().GetValue()

    def on_timer(self, event):
        if not self.playing:
            return

        self.prev_line_pos = self.v_line_pos
        self.v_line_pos = (self.v_line_pos + 1) % 10

        # Process camera frame for hue detection
        self.camera_mgr.process_frame(
            camera_bitmap=self.camera_bitmap,
            edge_bitmap=self.edge_bitmap,
            mask_bitmap=self.mask_bitmap,
            hue_detection_enabled=self.hue_detection_enabled,
            target_hue=self.target_hue,
            color_sensitivity=self.color_sensitivity,
            hue_volume=self.hue_volume,
            hue_reverb=self.hue_reverb
        )

        # -----------------------
        # STOP PREVIOUS COLUMN
        # -----------------------
        if self.prev_line_pos >= 0:
            if self.column_mixers[self.prev_line_pos] is not None:
                final_out, final_fader = self.column_mixers[self.prev_line_pos]
                final_fader.stop()  # triggers fade-out

            # Revert the button colors in that column
            for y in range(10):
                inst_index = self.current_instruments[y][self.prev_line_pos]
                if inst_index != -1:
                    self.buttons[y][self.prev_line_pos].SetBackgroundColour(
                        self.get_instrument_color(inst_index)
                    )
                else:
                    self.buttons[y][self.prev_line_pos].SetBackgroundColour(wx.Colour(70,70,70))

        # -----------------------
        # PLAY CURRENT COLUMN
        # -----------------------
        active_sources = []
        for y in range(10):
            inst_index = self.current_instruments[y][self.v_line_pos]
            if inst_index != -1:
                freq = self.scale_frequencies[y]
                inst = create_instrument(
                    instrument=INSTRUMENT_NAMES[inst_index],
                    freq=freq,
                    volume=self.volume,
                    filter_enabled=self.filter_enabled,
                    filter_frequency=self.filter_frequency,
                    selected_sample=self.selected_sample
                )
                active_sources.append(inst[0])
                # Highlight the current step in the grid (white)
                self.buttons[y][self.v_line_pos].SetBackgroundColour(wx.Colour(255, 255, 255))
            else:
                self.buttons[y][self.v_line_pos].SetBackgroundColour(wx.Colour(70,70,70))

        if active_sources:
            mixed = Mix(active_sources, voices=2)
            mixed.setMul(0.5 / len(active_sources))  # reduce volume buildup

            compressed = Compress(
                input=mixed,
                thresh=-6,   # -6 dB threshold
                ratio=20,    # high ratio => acts like limiter
                risetime=0.01,
                falltime=0.1
            )

            # Final fader for the combined column output
            final_fader = Fader(fadein=0.05, fadeout=0.2, mul=1.0).play()

            # Multiply the compressed signal by final_fader => smooth fade in/out
            final_out = compressed * final_fader
            final_out.out()

            # Store both so we can stop them gracefully next time
            self.column_mixers[self.v_line_pos] = [final_out, final_fader]
        else:
            self.column_mixers[self.v_line_pos] = None

        self.Refresh()

    def on_close(self, event):
        # Release camera, stop hue oscillator
        self.camera_mgr.release()
        self.camera_mgr.stop_hue_oscillator()
        self.Destroy()

if __name__ == '__main__':
    app = wx.App(False)
    SoundGrid(None, 'SoundGrid')
    app.MainLoop()