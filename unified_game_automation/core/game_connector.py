# Unified game connector with BitBlt capture
# Combines functionality from main.py GameConnector and arrival_skill_ocr/game_connector.py

from pywinauto import Application
import win32gui
import win32con
import win32ui
from ctypes import windll
from PIL import Image
import threading
import functools


def guarded_input(method):
    @functools.wraps(method)
    def guarded(self, *args, **kwargs):
        with self._input_lock:
            allowed, dry = self.input_policy() if self.input_policy else (True, False)
            if not allowed:
                return False
            if dry:
                self.update_status(f"DRY RUN: would {method.__name__} at {args}")
                return True
            if not self.is_connected() or win32gui.IsIconic(self.game_window.handle):
                self.update_status("Game unavailable or minimized")
                return False
            # Click coordinates are window-relative in legacy profiles.
            coords = args[0] if args else kwargs.get("coords")
            client = self.get_client_rect()
            if not coords or not client:
                return False
            adjusted = kwargs.get("adjust_for_client_area", True)
            # Public coordinates are window-relative. The wrapped method applies
            # the window-to-client offset exactly once when requested.
            x, y = coords
            if not (0 <= x < client[2]-client[0] and 0 <= y < client[3]-client[1]):
                self.update_status("Click is outside the client; recalibrate")
                return False
            result = method(self, *args, **kwargs)
            if result and self.on_action:
                self.on_action()
            return result
    return guarded


