from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.carousel import Carousel
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line, RenderContext, BindTexture
from kivy.core.image import Image as CoreImage
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
import math
import io
import time
import json
import os
from collections import defaultdict

# ---------- Android detection ----------
try:
    from jnius import autoclass
    ANDROID = True
    ByteArrayOutputStream = autoclass('java.io.ByteArrayOutputStream')
    CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')
except ImportError:
    ANDROID = False
    print("Running on desktop – dummy apps will be used")

# ---------- Gesture helpers ----------
def load_gesture_map(app_data_dir):
    path = os.path.join(app_data_dir, 'gestures.json')
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_gesture_map(app_data_dir, mapping):
    path = os.path.join(app_data_dir, 'gestures.json')
    try:
        with open(path, 'w') as f:
            json.dump(mapping, f)
    except Exception as e:
        print(f"Could not save gestures: {e}")

# ---------- StatusBar (built‑in) ----------
class StatusBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='horizontal', **kwargs)
        self.size_hint_y = None
        self.height = 40
        self.padding = [10, 0, 10, 0]
        with self.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
        self.network_label = Label(text="4G", font_size='12sp', size_hint_x=None, width=40, color=(1,1,1,0.8))
        self.time_label = Label(text="...", font_size='14sp', size_hint_x=1, halign='center', valign='middle')
        self.time_label.bind(size=self.time_label.setter('text_size'))
        self.battery_label = Label(text="100%", font_size='14sp', size_hint_x=None, width=60, color=(0.5,1,0.5,1), halign='right', valign='middle')
        self.battery_label.bind(size=self.battery_label.setter('text_size'))
        self.add_widget(self.network_label)
        self.add_widget(self.time_label)
        self.add_widget(self.battery_label)
        Clock.schedule_interval(self.update_info, 2.0)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def update_info(self, *args):
        self.time_label.text = time.strftime("%H:%M")
        try:
            from plyer import battery
            status = battery.status
            if status and 'percentage' in status:
                percent = status['percentage']
                self.battery_label.text = f"{int(percent)}%"
            else:
                self.battery_label.text = "100%"
        except:
            self.battery_label.text = "100%"

# ---------- iOS‑style button ----------
class iOSButton(Button):
    def __init__(self, **kwargs):
        self.icon_texture = kwargs.pop('icon_texture', None)
        self.icon_color = (0.5, 0.5, 0.5, 1)
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.size_hint = (None, None)
        self.size = (dp(56), dp(56))

    def set_icon_color(self, color):
        self.icon_color = color
        self.redraw()

    def redraw(self, *args):
        if not self.canvas:
            return
        self.canvas.before.clear()
        with self.canvas.before:
            color = self.icon_color
            if self.state == 'down':
                color = (color[0]*0.75, color[1]*0.75, color[2]*0.75, 1)
            if self.icon_texture:
                Color(*color)
                Rectangle(pos=self.pos, size=self.size, texture=self.icon_texture)
            else:
                Color(*color)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[self.width/2])

    def on_state(self, widget, state):
        self.redraw()

    def on_size(self, *args):
        self.redraw()

    def on_pos(self, *args):
        self.redraw()

# ---------- Long‑press button ----------
class LongPressAppButton(Button):
    def __init__(self, **kwargs):
        self.icon_texture = kwargs.pop('icon_texture', None)
        self.icon_color = (0.5, 0.5, 0.5, 1)
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.size_hint = (None, None)
        self.size = (dp(56), dp(56))
        self.register_event_type('on_long_press')
        self._long_press_triggered = False
        self._clock_event = None
        self.tap_callback = None

    def set_icon_color(self, color):
        self.icon_color = color
        self.redraw()

    def redraw(self, *args):
        if not self.canvas:
            return
        self.canvas.before.clear()
        with self.canvas.before:
            color = self.icon_color
            if self.state == 'down':
                color = (color[0]*0.75, color[1]*0.75, color[2]*0.75, 1)
            if self.icon_texture:
                Color(*color)
                Rectangle(pos=self.pos, size=self.size, texture=self.icon_texture)
            else:
                Color(*color)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[self.width/2])

    def on_state(self, widget, state):
        self.redraw()

    def on_size(self, *args):
        self.redraw()

    def on_pos(self, *args):
        self.redraw()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._long_press_triggered = False
            self._clock_event = Clock.schedule_once(self._check_long_press, 0.6)
            return super().on_touch_down(touch)
        return False

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            return super().on_touch_move(touch)
        else:
            self._cancel_long_press()
            return False

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            if self._long_press_triggered:
                self._cancel_long_press()
                return True
            else:
                self._cancel_long_press()
                if self.tap_callback:
                    self.tap_callback()
                return super().on_touch_up(touch)
        return False

    def _check_long_press(self, dt):
        if self.state == 'down':
            self._long_press_triggered = True
            self.dispatch('on_long_press')

    def _cancel_long_press(self):
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None

    def on_long_press(self, *args):
        pass

