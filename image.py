import errno
from os import makedirs, lstat, unlink
from zlib import crc32
from shutil import rmtree
from os.path import join, dirname
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.uix.image import AsyncImage
from kivy.uix.floatlayout import FloatLayout
from kivy.network.urlrequest import UrlRequest

APP = "KBImage"

Builder.load_string('''
<CachedImage>:
    image: image
    RotImage:
        id: image
        x: root.x
        y: root.y
        orientation: root.orientation

<RotImage>:
    angle: 0
    orientation: 1
    color: [0, 0, 0, 1]
    nocache: True
    canvas.before:
        PushMatrix
        Rotate:
            angle:root.angle
            axis: 0, 0, 1
            origin: root.center
    canvas.after:
        PopMatrix
''')

cache_root = ".kbimgcache"


def set_cache_dir(root):
    global cache_root
    cache_root = root


def get_cache_dir():
    return cache_root


def clear_cache():
    try:
        rmtree(cache_root)
        Logger.info("%s: Cleared cache dir %s" % (APP, cache_root))
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


class RotImage(AsyncImage):
    angle = NumericProperty(0)
    orientation = NumericProperty(1)

    def __init__(self, **kwargs):
        self.previous_orientation = 1
        super(RotImage, self).__init__(**kwargs)

    def on_orientation(self, widget, value):
        self.angle = {1: 0, 3: 180, 6: 270, 8: 90}[value]
        p, n = self.previous_orientation, value  # previous, new
        w, h = self.width, self.height
        if (p, n) in [(1, 6), (1, 8), (3, 6), (3, 8),
                      (6, 1), (6, 3), (8, 1), (8, 3)]:
            self.width, self.height = h, w
        self.previous_orientation = value

    def _on_source_load(self, value):
        super(RotImage, self)._on_source_load(value)
        self.color = [1, 1, 1, 1]
        self.allow_stretch = True


class CachedImage(FloatLayout):
    x = NumericProperty()
    y = NumericProperty()
    angle = NumericProperty(0)
    orientation = NumericProperty(1)
    source = StringProperty("", allownone=True)
    image = ObjectProperty()

    def __init__(self, **kwargs):
        super(CachedImage, self).__init__(**kwargs)
        self.on_source(self, self.source)

    def on_source(self, widget, source):
        if not source or not self.image:
            return
        fn = "{0:x}.jpg".format(crc32(source) & 0xffffffff)
        self.fn = fn = join(cache_root, fn[:2], fn)
        try:
            open(fn)  # Keep for reference: getattr(os.lstat(fn), 'st_size')
            self.image.source = fn
        except:
            try:
                makedirs(dirname(fn))
            except OSError as exception:
                if exception.errno != errno.EEXIST:
                    raise
            UrlRequest(url=source, on_success=self.img_downloaded, file_path=fn,
                       on_failure=self.cleanup, on_error=self.cleanup)

    def img_downloaded(self, req, res):
        Logger.debug("%s: img_downloaded %s %s" % (APP, req, res))
        self.image.source = self.fn

    def cleanup(self, *args):
        try:
            unlink(self.fn)
        except:
            pass
