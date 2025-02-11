import cv2
import numpy as np
import wx
from pyo import Sine, Freeverb, Compress, Chorus

class CameraManager:
    """
    A helper class for reading from the camera and
    applying hue-based color detection.
    """
    def __init__(self, capture_index=0):
        self.capture = cv2.VideoCapture(capture_index)
        self.hue_oscillator = None
        self.hue_reverb_effect = None
        self.current_freq = 220  # Initial frequency for smoothing
        self.frame_counter = 0

    def release(self):
        """ Release the camera resource. """
        self.capture.release()

    def process_frame(
        self,
        camera_bitmap,
        edge_bitmap,
        mask_bitmap,
        hue_detection_enabled,
        target_hue,
        color_sensitivity,
        hue_volume,
        hue_reverb
    ):
        """
        Captures a frame from the camera, detects a color range around target_hue,
        updates or stops the hue oscillator, and updates the bitmaps.
        """
        if not hue_detection_enabled:
            self.stop_hue_oscillator()
            return

        ret, frame = self.capture.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        frame_resized = cv2.resize(frame, (400, 225))
        self.frame_counter = (self.frame_counter + 1) % 5

        hue_frame = frame_resized.copy()
        edge_frame = frame_resized.copy()

        # Convert to HSV for color detection
        hsv = cv2.cvtColor(hue_frame, cv2.COLOR_BGR2HSV)
        lower_bound = np.array([target_hue - color_sensitivity * 10, 100, 100])
        upper_bound = np.array([target_hue + color_sensitivity * 10, 255, 255])
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)

            # Outline the detected area
            hue_bgr = cv2.cvtColor(
                np.uint8([[[target_hue, 255, 255]]]),
                cv2.COLOR_HSV2BGR
            )[0][0]
            rectangle_color = (int(hue_bgr[0]), int(hue_bgr[1]), int(hue_bgr[2]))
            cv2.rectangle(hue_frame, (x, y), (x+w, y+h), rectangle_color, 2)

            # Calculate frequency from area and map to a musical scale
            area = cv2.contourArea(largest_contour)
            raw_freq = 220 + (area % 300)
            harmonic_freq = self.quantize_to_scale(raw_freq)

            # Update or start the hue oscillator
            self.update_hue_oscillator(harmonic_freq, hue_volume, hue_reverb)
        else:
            # No hue detected => Stop oscillator
            self.stop_hue_oscillator()

        # 1) Update the main "camera_bitmap" with the hue-detection feed
        hue_frame_rgb = cv2.cvtColor(hue_frame, cv2.COLOR_BGR2RGB)
        camera_bitmap.SetBitmap(
            wx.Bitmap.FromBuffer(
                hue_frame_rgb.shape[1],
                hue_frame_rgb.shape[0],
                hue_frame_rgb
            )
        )

        # 2) Edge detection
        blurred = cv2.GaussianBlur(edge_frame, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        edge_bitmap.SetBitmap(
            wx.Bitmap.FromBuffer(
                edges_rgb.shape[1],
                edges_rgb.shape[0],
                edges_rgb
            )
        )

        # 3) Mask visualization
        mask_rgb = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        mask_bitmap.SetBitmap(
            wx.Bitmap.FromBuffer(
                mask_rgb.shape[1],
                mask_rgb.shape[0],
                mask_rgb
            )
        )

    def stop_hue_oscillator(self):
        """ Stops the hue oscillator if it is running. """
        if self.hue_oscillator:
            if self.hue_reverb_effect:
                self.hue_reverb_effect.stop()
            self.hue_oscillator.stop()
            self.hue_oscillator = None
            self.hue_reverb_effect = None

    def update_hue_oscillator(self, target_freq, volume, reverb):
        """ Smoothly updates or initializes the hue oscillator. """
        # Smooth transition to new frequency
        self.current_freq += (target_freq - self.current_freq) * 0.1

        if self.hue_oscillator is None:
            # Start the oscillator with harmonic effects
            self.hue_oscillator = Sine(freq=self.current_freq, mul=volume)
            self.hue_reverb_effect = self.create_hue_effects(self.hue_oscillator, volume, reverb)
        else:
            # Update frequency and amplitude
            if self.frame_counter % 5 == 0:  # Reduce choppiness by updating less frequently
                self.hue_oscillator.setFreq(self.current_freq)
            self.hue_oscillator.setMul(volume)
            if self.hue_reverb_effect:
                self.hue_reverb_effect.setSize(reverb)
                self.hue_reverb_effect.setBal(reverb)

    def create_hue_effects(self, oscillator, volume, reverb):
        """ Creates harmonic effects for the oscillator. """
        # Add a light chorus
        chorus = Chorus(oscillator, depth=0.5, feedback=0.25, bal=0.2)
        # Add compression to avoid harsh dynamics
        compressed = Compress(
            chorus,
            thresh=-10,  # dB threshold
            ratio=4.0,   # Compression ratio
            risetime=0.01,
            falltime=0.1
        )
        # Add reverb
        reverb_effect = Freeverb(compressed, size=reverb, bal=reverb)
        return reverb_effect.out()

    def quantize_to_scale(self, freq):
        """ Quantizes the frequency to a musical scale for harmonic sound. """
        # Example: A minor pentatonic scale frequencies
        SCALE_FREQUENCIES = [
            220.0, 246.94, 261.63, 293.66, 329.63, 392.0, 440.0, 493.88, 523.25, 587.33
        ]
        return min(SCALE_FREQUENCIES, key=lambda x: abs(x - freq))
