# -*- coding: utf-8 -*-
from pickle import dumps
from base64 import b64encode, b64decode
from datetime import datetime, time, timedelta
from copy import copy
from functools import partial
from pprint import pformat

from kivy.app import App
from kivy.config import Config
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.image import AsyncImage
from kivy.uix.floatlayout import FloatLayout
from kivy import platform
from kivy.logger import Logger
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.animation import Animation
from kivy.vector import Vector
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Line, Rectangle
from kivy.uix.screenmanager import Screen, RiseInTransition, FallOutTransition, \
    SlideTransition, NoTransition
from kivy.utils import get_color_from_hex
from kivy.properties import NumericProperty, ObjectProperty, StringProperty

if platform == 'android':
    Logger.debug('KBGALLERY: Importando %s' % datetime.now())
    import android
    from plyer.platforms.android import activity
    from jnius import autoclass, cast
    from android.runnable import run_on_ui_thread
    Intent = autoclass('android.content.Intent')
    String = autoclass('java.lang.String')

if platform == 'win' or platform == 'linux':
    Config.set('graphics', 'width', 480)
    Config.set('graphics', 'height', 756)

APP = 'KBGALLERY'


class KBGalleryApp(App):

    def build(self):
        Logger.debug("%s: build %s " % (APP, datetime.now()))
        self.use_kivy_settings = False
        return self.root

    def build_config(self, config):
        Logger.debug("%s: build_config %s " % (APP, datetime.now()))
        # config.setdefaults('general', {
        #     'nucleo': 'INDEFINIDO',
        #     'margen_ejec': 10,
        #     'margen_ayud': 5,
        #     'sound_alarm': 1,
        #     'vibration_alarm': 1,
        #     'numero': 0,
        #     's1': 'Sector1',
        #     's2': 'Sector2',
        #     's3': 'Sector3',
        #     'alarmas': b64encode(dumps({}))})

    def build_settings(self, settings):
        Logger.debug("%s: build_settings %s " % (APP, datetime.now()))
        # settings.add_json_panel('Planilla', self.config, 'settings.json')

    def on_pause(self):
        return True

    def on_resume(self):
        Logger.debug("%s: On resume %s" % (APP, datetime.now()))

    def on_new_intent(self, intent):
        Logger.debug("%s: on_new_intent %s %s" % (
            APP, datetime.now(), intent.toString()))

    def on_keypress(self, window, keycode1, keycode2, text, modifiers):
        # Logger.debug("%s: on_keypress k1: %s, k2: %s, text: %s, mod: %s" % (
        #     APP, keycode1, keycode2, text, modifiers))
        if keycode1 in [27, 1001]:
            if self._app_settings in self._app_window.children:
                self.close_settings()
                return True
            else:
                if platform == 'android':
                    activity.moveTaskToBack(True)
                return True
        return False

    def on_start(self):
        Logger.debug("%s: on_start %s" % (APP, datetime.now()))

        from kivy.core.window import Window
        Window.bind(on_keyboard=self.on_keypress)

        if platform == 'android':
            android.map_key(android.KEYCODE_BACK, 1001)

            import android.activity as python_activity
            python_activity.bind(on_new_intent=self.on_new_intent)
            # on_new_intent sólo se llama cuando la aplicación ya está
            # arrancada. Para no duplicar código la llamamos desde aquí
            self.on_new_intent(activity.getIntent())

        self.i = 0

        Clock.schedule_interval(self.add_item, 0.2)

    def add_item(self, *args):
        self.root.item_strings.append(str(self.i))
        self.i += 1

    def on_stop(self):
        pass

    def on_config_change(self, config, section, key, value):
        Logger.debug("%s: on_config_change key %s %s" % (
            APP, key, value))

    if platform == 'android':
        @run_on_ui_thread
        def toast(self, text="texto", short=True):
            Logger.debug("%s: texto %s, short %s" % (
                APP, text.encode('ascii', 'ignore'), short))
            Toast = autoclass('android.widget.Toast')
            Gravity = autoclass('android.view.Gravity')
            duration = Toast.LENGTH_SHORT if short else Toast.LENGTH_LONG
            t = Toast.makeText(activity, String(text), duration)
            t.setGravity(Gravity.BOTTOM, 0, 0)
            t.show()
    else:
        def toast(*args, **kwargs):
            pass

    def send_log(self):
        if platform != 'android':
            return
        Logger.debug("%s: send_log %s" % (APP, datetime.now()))

        from subprocess import Popen
        Uri = autoclass('android.net.Uri')
        File = autoclass('java.io.File')
        FileOutputStream = autoclass('java.io.FileOutputStream')
        Build = autoclass('android.os.Build')
        BV = autoclass('android.os.Build$VERSION')

        try:
            f = open("log.txt", "w")
            fa = File(activity.getExternalFilesDir(None), "log.txt")
            p1 = Popen(["/system/bin/logcat", "-d"], stdout=f)
            p1.wait()
            out = FileOutputStream(fa)
            f.close()
            f = open("log.txt", "r")
            out.write("".join(f.readlines()))
        except Exception as e:
            Logger.debug("%s: Log creation failed %s" % (APP, str(e)))
        finally:
            f.close()
            out.close()

        texto = "%s\n%s\n%s\n%s\n\n" % (
            Build.MANUFACTURER, Build.MODEL, BV.RELEASE, self.about())

        intent = Intent(Intent.ACTION_SEND).setType('message/rfc822')
        intent = intent.putExtra(Intent.EXTRA_TEXT, String(texto))
        intent = intent.putExtra(Intent.EXTRA_EMAIL, ["toledo+kbgallery@lazaro.es"])
        intent = intent.putExtra(Intent.EXTRA_SUBJECT, String("KBGallery Log"))
        try:
            intent = intent.putExtra(
                Intent.EXTRA_STREAM,
                cast('android.os.Parcelable', Uri.fromFile(fa)))

            activity.startActivity(Intent.createChooser(
                intent, String("Send Log with:")))
        except Exception as e:
            Logger.debug("%s: Log delivery failed %s" % (APP, str(e)))

    def about(self):
        try:
            with open("version.txt") as f:
                v = f.read()[:-1]
        except:
            v = "undefined"
        self.toast(text="KBGallery %s\nJuan Toledo" % v, short=False)
        return v

if __name__ == '__main__':
    Logger.debug("%s: End imports. %s KBGalleryApp().run()" % (
        APP, datetime.now()))
    KBGalleryApp().run()