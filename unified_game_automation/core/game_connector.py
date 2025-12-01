# Unified game connector with BitBlt capture
# Combines functionality from main.py GameConnector and arrival_skill_ocr/game_connector.py

from pywinauto import Application
import win32gui
import win32con
import win32ui
from ctypes import windll
from PIL import Image

class GameConnector:
    def __init__(self, status_callback=None):
        """Initialize the unified game connector"""
        self.game_window = None
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
        return self.game_window is not None

    def capture_area_bitblt(self, area):
        """
        Capture a specific area using BitBlt method - works even with background windows
        Args:
            area: Tuple of (left, top, width, height) in screen coordinates
        Returns:
            PIL Image or None if capture failed
        """
        if not self.game_window:
            return None

        try:
            hwnd = self.game_window.handle

            if win32gui.IsIconic(hwnd):
                return None

            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            result = windll.gdi32.BitBlt(saveDC.GetSafeHdc(), 0, 0, width, height,
                                       hwndDC, 0, 0, win32con.SRCCOPY)

            if result:
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)
                full_image = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                                            bmpstr, 'raw', 'BGRX', 0, 1)

                area_left, area_top, area_width, area_height = area
                rel_left = area_left - left
                rel_top = area_top - top

                cropped = full_image.crop((rel_left, rel_top,
                                         rel_left + area_width,
                                         rel_top + area_height))

                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(hwnd, hwndDC)

                return cropped

        except Exception:
            pass

        try:
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
        except:
            pass

        return None
