# -*- coding: utf-8 -*-
from urllib import quote
from posixpath import join as urljoin
from itertools import islice, izip
from json import loads

from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.event import EventDispatcher
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.listview import ListView
from kivy.uix.carousel import Carousel
from kivy.adapters.listadapter import ListAdapter
from kivy.network.urlrequest import UrlRequest

from image import CachedImage

APP = 'KBContentList'
DIR = 'dir'
FILE = 'file'


Builder.load_string('''
<Direntry@ButtonBehavior+FloatLayout>:
    text: ''
    source: None
    orientation: 1
    CachedImage:
        x: root.x
        y: root.y
        source: root.source
        orientation: root.orientation
    Label:
        pos_hint: {'center_x': 0.5, 'y': 0}
        text_size: (root.width, None)
        text: root.text
        size: self.texture_size
        size_hint: (None, None)
    Label:
        pos_hint: {'center_x': 0.5, 'top': 1}
        text_size: (root.width, None)
        text: str(root.orientation)
        size: self.texture_size
        size_hint: (None, None)

<DirlistRow>:
    size_hint_y: None
    height: 240
    Direntry:
        text: root.dir1
        source: root.thumb1
        orientation: root.orientation1
        on_release: root.direntry_selected(root.dir1)
    Direntry:
        text: root.dir2
        source: root.thumb2
        orientation: root.orientation2
        on_release: root.direntry_selected(root.dir2)

<ImglistRow>:
    size_hint_y: None
    height: 160
    Direntry:
        text: root.f1
        source: root.t1
        orientation: root.o1
        on_release: root.img_selected(root.f1)
    Direntry:
        text: root.f2
        source: root.t2
        orientation: root.o2
        on_release: root.img_selected(root.f2)
    Direntry:
        text: root.f3
        source: root.t3
        orientation: root.o3
        on_release: root.img_selected(root.f3)
''')


def pad_modulo(list, padding, modulo):
    length_modulo = len(list) % modulo
    if length_modulo in (0, modulo):
        return list
    else:
        return list + padding * (modulo - length_modulo)


def group(lst, n):
    """group([0,3,4,10,2,3], 2) => iterator

    Group an iterable into an n-tuples iterable. Incomplete tuples
    are discarded e.g.

    >>> list(group(range(10), 3))
    [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
    """
    return izip(*[islice(lst, i, None, n) for i in range(n)])


_direntries = []


def get_direntries(res):
        # TODO Fix this if we want to be able to handle to requests
        # at the same time
        global _direntries
        direntries = []
        sdir = None
        for l in res.split("\n"):
            try:
                d = loads(l)
                try:
                    sdir = d['dir']  # Server dir
                except:
                    # If we get a partial result, only append
                    # the new direntries
                    if d not in _direntries:
                        direntries.append(d)
                        _direntries.append(d)
            except:
                pass
        return sdir, direntries


class ImageDir(FloatLayout, EventDispatcher):

    __events__ = ('on_navigate_down', 'on_navigate_top', 'on_img_selected')

    def __init__(self, server_url, root="", path="", **kwargs):

        self.navigation = []
        self.server_url = server_url

        # Currently displayed content widget (dirlist, imglist)
        self._path = ""        # The path under the server root of the dirlist
        self._direntries = []  # The direntries already received
        self.content = None   # The Dirlist widget currently displayed

        super(ImageDir, self).__init__(**kwargs)

        self.fetch_dir(path='')

    def fetch_dir(self, path=''):  # Server dir
        root = self.server_url
        self._path = path = quote((path).encode('utf-8'))
        self.req = UrlRequest(urljoin(root, path, ''),
                              on_success=self.got_dirlist,
                              debug=True)
        self.req.cancel = False

    def got_dirlist(self, req, res):
        Logger.debug("%s: got_dirlist (req %s, results %s" % (APP, req, res))
        if req.cancel:
            return

        # TODO in partial results sdir may be None
        sdir, direntries = get_direntries(res)
        print sdir, direntries

        directories = [de for de in direntries if de[2] == DIR]
        files = [de for de in direntries if de[2] == FILE]

        turl = self.server_url + urljoin('thumb',
                                         quote(sdir.encode('utf-8')))
        if len(directories):
            listclass = Dirlist
            listing = directories
            cols = 2
            arg_dict = {'direntry_selected': self.direntry_selected}
        elif len(files):
            listclass = Imglist
            listing = files
            cols = 3
            arg_dict = {'img_selected': self.img_selected}
        else:
            Logger.warning("Empty directory %s" % urljoin(self._path, sdir))
            return

        ld = [dict(arg_dict.items() +
                   {'direntry': de,
                    'thumb_url': urljoin(turl,
                                         quote(de.encode('utf-8')+'.jpg')),
                    'orientation': orientation}.items())
              for (de, orientation, file_type) in listing]
        ld = pad_modulo(ld, [{'direntry': '', 'thumb_url': '',
                             'orientation': 1}], cols)

        data = group(ld, cols)
        listwidget = listclass(root=self.server_url, path=self._path)
        listwidget.adapter.data = data
        listwidget._reset_spopulate()

        self.add_widget(listwidget)
        self.content = listwidget

        # Finally, when we get the full results
        self._direntries = []

    def direntry_selected(self, direntry):
        Logger.debug("%s: on_direntry_selected %s" % (APP, direntry))

        # TODO Cancelar los requests anteriores si posible
        # El servidor se puede quedar pillado haciendo thumbnails
        # antes de responder al cambio de directorio

        self.remove_widget(self.content)
        self.navigation.append(self.content)
        self.fetch_dir(path=urljoin(self.content.path, direntry, ''))
        self.dispatch('on_navigate_down')

    def img_selected(self, direntry):
        fn = urljoin(self.content.path, direntry)
        Logger.debug("%s: img_selected %s" % (APP, fn))
        self.dispatch('on_img_selected', self.content.path, direntry)

        # TODO Cancelar los requests anteriores si posible
        # El servidor se puede quedar pillado haciendo thumbnails
        # antes de responder al cambio de directorio

        # self.root.container.remove_widget(self.dirlist)
        # self.navigation.append(self.dirlist)
        # self.fetch_dir(path=urljoin(self.dirlist.path, direntry, ''))
        # self.root.with_previous = True

    def reload(self):
        try:
            if type(self.content) in (Imglist, Dirlist):
                pass
        except Exception as e:
            Logger.error("%s: Unable to reload content: %s" % (APP, e))

    def load_previous(self):
        try:
            previous = self.navigation.pop(-1)
            self.req.cancel = True
            self.remove_widget(self.content)
            self.add_widget(previous)
            self.content = previous
        except IndexError:
            pass

        if not len(self.navigation):
            self.dispatch('on_navigate_top')

    def on_navigate_down(self):
        pass

    def on_navigate_top(self):
        pass

    def on_img_selected(self, url):
        pass


