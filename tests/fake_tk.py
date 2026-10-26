"""Tkinter & ttkbootstrap palsu untuk menguji lapisan GUI tanpa layar.

Lingkungan CI tidak punya server X, jadi modul ini mengganti ``tkinter``
dengan objek yang mencatat pemanggilan (geometri, konfigurasi, binding) tanpa
menggambar apa pun. Tujuannya bukan menguji piksel, melainkan memastikan semua
kode pembangunan UI benar-benar dieksekusi: tidak ada ``NameError``,
``AttributeError``, salah jumlah argumen, atau logika yang error saat resize.
"""

from __future__ import annotations

import sys
import types
from typing import Any, Callable, Dict, List, Optional


class TclError(Exception):
    """Tiruan ``tkinter.TclError``."""


class FakeVariable:
    def __init__(self, master=None, value: Any = None, name: str = "") -> None:
        self._value = value if value is not None else ""
        self._traces: List[Callable] = []

    def get(self) -> Any:
        return self._value

    def set(self, value: Any) -> None:
        self._value = value
        for trace in list(self._traces):
            trace("*", "", "write")

    def trace_add(self, mode: str, callback: Callable) -> str:
        self._traces.append(callback)
        return "trace-{}".format(len(self._traces))

    def trace_remove(self, *args) -> None:
        return None


