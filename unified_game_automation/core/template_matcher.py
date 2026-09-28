"""Bounded scale search with cached templates; reject flat templates."""
from collections import OrderedDict
import cv2
import numpy as np


class TemplateMatcher:
    def __init__(self):
        self._scaled = OrderedDict()

    def match(self, screen, template, minimum=1.0, maximum=1.0):
        if not (0.5 <= minimum <= maximum <= 2.0):
            raise ValueError("Template scales must satisfy 0.5 <= min <= max <= 2.0")
        if float(np.std(template)) < 1e-6:
            return None
        best = None
        for scale in np.linspace(minimum, maximum, max(1, int(round((maximum-minimum)/0.05))+1)):
            width = max(1, int(round(template.shape[1]*scale)))
            height = max(1, int(round(template.shape[0]*scale)))
            if height > screen.shape[0] or width > screen.shape[1]:
                continue
            key = (id(template), width, height)
            if key not in self._scaled:
                # Retain the source so its id cannot be recycled while cached.
                self._scaled[key] = (template, cv2.resize(template, (width, height)))
                while len(self._scaled) > 128:
                    self._scaled.popitem(last=False)
            scaled = self._scaled[key][1]
            if float(np.std(scaled)) < 1e-6:
                continue
            result = cv2.matchTemplate(screen, scaled, cv2.TM_CCOEFF_NORMED)
            _, score, _, location = cv2.minMaxLoc(result)
            if best is None or score > best[0]:
                best = (score, location, (width, height))
        return best