class GameConnector:
    def __init__(self, status_callback=None):
        """Initialize the unified game connector"""
        self.game_window = None
        self._input_lock = threading.RLock()
        self.input_policy = None
        self.on_action = None
        self.status_callback = status_callback

    def update_status(self, message):
        """Update status via callback if available"""
        if self.status_callback:
            self.status_callback(message)

    def connect_to_game(self):
        """Connect to the game window by class name"""
        try:
            app = Application()
            app.connect(class_name="D3D Window")
            windows = app.windows(class_name="D3D Window")

            if len(windows) == 1:
                self.game_window = windows[0]
            elif len(windows) > 1:
                for window in windows:
                    window_text = window.window_text().lower()
                    if any(keyword in window_text for keyword in ["stellar", "game", "cabal"]):
                        self.game_window = window
                        break
                else:
                    for window in windows:
                        if window.is_visible():
                            self.game_window = window
                            break
                    else:
                        self.game_window = windows[0]
            else:
                raise Exception("No D3D Window found")

            if self.game_window.is_visible() and self.game_window.is_enabled():
                return True
            else:
                raise Exception("Found window but it's not visible or enabled")

        except Exception as e:
            self.update_status(f"Could not connect to the game. Make sure it's running. Error: {str(e)}")
            return False

    @guarded_input
    def click_at_position(self, coords, adjust_for_client_area=True):
        """Click at the specified coordinates in the game window"""
        if not self.game_window:
            return False
        try:
            if adjust_for_client_area:
                offset = self.get_window_client_offset()
                if offset:
                    adjusted_coords = (coords[0] - offset[0], coords[1] - offset[1])
                    self.game_window.click(coords=adjusted_coords)
                    return True

            self.game_window.click(coords=coords)
            return True
        except Exception as e:
            self.update_status(f"Click failed: {str(e)}")
            return False

    @guarded_input
    def middle_click_at_position(self, coords, adjust_for_client_area=True):
        """Middle click at the specified coordinates in the game window without moving mouse cursor"""
        if not self.game_window:
            return False
        try:
            target_coords = coords
            if adjust_for_client_area:
                offset = self.get_window_client_offset()
                if offset:
                    target_coords = (coords[0] - offset[0], coords[1] - offset[1])

            # Try pywinauto window click with button='middle'
            try:
                self.game_window.click(button='middle', coords=target_coords)
                return True
            except Exception:
                pass

            # Fallback to PostMessage WM_MBUTTONDOWN / WM_MBUTTONUP (no mouse movement)
            try:
                hwnd = self.game_window.handle
                lparam = ((int(target_coords[1]) & 0xFFFF) << 16) | (int(target_coords[0]) & 0xFFFF)
                win32gui.PostMessage(hwnd, win32con.WM_MBUTTONDOWN, win32con.MK_MBUTTON, lparam)
                win32gui.PostMessage(hwnd, win32con.WM_MBUTTONUP, 0, lparam)
                return True
            except Exception:
                pass

            return False
        except Exception as e:
            self.update_status(f"Middle click failed: {str(e)}")
            return False

    @guarded_input
    def right_click_at_position(self, coords, adjust_for_client_area=True):
        """Right click at the specified coordinates in the game window without moving mouse cursor"""
        if not self.game_window:
            return False
        try:
            target_coords = coords
            if adjust_for_client_area:
                offset = self.get_window_client_offset()
                if offset:
                    target_coords = (coords[0] - offset[0], coords[1] - offset[1])

            # Try pywinauto right click
            try:
                if hasattr(self.game_window, 'right_click'):
                    self.game_window.right_click(coords=target_coords)
                else:
                    self.game_window.click(button='right', coords=target_coords)
                return True
            except Exception:
                pass

            # Fallback to PostMessage WM_RBUTTONDOWN / WM_RBUTTONUP (no mouse movement)
            try:
                hwnd = self.game_window.handle
                lparam = ((int(target_coords[1]) & 0xFFFF) << 16) | (int(target_coords[0]) & 0xFFFF)
                win32gui.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lparam)
                win32gui.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, lparam)
                return True
            except Exception:
                pass

            return False
        except Exception as e:
            self.update_status(f"Right click failed: {str(e)}")
            return False




    def get_window_rect(self):
        """Get the rectangle of the game window"""
        if not self.game_window:
            return None
        try:
            return self.game_window.rectangle()
        except Exception:
            return None

    def get_client_rect(self):
        """Get the client rectangle of the game window"""
        if not self.game_window:
            return None
        try:
            hwnd = self.game_window.handle
            client_rect = win32gui.GetClientRect(hwnd)
            client_pos = win32gui.ClientToScreen(hwnd, (0, 0))
            return (
                client_pos[0],
                client_pos[1],
                client_pos[0] + client_rect[2],
                client_pos[1] + client_rect[3]
            )
        except Exception as e:
            self.update_status(f"Failed to get client rect: {str(e)}")
            return None

    def get_window_client_offset(self):
        """Calculate the offset between window coordinates and client coordinates"""
        if not self.game_window:
            return None
        try:
            window_rect = self.get_window_rect()
            client_rect = self.get_client_rect()
            if not window_rect or not client_rect:
                return None
            offset_x = client_rect[0] - window_rect.left
            offset_y = client_rect[1] - window_rect.top
            return (offset_x, offset_y)
        except Exception as e:
            self.update_status(f"Failed to calculate window-client offset: {str(e)}")
            return None

    def convert_to_window_coords(self, screen_x, screen_y):
        """Convert screen coordinates to window-relative coordinates"""
        if not self.game_window:
            return (screen_x, screen_y, False)
        try:
            rect = self.game_window.rectangle()
            rel_x = screen_x - rect.left
            rel_y = screen_y - rect.top
            return (rel_x, rel_y, True)
        except Exception:
            return (screen_x, screen_y, False)

    def is_connected(self):
        """Check if connected to game window"""
        if self.game_window is None:
            return False
        try:
            if win32gui.IsWindow(self.game_window.handle):
                return True
        except (AttributeError, TypeError):
            pass
        self.game_window = None
        return False

    def capture_area_bitblt(self, area):
        """
        Capture a specific area using BitBlt method - works even with background windows
        Args:
            area: Tuple of (left, top, width, height) in screen coordinates
        Returns:
            PIL Image or None if capture failed
        """
        area = self.resolve_area(area)
        if not area or not self.is_connected():
            return None

        hwndDC = None
        mfcDC = None
        saveDC = None
        saveBitMap = None
        hwnd = None
        old_bitmap = None

        try:
            hwnd = self.game_window.handle

            if win32gui.IsIconic(hwnd):
                return None

            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                return None

            hwndDC = win32gui.GetWindowDC(hwnd)
            if not hwndDC:
                return None
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            old_bitmap = saveDC.SelectObject(saveBitMap)

            result = windll.gdi32.BitBlt(saveDC.GetSafeHdc(), 0, 0, width, height,
                                       hwndDC, 0, 0, win32con.SRCCOPY)

            if result:
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)
                full_image = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                                            bmpstr, 'raw', 'BGRX', 0, 1)

                area_left, area_top, area_width, area_height = area
                
                # Support both absolute screen coordinates and window-relative coordinates
                rel_left = area_left - left
                rel_top = area_top - top
                if rel_left < 0 or rel_top < 0 or rel_left + area_width > width or rel_top + area_height > height:
                    self.update_status("Capture region is outside the game window; recalibrate")
                    return None

                # Clamp crop coordinates to valid image boundaries
                crop_left = max(0, min(int(rel_left), width - 1))
                crop_top = max(0, min(int(rel_top), height - 1))
                crop_right = max(crop_left + 1, min(crop_left + int(area_width), width))
                crop_bottom = max(crop_top + 1, min(crop_top + int(area_height), height))

                return full_image.crop((crop_left, crop_top, crop_right, crop_bottom))

        except Exception:
            pass
        finally:
            if old_bitmap is not None and saveDC is not None:
                try:
                    saveDC.SelectObject(old_bitmap)
                except Exception:
                    pass
            if saveBitMap is not None:
                try:
                    win32gui.DeleteObject(saveBitMap.GetHandle())
                except Exception:
                    pass
            if saveDC is not None:
                try:
                    saveDC.DeleteDC()
                except Exception:
                    pass
            if mfcDC is not None:
                try:
                    mfcDC.DeleteDC()
                except Exception:
                    pass
            if hwndDC is not None and hwnd is not None:
                try:
                    win32gui.ReleaseDC(hwnd, hwndDC)
                except Exception:
                    pass

        return None

    def take_screenshot(self, area=None):
        """Capture a screenshot of the requested area or full game window."""
        if not self.game_window:
            return None

        if area:
            return self.capture_area_bitblt(area)

        rect = self.get_window_rect()
        if not rect:
            return None

        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        width = right - left
        height = bottom - top
        return self.capture_area_bitblt((left, top, width, height))

    @guarded_input
    def double_click_at_position(self, coords):
        if not self.is_connected():
            return False
        offset = self.get_window_client_offset() or (0, 0)
        try:
            self.game_window.double_click(coords=(coords[0]-offset[0], coords[1]-offset[1]))
            return True
        except Exception as exc:
            self.update_status(f"Double click failed: {exc}")
            return False

    def screen_to_client_area(self, area):
        rect = self.get_client_rect()
        if not rect:
            raise ValueError("Connect to the game before calibrating")
        x, y, w, h = area
        if w <= 0 or h <= 0 or x < rect[0] or y < rect[1] or x+w > rect[2] or y+h > rect[3]:
            raise ValueError("Select a region entirely inside the game client")
        return {"space": "client", "x": x-rect[0], "y": y-rect[1], "width": w, "height": h,
                "client_size": [rect[2]-rect[0], rect[3]-rect[1]]}

    def resolve_area(self, area):
        if not isinstance(area, dict):
            return area  # Legacy profiles retain their explicit screen coordinates.
        rect = self.get_client_rect()
        if not rect or area.get("space") != "client":
            return None
        if area.get("client_size") != [rect[2]-rect[0], rect[3]-rect[1]]:
            self.update_status("Client size changed; recalibrate the region")
            return None
        return (rect[0]+area["x"], rect[1]+area["y"], area["width"], area["height"])

    @staticmethod
    def available_windows():
        windows = []
        def visit(hwnd, _):
            if win32gui.GetClassName(hwnd) == "D3D Window" and win32gui.IsWindowVisible(hwnd):
                windows.append((hwnd, win32gui.GetWindowText(hwnd)))
        win32gui.EnumWindows(visit, None)
        return windows

    def attach_window(self, hwnd):
        if not win32gui.IsWindow(hwnd) or win32gui.GetClassName(hwnd) != "D3D Window":
            return False
        app = Application().connect(handle=hwnd)
        self.game_window = app.window(handle=hwnd).wrapper_object()
        return self.is_connected()