class Widget:
    """Widget tiruan dengan semua method yang dipakai aplikasi."""

    def __init__(self, master: Optional["Widget"] = None, cnf: Any = None, **kwargs: Any) -> None:
        self.master = master
        self.children: List[Widget] = []
        self._options: Dict[str, Any] = {}
        if isinstance(cnf, dict):
            self._options.update(cnf)
        self._options.update(kwargs)
        self._bindings: Dict[str, List[Callable]] = {}
        self._exists = True
        self._manager: Optional[str] = None
        self._pack_info: Dict[str, Any] = {}
        self._grid_info: Dict[str, Any] = {}
        self._place_info: Dict[str, Any] = {}
        self._items: List[str] = []
        self._item_options: Dict[str, Dict[str, Any]] = {}
        self._text_content = ""
        self._focus = False
        if master is not None and hasattr(master, "children"):
            master.children.append(self)

    # -- konfigurasi ---------------------------------------------------- #
    def configure(self, cnf: Any = None, **kwargs: Any) -> None:
        if isinstance(cnf, dict):
            self._options.update(cnf)
        self._options.update(kwargs)

    config = configure
    def configure_item(self, *args, **kwargs) -> None:
        return None

    def cget(self, key: str) -> Any:
        if key in self._options:
            return self._options[key]
        return ""

    def __setitem__(self, key: str, value: Any) -> None:
        self._options[key] = value

    def __getitem__(self, key: str) -> Any:
        return self.cget(key)

    def keys(self) -> List[str]:
        return list(self._options)

    def option_add(self, pattern: str, value: Any) -> None:
        return None

    def configure_scroll(self, *args, **kwargs) -> None:
        return None

    # -- geometri -------------------------------------------------------- #
    def pack(self, cnf: Any = None, **kwargs: Any):
        self._manager = "pack"
        self._pack_info = dict(cnf or {}, **kwargs)
        return self

    def pack_configure(self, cnf: Any = None, **kwargs: Any):
        self._manager = "pack"
        self._pack_info.update(dict(cnf or {}, **kwargs))
        return self

    def pack_forget(self) -> None:
        self._manager = None

    def pack_propagate(self, flag: Any = None) -> None:
        return None

    def pack_slaves(self) -> List["Widget"]:
        return [child for child in self.children if child._manager == "pack"]

    def grid(self, cnf: Any = None, **kwargs: Any):
        self._manager = "grid"
        self._grid_info = dict(cnf or {}, **kwargs)
        return self

    def grid_configure(self, cnf: Any = None, **kwargs: Any):
        self._manager = "grid"
        self._grid_info.update(dict(cnf or {}, **kwargs))
        return self

    def grid_remove(self) -> None:
        self._manager = None

    def grid_forget(self) -> None:
        self._manager = None

    def grid_propagate(self, flag: Any = None) -> None:
        return None

    def grid_columnconfigure(self, index: Any, **kwargs: Any) -> None:
        return None

    def grid_rowconfigure(self, index: Any, **kwargs: Any) -> None:
        return None

    def place(self, cnf: Any = None, **kwargs: Any):
        self._manager = "place"
        self._place_info = dict(cnf or {}, **kwargs)
        return self

    def place_forget(self) -> None:
        self._manager = None

    def lift(self, *args) -> None:
        return None

    def lower(self, *args) -> None:
        return None

    # -- informasi ------------------------------------------------------- #
    def winfo_children(self) -> List["Widget"]:
        return list(self.children)

    def winfo_exists(self) -> int:
        return 1 if self._exists else 0

    def winfo_width(self) -> int:
        value = self._options.get("width", self._dimension())
        try:
            return int(value)
        except (TypeError, ValueError):
            return 100

    def winfo_height(self) -> int:
        value = self._options.get("height", 100)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 100

    def _dimension(self) -> int:
        return 100

    def winfo_reqwidth(self) -> int:
        return self.winfo_width()

    def winfo_reqheight(self) -> int:
        return self.winfo_height()

    def winfo_rootx(self) -> int:
        return 0

    def winfo_rooty(self) -> int:
        return 0

    def winfo_x(self) -> int:
        return 0

    def winfo_y(self) -> int:
        return 0

    def winfo_screenwidth(self) -> int:
        return 1920

    def winfo_screenheight(self) -> int:
        return 1080

    def winfo_ismapped(self) -> int:
        return 1

    def winfo_class(self) -> str:
        return type(self).__name__

    def nametowidget(self, name: str) -> "Widget":
        return self

    def cget_width(self) -> int:
        return self.winfo_width()

    # -- event ----------------------------------------------------------- #
    def bind(self, sequence: Optional[str] = None, func: Optional[Callable] = None, add: Any = None):
        if sequence is not None and func is not None:
            self._bindings.setdefault(sequence, []).append(func)
        return "binding"

    def unbind(self, sequence: str, funcid: Any = None) -> None:
        self._bindings.pop(sequence, None)

    def bind_all(self, sequence: Optional[str] = None, func: Optional[Callable] = None, add: Any = None):
        root = self._root()
        root._all_bindings.setdefault(sequence, []).append(func) if sequence and func else None
        return "binding"

    def unbind_all(self, sequence: str) -> None:
        self._root()._all_bindings.pop(sequence, None)

    def _root(self) -> "Widget":
        widget: Any = self
        while getattr(widget, "master", None) is not None:
            widget = widget.master
        return widget

    def event_generate(self, sequence: str, **kwargs: Any) -> None:
        return None

    def trigger(self, sequence: str) -> None:
        """Helper tes: jalankan binding pada widget ini."""
        for callback in self._bindings.get(sequence, []):
            callback(types.SimpleNamespace(widget=self, x=0, y=0, delta=0, num=0, keysym=""))

    def after(self, delay: int, callback: Optional[Callable] = None):
        root = self._root()
        identifier = "after-{}".format(len(getattr(root, "_after_queue", [])))
        root._after_queue.append((identifier, delay, callback))
        return identifier

    def after_idle(self, callback: Callable):
        return self.after(1, callback)

    def after_cancel(self, identifier: Any) -> None:
        root = self._root()
        root._after_queue = [item for item in root._after_queue if item[0] != identifier]

    def update_idletasks(self) -> None:
        return None

    def update(self) -> None:
        return None

    def destroy(self) -> None:
        self._exists = False
        for child in list(self.children):
            child.destroy()
        if getattr(self, "master", None) is not None:
            try:
                self.master.children.remove(self)
            except ValueError:  # pragma: no cover
                pass

    def focus_set(self) -> None:
        self._root()._focus = self

    def focus_force(self) -> None:
        self.focus_set()

    def focus_get(self) -> Optional["Widget"]:
        return getattr(self._root(), "_focus", None)

    def grab_set(self) -> None:
        return None

    def grab_release(self) -> None:
        return None

    def wait_window(self, window: Any = None) -> None:
        return None

    def transient(self, window: Any = None) -> None:
        return None

    def protocol(self, name: str, handler: Callable) -> None:
        return None

    def attributes(self, *args: Any) -> None:
        return None

    def title(self, text: Optional[str] = None) -> Optional[str]:
        if text is not None:
            self._options["title"] = text
        return self._options.get("title")

    def geometry(self, spec: Optional[str] = None) -> Optional[str]:
        if spec is not None:
            self._options["geometry"] = spec
        return self._options.get("geometry", "1180x780+0+0")

    wm_geometry = geometry

    def wm_overrideredirect(self, flag: Any = None) -> None:
        return None

    def wm_attributes(self, *args: Any) -> None:
        return None

    def wm_title(self, text: Optional[str] = None) -> Optional[str]:
        return self.title(text)

    def wm_minsize(self, width: int = 0, height: int = 0) -> None:
        return None

    def wm_transient(self, window: Any = None) -> None:
        return None

    def overrideredirect(self, flag: Any = None) -> None:
        return None

    def iconphoto(self, *args: Any, **kwargs: Any) -> None:
        return None

    def iconbitmap(self, *args: Any, **kwargs: Any) -> None:
        return None

    def minsize(self, width: int = 0, height: int = 0) -> None:
        return None

    def resizable(self, width: Any = None, height: Any = None) -> None:
        return None

    def withdraw(self) -> None:
        self._options["withdrawn"] = True

    def deiconify(self) -> None:
        self._options["withdrawn"] = False

    def state(self, *args: Any) -> str:
        return "normal"

    def mainloop(self, n: int = 0) -> None:
        return None

    def clipboard_clear(self) -> None:
        self._root()._clipboard = ""

    def clipboard_append(self, text: str) -> None:
        root = self._root()
        root._clipboard = getattr(root, "_clipboard", "") + text

    def grid_slaves(self) -> List["Widget"]:
        return [child for child in self.children if child._manager == "grid"]

    # -- teks / entry ---------------------------------------------------- #
    def insert(self, index: Any, text: str) -> None:
        self._text_content += str(text)
        variable = self._options.get("textvariable")
        if variable is not None and hasattr(variable, "get"):
            variable.set(self._text_content)

    def delete(self, first: Any = None, last: Any = None) -> None:
        if first == "all" or (first is None and last is None):
            self._items.clear()
            self._text_content = ""
        elif last is None:
            self._text_content = ""
        else:
            self._text_content = ""

    def get(self, first: Any = None, last: Any = None) -> str:
        variable = self._options.get("textvariable")
        if variable is not None and hasattr(variable, "get"):
            return str(variable.get())
        return self._text_content

    def select_range(self, *args: Any) -> None:
        return None

    def icursor(self, *args: Any) -> None:
        return None

    def see(self, *args: Any) -> None:
        return None

    def tag_add(self, *args: Any) -> None:
        return None

    def tag_config(self, *args, **kwargs) -> None:
        return None

    # -- canvas ---------------------------------------------------------- #
    def create_line(self, *args: Any, **kwargs: Any) -> str:
        return self._add_item("line", kwargs)

    def create_rectangle(self, *args: Any, **kwargs: Any) -> str:
        return self._add_item("rect", kwargs)

    def create_oval(self, *args: Any, **kwargs: Any) -> str:
        return self._add_item("oval", kwargs)

    def create_polygon(self, *args: Any, **kwargs: Any) -> str:
        return self._add_item("polygon", kwargs)

    def create_arc(self, *args: Any, **kwargs: Any) -> str:
        return self._add_item("arc", kwargs)

    def create_text(self, *args: Any, **kwargs: Any) -> str:
        return self._add_item("text", kwargs)

    def create_window(self, *args: Any, **kwargs: Any) -> str:
        return self._add_item("window", kwargs)

    def _add_item(self, kind: str, options: Dict[str, Any]) -> str:
        identifier = "{}{}".format(kind, len(self._items) + 1)
        self._items.append(identifier)
        self._item_options[identifier] = dict(options, _kind=kind)
        return identifier

    def delete_item(self, tag: str) -> int:
        return 0

    def itemconfigure(self, *args, **kwargs) -> None:
        return None

    itemconfig = itemconfigure

    def itemcget(self, item: str, key: str) -> Any:
        return self._item_options.get(item, {}).get(key, "")

    def find_all(self) -> List[str]:
        return list(self._items)

    def tag_lower(self, *tags: Any) -> None:
        return None

    def tag_raise(self, *tags: Any) -> None:
        return None

    def bbox(self, *args: Any) -> tuple:
        return (0, 0, 400, 600)

    def configure_canvas(self, **kwargs: Any) -> None:
        return None

    def yview(self, *args: Any) -> tuple:
        return (0.0, 1.0)

    def yview_scroll(self, number: int, what: str) -> None:
        return None

    def yview_moveto(self, fraction: float) -> None:
        return None

    def xview(self, *args: Any) -> tuple:
        return (0.0, 1.0)