class ImglistRow(BoxLayout):
    f1 = StringProperty()  # Filepath 1, 2, 3
    f2 = StringProperty()
    f3 = StringProperty()
    t1 = StringProperty()  # Thumbpath 1, 2, 3
    t2 = StringProperty()
    t3 = StringProperty()
    o1 = NumericProperty(1)  # Orientation 1, 2, 3
    o2 = NumericProperty(1)
    o3 = NumericProperty(1)
    img_selected = ObjectProperty()


class Imglist(ListView):

    def __init__(self, root="", path="", **kwargs):

        self.path = path

        def args_converter(row_index, rec):
            return {'f1': rec[0]['direntry'],
                    'f2': rec[1]['direntry'],
                    'f3': rec[2]['direntry'],
                    't1': rec[0]['thumb_url'],
                    't2': rec[1]['thumb_url'],
                    't3': rec[2]['thumb_url'],
                    'o1': rec[0]['orientation'],
                    'o2': rec[1]['orientation'],
                    'o3': rec[2]['orientation'],
                    'img_selected': rec[0]['img_selected']
                    }

        self.adapter = adapter = ListAdapter(
            data=[],
            args_converter=args_converter,
            cls=ImglistRow,
            selection_mode='none'
            )

        super(Imglist, self).__init__(adapter=adapter, **kwargs)


class DirlistRow(BoxLayout):
    dir1 = StringProperty()
    dir2 = StringProperty()
    thumb1 = StringProperty()
    thumb2 = StringProperty()
    orientation1 = NumericProperty(1)
    orientation2 = NumericProperty(1)
    direntry_selected = ObjectProperty()


class Dirlist(ListView):

    def __init__(self, root="", path="", **kwargs):

        self.path = path

        def args_converter(row_index, rec):
            return {'dir1': rec[0]['direntry'],
                    'dir2': rec[1]['direntry'],
                    'thumb1': rec[0]['thumb_url'],
                    'thumb2': rec[1]['thumb_url'],
                    'orientation1': rec[0]['orientation'],
                    'orientation2': rec[1]['orientation'],
                    'direntry_selected': rec[0]['direntry_selected']}

        self.adapter = adapter = ListAdapter(
            data=[],
            args_converter=args_converter,
            cls=DirlistRow,
            selection_mode='none'
            )

        super(Dirlist, self).__init__(adapter=adapter, **kwargs)


class ImageCarousel(Carousel):
    path = StringProperty("")
    server_url = StringProperty("")

    def on_path(self, widget, path):
        self.clear_widgets()
        req = UrlRequest(urljoin(self.server_url, path, ""),
                         on_success=self.got_dir)

    def got_dir(self, req, res):
        #import pdb; pdb.set_trace()
        sdir, direntries = get_direntries(res)

        files = [de for de in direntries if de[2] == FILE]

        turl = self.server_url + urljoin('thumb',
                                         quote(sdir.encode('utf-8')), '')
        for (fn, orientation, file_type) in files:
            self.add_widget(
                CachedImage(source=turl + quote(fn.encode('utf-8') + '.jpg'),
                            orientation=orientation))