# ---------- Gesture overlay ----------
class GestureOverlay(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type('on_gesture')
        self.points = []
        self.drawing = False
        with self.canvas.after:
            self.line_color = Color(1, 1, 1, 0.7)
            self.line = Line(points=[], width=dp(2))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.points = [touch.x, touch.y]
            self.drawing = True
            self.line.points = self.points
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.drawing:
            self.points += [touch.x, touch.y]
            self.line.points = self.points
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.drawing:
            self.drawing = False
            self.line.points = []
            gesture = self._recognise()
            if gesture:
                self.dispatch('on_gesture', gesture)
            return True
        return super().on_touch_up(touch)

    def _recognise(self):
        if len(self.points) < 10:
            return None
        pts = list(zip(self.points[0::2], self.points[1::2]))
        min_x = min(p[0] for p in pts)
        max_x = max(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        max_y = max(p[1] for p in pts)
        width = max_x - min_x
        height = max_y - min_y
        if width < dp(30) and height < dp(30):
            return None
        aspect = width / height if height != 0 else 1
        if 0.7 < aspect < 1.3:
            cx = (min_x + max_x) / 2
            cy = (min_y + max_y) / 2
            distances = [math.hypot(p[0]-cx, p[1]-cy) for p in pts]
            avg_dist = sum(distances) / len(distances)
            if max(distances) - min(distances) < avg_dist * 0.4:
                return "circle"
        start = pts[0]
        end = pts[-1]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        else:
            return "down" if dy > 0 else "up"

    def on_gesture(self, gesture):
        pass

# ---------- Blurred background (GPU shader) ----------
BLUR_VERTEX_SHADER = '''
#ifdef GL_ES
    precision highp float;
#endif
attribute vec4 pos;
attribute vec2 uv;
varying vec2 tex_coord0;
void main() {
    gl_Position = pos;
    tex_coord0 = uv;
}
'''
BLUR_FRAGMENT_SHADER = '''
#ifdef GL_ES
    precision highp float;
#endif
varying vec2 tex_coord0;
uniform sampler2D texture0;
uniform float blur_size;
void main() {
    vec4 color = vec4(0.0);
    float total = 0.0;
    for (float x = -4.0; x <= 4.0; x++) {
        for (float y = -4.0; y <= 4.0; y++) {
            vec2 offset = vec2(x, y) * blur_size;
            color += texture2D(texture0, tex_coord0 + offset);
            total += 1.0;
        }
    }
    gl_FragColor = color / total;
}
'''

class BlurredBackground(Widget):
    source_texture = ObjectProperty(None, allownone=True)
    blur_strength = NumericProperty(0.5)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._shader = None
        self.bind(source_texture=self._update_shader, blur_strength=self._update_shader,
                  size=self._update_shader, pos=self._update_shader)

    def _update_shader(self, *args):
        if not self.source_texture:
            self.canvas.clear()
            with self.canvas:
                Color(0, 0, 0, 0.4)
                Rectangle(pos=self.pos, size=self.size)
            return
        self.canvas.clear()
        with self.canvas:
            self._shader = RenderContext()
            self._shader.shader.fs = BLUR_FRAGMENT_SHADER
            self._shader.shader.vs = BLUR_VERTEX_SHADER
            self._shader['blur_size'] = self.blur_strength
            self._shader['texture0'] = 0
            BindTexture(texture=self.source_texture, index=0)
            Rectangle(pos=self.pos, size=self.size)

# ---------- Terminal popup ----------
class TerminalPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "AyoOS Terminal"
        self.size_hint = (0.9, 0.8)
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(5))
        self.output = TextInput(readonly=True, size_hint_y=0.8, background_color=(0.1,0.1,0.1,1), foreground_color=(0,1,0,1))
        self.input_line = TextInput(hint_text="Enter command...", multiline=False, size_hint_y=None, height=dp(40), background_color=(0.2,0.2,0.2,1), foreground_color=(1,1,1,1))
        self.input_line.bind(on_text_validate=self.execute_command)
        btn_clear = Button(text="Clear", size_hint_y=None, height=dp(35))
        btn_clear.bind(on_press=lambda x: setattr(self.output, 'text', ''))
        layout.add_widget(self.output)
        layout.add_widget(self.input_line)
        layout.add_widget(btn_clear)
        self.content = layout

    def execute_command(self, instance):
        command = self.input_line.text.strip()
        if not command:
            return
        self.output.text += f"$ {command}\n"
        self.input_line.text = ""
        import threading, subprocess
        threading.Thread(target=self._run, args=(command,), daemon=True).start()

    def _run(self, command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=5)
            out = result.stdout + result.stderr
        except Exception as e:
            out = str(e)
        Clock.schedule_once(lambda dt: self._append(out))

    def _append(self, text):
        self.output.text += text + "\n"

# ---------- Expandable folder section ----------
class ExpandableSection(BoxLayout):
    def __init__(self, title, content, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, **kwargs)
        self.content = content
        self.toggle_btn = Button(text=title, size_hint_y=None, height=dp(40), background_color=(0.4,0.4,0.4,1))
        self.toggle_btn.bind(on_press=self._toggle)
        self.add_widget(self.toggle_btn)
        self.content_widget = content
        self.add_widget(self.content_widget)
        self.content_visible = True
        self._update_height()

    def _toggle(self, instance):
        if self.content_visible:
            self.remove_widget(self.content_widget)
            self.content_visible = False
        else:
            self.add_widget(self.content_widget)
            self.content_visible = True
        self._update_height()

    def _update_height(self):
        h = self.toggle_btn.height
        if self.content_visible:
            h += self.content_widget.height
        self.height = h

# ---------- Helper functions ----------
def get_kivy_texture_from_android(pm, activity_info):
    try:
        drawable = activity_info.loadIcon(pm)
        Bitmap = autoclass('android.graphics.Bitmap')
        BitmapConfig = autoclass('android.graphics.Bitmap$Config')
        Canvas = autoclass('android.graphics.Canvas')
        width = drawable.getIntrinsicWidth() or 96
        height = drawable.getIntrinsicHeight() or 96
        bitmap = Bitmap.createBitmap(width, height, BitmapConfig.ARGB_8888)
        canvas = Canvas(bitmap)
        drawable.setBounds(0, 0, canvas.getWidth(), canvas.getHeight())
        drawable.draw(canvas)
        stream = ByteArrayOutputStream()
        bitmap.compress(CompressFormat.PNG, 100, stream)
        byte_array = stream.toByteArray()
        python_bytes = bytes(byte_array)
        data = io.BytesIO(python_bytes)
        return CoreImage(data, ext='png').texture
    except:
        return None

IOS_COLORS = [
    (0.5,0.5,0.5,1), (0.9,0.8,0.2,1), (0.3,0.3,0.3,1), (0.9,0.2,0.2,1),
    (0.2,0.6,0.9,1), (0.1,0.1,0.1,1), (0.4,0.7,1.0,1), (1.0,0.6,0.1,1),
    (0.1,0.8,0.3,1), (0.1,0.5,0.9,1), (1.0,0.4,0.4,1), (0.2,0.2,0.2,1),
    (0.2,0.6,1.0,1), (0.4,0.6,0.9,1), (0.9,0.2,0.4,1), (0.6,0.2,0.8,1),
    (0.1,0.1,0.1,1), (0.9,0.5,0.2,1), (0.2,0.7,0.2,1), (0.4,0.6,0.9,1),
    (0.5,0.5,0.5,1), (0.9,0.2,0.2,1), (0.8,0.2,0.2,1), (0.1,0.2,0.2,1),
    (0.9,0.7,0.1,1), (0.1,0.5,0.9,1), (0.3,0.5,0.9,1), (0.2,0.8,0.2,1)
]

def create_home_cell(app_data, launch_func, size=(dp(56), dp(56))):
    box = BoxLayout(orientation='vertical', size_hint=(1,1), spacing=dp(4))
    btn = iOSButton(icon_texture=app_data.get('texture'))
    btn.size = size
    if app_data.get('texture') is None:
        color = IOS_COLORS[abs(hash(app_data['name'])) % len(IOS_COLORS)]
        btn.set_icon_color(color)
    btn.bind(on_press=launch_func)
    label = Label(text=app_data['name'], font_size='11sp', color=(1,1,1,1), size_hint_y=None, height=dp(24), halign='center', shorten=True, shorten_from='right', valign='middle')
    label.bind(size=label.setter('text_size'))
    box.add_widget(btn)
    box.add_widget(label)
    return box

def create_drawer_cell(app_data, launch_func, long_press_func, size=(dp(56), dp(56))):
    box = BoxLayout(orientation='vertical', size_hint=(1,1), spacing=dp(4))
    btn = LongPressAppButton(icon_texture=app_data.get('texture'))
    btn.size = size
    if app_data.get('texture') is None:
        color = IOS_COLORS[abs(hash(app_data['name'])) % len(IOS_COLORS)]
        btn.set_icon_color(color)
    btn.tap_callback = launch_func
    btn.bind(on_long_press=long_press_func)
    label = Label(text=app_data['name'], font_size='11sp', color=(1,1,1,1), size_hint_y=None, height=dp(24), halign='center', shorten=True, shorten_from='right', valign='middle')
    label.bind(size=label.setter('text_size'))
    box.add_widget(btn)
    box.add_widget(label)
    return box

# ---------- Main App ----------
class iOSLauncher(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.favorites = []
        self.all_apps = []
        self.dock_icons = {"Phone": None, "Browser": None, "Chats": None, "Media": None}
        self.dock_pkgs = {"Phone": "", "Browser": "", "Chats": "", "Media": ""}
        self.current_activity = None
        self.pm = None
        self.use_folders = True
        self.gesture_map = {}
        self.wallpaper_texture = None

    def build(self):
        Window.fullscreen = True
        Window.clearcolor = (0.1, 0.1, 0.1, 1)

        # Wallpaper (fallback gradient)
        if ANDROID:
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                self.current_activity = PythonActivity.mActivity
                self.pm = self.current_activity.getPackageManager()
                WallpaperManager = autoclass('android.app.WallpaperManager')
                wm = WallpaperManager.getInstance(self.current_activity)
                drawable = wm.getDrawable()
                if drawable:
                    Bitmap = autoclass('android.graphics.Bitmap')
                    Config = autoclass('android.graphics.Bitmap$Config')
                    Canvas = autoclass('android.graphics.Canvas')
                    width = drawable.getIntrinsicWidth() or 1080
                    height = drawable.getIntrinsicHeight() or 1920
                    bitmap = Bitmap.createBitmap(width, height, Config.ARGB_8888)
                    canvas = Canvas(bitmap)
                    drawable.setBounds(0, 0, canvas.getWidth(), canvas.getHeight())
                    drawable.draw(canvas)
                    stream = ByteArrayOutputStream()
                    bitmap.compress(CompressFormat.PNG, 100, stream)
                    byte_array = stream.toByteArray()
                    data = io.BytesIO(bytes(byte_array))
                    self.wallpaper_texture = CoreImage(data, ext='png').texture
            except:
                pass
        if self.wallpaper_texture is None:
            from kivy.graphics.texture import Texture
            tex = Texture.create(size=(256,256), colorfmt='rgba')
            buf = bytearray()
            for y in range(256):
                for x in range(256):
                    r = int(0.1*255); g = int(0.1*255); b = int(0.3*255)
                    buf.extend([r,g,b,255])
            tex.blit_buffer(bytes(buf), colorfmt='rgba', bufferfmt='ubyte')
            self.wallpaper_texture = tex

        root = BoxLayout(orientation='vertical', padding=0, spacing=0)
        root.add_widget(StatusBar())

        # Top swipe zone (FIXED)
        class TopSwipeZone(Widget):
            def __init__(self, callback=None, **kw):
                super().__init__(size_hint=(1,None), height=dp(15), **kw)
                self.cb = callback
                self._sy = None
            def on_touch_down(self, t):
                if self.collide_point(*t.pos): self._sy = t.y; return True
            def on_touch_move(self, t):
                if self._sy and self._sy - t.y > dp(60): self._sy=None; self.cb(); return True
            def on_touch_up(self, t): self._sy=None
        root.add_widget(TopSwipeZone(callback=self.minimize_current_app))

        # Inner container with side margins
        inner = BoxLayout(orientation='vertical', padding=[dp(16),0,dp(16),0], spacing=0)
        self.home_carousel = Carousel(direction='right', size_hint_y=1)
        inner.add_widget(self.home_carousel)
        root.add_widget(inner)

        # Invisible corner buttons
        corner_overlay = FloatLayout(size_hint=(1,None), height=dp(40))
        corner_overlay.add_widget(self._make_corner_btn(self.open_toolbar, 'left'))
        corner_overlay.add_widget(self._make_corner_btn(self.open_notifications, 'right'))
        root.add_widget(corner_overlay)

        # Dock area with blur
        bottom_area = FloatLayout(size_hint=(1,None), height=dp(100))
        if self.wallpaper_texture:
            dock_blur = BlurredBackground(size_hint=(1,1), blur_strength=0.5, source_texture=self.wallpaper_texture)
            bottom_area.add_widget(dock_blur)
        else:
            with bottom_area.canvas:
                Color(0,0,0,0.4); Rectangle(pos=bottom_area.pos, size=bottom_area.size)
        dock_row = self._build_dock()
        dock_wrapper = AnchorLayout(anchor_x='center', anchor_y='bottom', size_hint=(1,1))
        dock_wrapper.add_widget(dock_row)
        bottom_area.add_widget(dock_wrapper)
        root.add_widget(bottom_area)

        self.load_installed_apps()
        self.load_favorites()
        self.load_gesture_map()
        if not self.favorites:
            self.favorites = self.all_apps[:4]
            self.save_favorites()
        self.initialize_home_screen()
        self.add_drawer_page()
        self.add_magic_canvas_page()
        self.update_dock_icons()
        return root

    def _make_corner_btn(self, callback, side):
        class CBtn(Widget):
            def __init__(self, cb, **kw):
                super().__init__(size_hint=(None,None), size=(dp(40),dp(40)), **kw)
                self.cb = cb
            def on_touch_down(self, t):
                if self.collide_point(*t.pos): self.cb(); return True
        if side == 'left':
            return CBtn(callback, pos_hint={'x':0, 'y':0})
        else:
            return CBtn(callback, pos_hint={'right':1, 'y':0})

    def _build_dock(self):
        dock = BoxLayout(orientation='horizontal', size_hint=(None,None), width=dp(4*56+3*30), height=dp(80), spacing=dp(30), padding=[0,dp(4)])
        self.dock_buttons = []
        for name in ["Phone","Browser","Chats","Media"]:
            box = BoxLayout(orientation='vertical', size_hint=(None,None), width=dp(56), height=dp(80), spacing=dp(4))
            btn = iOSButton(icon_texture=None)
            btn.size = (dp(56), dp(56))
            fallback = {"Phone":(0.2,0.8,0.2,1),"Browser":(0.1,0.5,0.9,1),"Chats":(0.3,0.8,0.4,1),"Media":(0.9,0.2,0.4,1)}[name]
            btn.set_icon_color(fallback)
            btn.bind(on_press=lambda i, n=name: self.launch_dock_app(n))
            label = Label(text=name, font_size='11sp', color=(1,1,1,1), size_hint_y=None, height=dp(20), halign='center', valign='middle')
            label.bind(size=label.setter('text_size'))
            box.add_widget(btn); box.add_widget(label)
            dock.add_widget(box)
            self.dock_buttons.append((name, btn))
        return dock

    # ---------- Gesture map persistence ----------
    def load_gesture_map(self):
        self.gesture_map = load_gesture_map(self.user_data_dir)
    def save_gesture_map(self):
        save_gesture_map(self.user_data_dir, self.gesture_map)

    def minimize_current_app(self):
        if self.current_activity:
            self.current_activity.moveTaskToBack(True)

    def open_toolbar(self):
        popup = Popup(title='Toolbar', content=Label(text='Quick tools coming soon'), size_hint=(0.6,0.4))
        popup.open()

    def open_notifications(self):
        if ANDROID:
            try:
                sb = self.current_activity.getSystemService('statusbar')
                sb.expandNotificationsPanel()
            except:
                pass

    # ---------- Magic Canvas ----------
    def add_magic_canvas_page(self):
        canvas_page = BoxLayout(orientation='vertical', spacing=dp(10))
        prompt = Label(text="Draw a shape to launch an app\nTap 'Assign Gestures' to set shortcuts", font_size='14sp', color=(1,1,1,0.8), size_hint_y=None, height=dp(40))
        canvas_page.add_widget(prompt)
        gesture_overlay = GestureOverlay(size_hint=(1,1))
        gesture_overlay.bind(on_gesture=self.handle_magic_gesture)
        assign_btn = Button(text="Assign Gestures", size_hint=(None,None), size=(dp(150),dp(40)), pos_hint={'center_x':0.5})
        assign_btn.bind(on_press=lambda x: self.open_gesture_assignment('global'))
        canvas_page.add_widget(assign_btn)
        canvas_page.add_widget(gesture_overlay)
        self.home_carousel.add_widget(canvas_page)

    def handle_magic_gesture(self, instance, gesture):
        pkg = self.gesture_map.get(gesture)
        if pkg: self.launch_app(pkg)
        else: Popup(title='No App', content=Label(text=f'Gesture "{gesture}" not assigned.'), size_hint=(0.6,0.4)).open()

    def open_gesture_assignment(self, name):
        content = BoxLayout(orientation='vertical', spacing=dp(5), padding=dp(10))
        popup = Popup(title='Assign Gesture', content=content, size_hint=(0.8,0.6))
        for g in ['circle','up','down','left','right']:
            btn = Button(text=g, size_hint_y=None, height=dp(40))
            btn.bind(on_press=lambda x, gest=g: self._choose_app_for_gesture(gest, popup))
            content.add_widget(btn)
        popup.open()

    def _choose_app_for_gesture(self, gesture, parent_popup):
        parent_popup.dismiss()
        def on_app_chosen(pkg):
            self.gesture_map[gesture] = pkg
            self.save_gesture_map()
            Popup(title='Success', content=Label(text=f'Gesture "{gesture}" assigned!'), size_hint=(0.5,0.3)).open()
        # Simple scrollable list of apps
        content = BoxLayout(orientation='vertical')
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        for app in self.all_apps:
            btn = Button(text=f"{app['name']} ({app['pkg']})", size_hint_y=None, height=dp(40))
            btn.bind(on_press=lambda x, pkg=app['pkg']: on_app_chosen(pkg))
            grid.add_widget(btn)
        scroll.add_widget(grid)
        content.add_widget(scroll)
        Popup(title="Choose App", content=content, size_hint=(0.9,0.8)).open()

    # ---------- App loading & favourites ----------
    def load_installed_apps(self):
        texture_cache = {}
        if ANDROID:
            try:
                Intent = autoclass('android.content.Intent')
                launcher_intent = Intent(Intent.ACTION_MAIN, None).addCategory(Intent.CATEGORY_LAUNCHER)
                installed = self.pm.queryIntentActivities(launcher_intent, 0)
                for i in range(installed.size()):
                    info = installed.get(i)
                    name = str(info.loadLabel(self.pm))
                    pkg = str(info.activityInfo.packageName)
                    if pkg not in texture_cache:
                        texture_cache[pkg] = get_kivy_texture_from_android(self.pm, info.activityInfo)
                    self.all_apps.append({'name':name, 'pkg':pkg, 'texture':texture_cache[pkg]})
            except Exception as e:
                print(f"Error loading apps: {e}")
        else:
            dummy = ["Camera","Photos","Settings","Calendar","Maps","Clock","Weather","Notes",
                     "FaceTime","App Store","Health","Wallet","Safari","Mail","Music","Podcasts",
                     "TV","Books","Home","Files","Contacts","Reminders","News","Stocks","iMovie",
                     "GarageBand","Keynote","Find My"]
            for name in dummy:
                self.all_apps.append({'name':name, 'pkg':f"com.dummy.{name.lower().replace(' ','')}", 'texture':None})

    def get_favorites_path(self):
        return os.path.join(self.user_data_dir, 'favorites.json')

    def save_favorites(self):
        with open(self.get_favorites_path(), 'w') as f:
            json.dump([app['pkg'] for app in self.favorites], f)

    def load_favorites(self):
        path = self.get_favorites_path()
        if not os.path.exists(path):
            return
        with open(path, 'r') as f:
            pkg_list = json.load(f)
        self.favorites = [app for app in self.all_apps if app['pkg'] in pkg_list]
        self.favorites.sort(key=lambda x: pkg_list.index(x['pkg']))

    def initialize_home_screen(self):
        self.home_pages = []
        self.rebuild_home_pages()

    def rebuild_home_pages(self):
        self.home_carousel.clear_widgets()
        self.home_pages = []
        per_page = 24
        total = len(self.favorites)
        num_pages = max(1, math.ceil(total / per_page))
        for i in range(num_pages):
            page = GridLayout(cols=4, spacing=dp(10), size_hint=(1,1))
            self.home_pages.append(page)
            self.home_carousel.add_widget(page)
        for i, page in enumerate(self.home_pages):
            page.clear_widgets()
            for app in self.favorites[i*per_page:(i+1)*per_page]:
                cell = create_home_cell(app, launch_func=lambda i, pkg=app['pkg']: self.launch_app(pkg))
                page.add_widget(cell)
            while len(page.children) < 24:
                page.add_widget(Widget(size_hint=(1,1)))

    def add_drawer_page(self):
        drawer_box = BoxLayout(orientation='vertical', spacing=dp(5))
        self.drawer_search = TextInput(hint_text="Search apps...", font_size='14sp', size_hint_y=None, height=dp(40), background_color=(0.3,0.3,0.3,1), foreground_color=(1,1,1,1), multiline=False)
        self.drawer_search.bind(text=self.on_drawer_search)
        drawer_box.add_widget(self.drawer_search)
        self.folder_toggle = Button(text="Folders: ON", size_hint_y=None, height=dp(30), background_color=(0.4,0.4,0.4,1))
        self.folder_toggle.bind(on_press=self.toggle_folders)
        drawer_box.add_widget(self.folder_toggle)
        scroll = ScrollView(size_hint=(1,1))
        self.drawer_container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.drawer_container.bind(minimum_height=self.drawer_container.setter('height'))
        scroll.add_widget(self.drawer_container)
        drawer_box.add_widget(scroll)
        self.home_carousel.add_widget(drawer_box)
        self.populate_drawer(self.all_apps)

    def toggle_folders(self, instance):
        self.use_folders = not self.use_folders
        instance.text = "Folders: ON" if self.use_folders else "Folders: OFF"
        self.populate_drawer(self.all_apps if not self.drawer_search.text else [a for a in self.all_apps if self.drawer_search.text.lower() in a['name'].lower()])

    def populate_drawer(self, apps):
        self.drawer_container.clear_widgets()
        if self.use_folders:
            cats = defaultdict(list)
            for app in apps:
                cat = self._categorise(app['name'])
                cats[cat].append(app)
            for cat in sorted(cats, key=lambda x: (x=="Other", x)):
                apps_in_cat = cats[cat]
                grid = GridLayout(cols=4, spacing=dp(8), size_hint_y=None)
                grid.bind(minimum_height=grid.setter('height'))
                for a in apps_in_cat:
                    cell = create_drawer_cell(a, launch_func=lambda i, pkg=a['pkg']: self.launch_app(pkg), long_press_func=lambda i, ad=a: self.show_context_menu(ad))
                    grid.add_widget(cell)
                grid.height = (len(apps_in_cat)//4 + 1) * (dp(56+24+4))
                section = ExpandableSection(title=f"{cat} ({len(apps_in_cat)})", content=grid)
                self.drawer_container.add_widget(section)
        else:
            grid = GridLayout(cols=4, spacing=dp(10), size_hint_y=None)
            grid.bind(minimum_height=grid.setter('height'))
            for a in apps:
                cell = create_drawer_cell(a, launch_func=lambda i, pkg=a['pkg']: self.launch_app(pkg), long_press_func=lambda i, ad=a: self.show_context_menu(ad))
                grid.add_widget(cell)
            grid.height = (len(apps)//4 + 1) * (dp(56+24+4))
            self.drawer_container.add_widget(grid)

    def _categorise(self, name):
        name = name.lower()
        if any(kw in name for kw in ["facebook","instagram","twitter","whatsapp","telegram","snapchat","messenger","tiktok","reddit"]): return "Social"
        if any(kw in name for kw in ["game","play","chess","puzzle","candy","crush","clash","pubg","fortnite","minecraft"]): return "Games"
        if any(kw in name for kw in ["notes","keep","todo","calendar","drive","docs","sheets","slides","onenote","evernote","notion","trello"]): return "Productivity"
        if any(kw in name for kw in ["camera","gallery","photos","music","video","youtube","netflix","spotify","podcast","tv"]): return "Media"
        if any(kw in name for kw in ["settings","security","battery","wifi","bluetooth","files","file manager","updater","about"]): return "System"
        if any(kw in name for kw in ["phone","dialer","contacts","messages","sms","gmail","email","chat"]): return "Communication"
        if any(kw in name for kw in ["browser","chrome","firefox","opera","safari","edge"]): return "Browser"
        if any(kw in name for kw in ["calculator","compass","clock","weather","maps","translate","flashlight","scanner"]): return "Tools"
        return "Other"

    def on_drawer_search(self, instance, text):
        filtered = [app for app in self.all_apps if text.lower() in app['name'].lower()]
        self.populate_drawer(filtered)

    def add_favorite(self, app_data):
        if app_data not in self.favorites:
            self.favorites.append(app_data)
            self.save_favorites()
            self.rebuild_home_pages()
            self.add_drawer_page()
            self.add_magic_canvas_page()

    def remove_favorite(self, app_data):
        if app_data in self.favorites:
            self.favorites.remove(app_data)
            self.save_favorites()
            self.rebuild_home_pages()
            self.add_drawer_page()
            self.add_magic_canvas_page()

    def show_context_menu(self, app_data):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        popup = Popup(title=app_data['name'], content=content, size_hint=(0.8,0.4))
        if app_data in self.favorites:
            btn_add = Button(text="Remove from Home", size_hint_y=None, height=dp(40))
            btn_add.bind(on_press=lambda x: self.remove_favorite(app_data))
        else:
            btn_add = Button(text="Add to Home", size_hint_y=None, height=dp(40))
            btn_add.bind(on_press=lambda x: self.add_favorite(app_data))
        btn_add.bind(on_press=lambda x: popup.dismiss())
        btn_info = Button(text="App Info", size_hint_y=None, height=dp(40))
        btn_info.bind(on_press=lambda x: self.app_info(app_data['pkg']) or popup.dismiss())
        btn_uninstall = Button(text="Uninstall", size_hint_y=None, height=dp(40))
        btn_uninstall.bind(on_press=lambda x: self.uninstall_app(app_data['pkg']) or popup.dismiss())
        btn_terminal = Button(text="Open Terminal", size_hint_y=None, height=dp(40))
        btn_terminal.bind(on_press=lambda x: (self.open_terminal(), popup.dismiss()))
        content.add_widget(btn_add); content.add_widget(btn_info); content.add_widget(btn_uninstall); content.add_widget(btn_terminal)
        popup.open()

    def open_terminal(self):
        TerminalPopup().open()

    def launch_app(self, package_name):
        if self.pm and self.current_activity and package_name:
            try:
                launch_intent = self.pm.getLaunchIntentForPackage(package_name)
                if launch_intent: self.current_activity.startActivity(launch_intent)
            except Exception as e:
                print(f"Launch failed: {e}")

    def uninstall_app(self, package_name):
        if self.current_activity:
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            intent = Intent(Intent.ACTION_DELETE, Uri.parse(f"package:{package_name}"))
            self.current_activity.startActivity(intent)

    def app_info(self, package_name):
        if self.current_activity:
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            intent.setData(autoclass('android.net.Uri').parse(f"package:{package_name}"))
            self.current_activity.startActivity(intent)

    def update_dock_icons(self):
        for app in self.all_apps:
            pkg = app['pkg'].lower(); name = app['name'].lower()
            if not self.dock_icons["Phone"] and (pkg in ["com.google.android.dialer","com.android.contacts","com.android.dialer"] or "phone" in name):
                self.dock_icons["Phone"]=app['texture']; self.dock_pkgs["Phone"]=app['pkg']
            if not self.dock_icons["Browser"] and (pkg in ["com.android.chrome","com.mi.globalbrowser"] or "browser" in pkg):
                self.dock_icons["Browser"]=app['texture']; self.dock_pkgs["Browser"]=app['pkg']
            if not self.dock_icons["Chats"] and (pkg in ["com.google.android.apps.messaging","com.android.mms"] or "message" in name or "messaging" in name):
                self.dock_icons["Chats"]=app['texture']; self.dock_pkgs["Chats"]=app['pkg']
            if not self.dock_icons["Media"] and (pkg in ["com.miui.gallery","com.google.android.apps.photos"] or "gallery" in pkg or "photos" in pkg):
                self.dock_icons["Media"]=app['texture']; self.dock_pkgs["Media"]=app['pkg']
        for name, btn in self.dock_buttons:
            tex = self.dock_icons.get(name)
            if tex: btn.icon_texture = tex; btn.redraw()

    def launch_dock_app(self, name):
        pkg = self.dock_pkgs.get(name, "")
        if pkg: self.launch_app(pkg)
        elif self.current_activity:
            Intent = autoclass('android.content.Intent'); Uri = autoclass('android.net.Uri')
            try:
                if name=="Phone": self.current_activity.startActivity(Intent(Intent.ACTION_DIAL))
                elif name=="Chats":
                    intent = Intent(Intent.ACTION_MAIN); intent.addCategory(Intent.CATEGORY_APP_MESSAGING)
                    self.current_activity.startActivity(intent)
                elif name=="Browser": self.current_activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://www.google.com")))
                elif name=="Media":
                    intent = Intent(Intent.ACTION_VIEW); intent.setType("image/*")
                    self.current_activity.startActivity(intent)
            except Exception as e: print(f"Dock fallback: {e}")

if __name__ == '__main__':
    iOSLauncher().run()