class Canvas(Widget):
    def _dimension(self) -> int:
        return 100


class Tk(Widget):
    """Root window tiruan dengan lebar yang bisa diatur tes."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(None, **kwargs)
        self._width = 1180
        self._height = 780
        self._all_bindings: Dict[str, List[Callable]] = {}
        self._after_queue: List[tuple] = []
        self._clipboard = ""
        self._focus: Optional[Widget] = None

    def winfo_width(self) -> int:
        return self._width

    def winfo_height(self) -> int:
        return self._height

    def set_size(self, width: int, height: Optional[int] = None) -> None:
        self._width = width
        if height:
            self._height = height

    def run_after(self, limit: int = 100) -> int:
        """Jalankan callback ``after`` yang tertunda (untuk tes)."""
        executed = 0
        while self._after_queue and executed < limit:
            _identifier, _delay, callback = self._after_queue.pop(0)
            if callback is not None:
                callback()
            executed += 1
        return executed


def install() -> None:
    """Daftarkan modul palsu ke ``sys.modules``."""
    tkinter = types.ModuleType("tkinter")

    class PhotoImage(Widget):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(None)

    tkinter.PhotoImage = PhotoImage

    for name in (
        "Frame Label Button Canvas Entry Text Listbox Menu Menubutton Toplevel "
        "Checkbutton Radiobutton Scale Spinbox LabelFrame Scrollbar Message "
        "Widget Misc"
    ).split():
        setattr(tkinter, name, type(name, (Widget,), {}))

    tkinter.Tk = Tk
    tkinter.TclError = TclError
    tkinter.Variable = FakeVariable
    tkinter.StringVar = FakeVariable
    tkinter.IntVar = FakeVariable
    tkinter.DoubleVar = FakeVariable
    tkinter.BooleanVar = FakeVariable
    for constant in (
        "ROUND ARC LEFT RIGHT CENTER TOP BOTTOM X Y BOTH N S E W NW NE SW SE "
        "NSEW HORIZONTAL VERTICAL END NORMAL DISABLED ACTIVE"
    ).split():
        setattr(tkinter, constant, constant.lower())
    tkinter._support_default_root = True
    tkinter._default_root = None

    font_module = types.ModuleType("tkinter.font")
    font_module.families = lambda *args: [
        "DejaVu Sans",
        "DejaVu Sans Mono",
        "TkDefaultFont",
        "Segoe UI",
    ]

    class Font:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._args = args
            self._kwargs = kwargs

        def configure(self, **kwargs: Any) -> None:
            return None

        def actual(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {"family": "DejaVu Sans", "size": 10}

    font_module.Font = Font
    font_module.nametofont = lambda name: Font()
    tkinter.font = font_module

    ttk_module = types.ModuleType("tkinter.ttk")
    for name in (
        "Frame Label Button Entry Combobox Scrollbar Checkbutton Notebook Treeview "
        "Progressbar Separator Style Menubutton Panedwindow Sizegrip Spinbox "
        "Radiobutton Scale Labelframe OptionMenu"
    ).split():
        setattr(ttk_module, name, type(name, (Widget,), {}))

    class Style:
        def __init__(self, master: Any = None, **kwargs: Any) -> None:
            self.master = master
            self.theme = "fake"

        def configure(self, name: str, cnf: Any = None, **kwargs: Any) -> None:
            return None

        def map(self, name: str, query_opt: Any = None, **kwargs: Any) -> None:
            return None

        def theme_use(self, themename: Optional[str] = None) -> Optional[str]:
            if themename:
                self.theme = themename
            return self.theme

        def theme_names(self) -> tuple:
            return ("flatly", "darkly", "activity-light", "activitynight-dark")

        def element_create(self, *args: Any, **kwargs: Any) -> None:
            return None

    ttk_module.Style = Style
    tkinter.ttk = ttk_module

    filedialog = types.ModuleType("tkinter.filedialog")
    filedialog.asksaveasfilename = lambda **kwargs: ""
    filedialog.askopenfilename = lambda **kwargs: ""
    filedialog.askdirectory = lambda **kwargs: ""
    tkinter.filedialog = filedialog

    messagebox = types.ModuleType("tkinter.messagebox")
    messagebox.showinfo = lambda *args, **kwargs: "ok"
    messagebox.showerror = lambda *args, **kwargs: "ok"
    messagebox.showwarning = lambda *args, **kwargs: "ok"
    messagebox.askyesno = lambda *args, **kwargs: True
    tkinter.messagebox = messagebox

    ttkbootstrap = types.ModuleType("ttkbootstrap")
    ttkbootstrap.__version__ = "2.2.6"

    class BootstrapStyle(Style):
        instance = None

    ttkbootstrap.Style = BootstrapStyle

    class Theme:
        def __init__(self, **kwargs: Any) -> None:
            self.name = kwargs.get("name", "custom")
            self.kwargs = kwargs

        def register(self):
            return self

        def to_definitions(self) -> List[Any]:
            return []

    ttkbootstrap.Theme = Theme
    ttkbootstrap.App = Tk
    ttkbootstrap.Window = Tk
    ttkbootstrap.constants = types.ModuleType("ttkbootstrap.constants")

    sys.modules["_tkinter"] = types.ModuleType("_tkinter")
    sys.modules["tkinter"] = tkinter
    sys.modules["tkinter.font"] = font_module
    sys.modules["tkinter.ttk"] = ttk_module
    sys.modules["tkinter.filedialog"] = filedialog
    sys.modules["tkinter.messagebox"] = messagebox
    sys.modules["ttkbootstrap"] = ttkbootstrap
