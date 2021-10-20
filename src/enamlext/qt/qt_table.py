import contextlib
from abc import abstractmethod, ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Any, Union, Callable, List, Tuple, TypedDict

from PyQt5.QtCore import QItemSelection
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, QObject, QPoint, Signal
from qtpy.QtGui import QContextMenuEvent, QFont, QColor
from qtpy.QtWidgets import QApplication, QTableView, QMenu, QAction

# Contants
DEFAULT_ROW_HEIGHT = 23
DEFAULT_FONT_NAME = "Calibri"
DEFAULT_FONT_SIZE_PX = 13


class SelectionMode(Enum):
    SINGLE_CELL = auto()
    MULTI_CELLS = auto()
    SINGLE_ROW = auto()
    MULTI_ROWS = auto()


class Alignment(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


QT_ALIGNMENT_MAP = {
    Alignment.LEFT: int(Qt.AlignLeft | Qt.AlignVCenter),
    Alignment.CENTER: int(Qt.AlignCenter | Qt.AlignVCenter),
    Alignment.RIGHT: int(Qt.AlignRight | Qt.AlignVCenter),
}

QtAlignment = int


def to_qt_alignment(align: Alignment) -> QtAlignment:
    return QT_ALIGNMENT_MAP[align]


class CellStyle(TypedDict, total=False):
    color: Optional[QColor]
    background: Optional[QColor]


class Column:
    def __init__(self,
                 key: Union[str, Callable],
                 title: Optional[str] = None,
                 align: Alignment = Alignment.LEFT,
                 tooltip: Optional[Union[str, Callable]] = None,
                 # TODO: how to specify the types for the signature of the callback here?
                 cell_style: Optional[Callable] = None,
                 ):
        if callable(key):
            self.get_value = key  # we re-wire the get_value() here
        self.key = key
        self.title = title
        self.align = align
        self.tooltip = tooltip
        self.cell_style = cell_style

    def get_value(self, item: Any) -> Any:
        return getattr(item, self.key)

    def get_tooltip(self, table_context: "TableContext") -> str:
        if self.tooltip is not None:
            if callable(self.tooltip):
                return str(self.tooltip(table_context))  # TODO: is it a good practice to enforce str() here?
            else:
                return self.tooltip  # str

    def get_cell_style(self, table_context: "TableContext") -> Optional[CellStyle]:
        if self.cell_style is not None:
            return self.cell_style(table_context) or CellStyle()

    #
    # def get_align(self, item: Any) -> Alignment:
    #     return self.align


class QTableModel(QAbstractTableModel):
    def __init__(self,
                 columns: List[Column],
                 items: Optional[List] = None,
                 *,
                 checkable: bool = False,
                 parent: Optional[QObject] = None,
                 ):
        super().__init__(parent)
        self.columns = columns
        self.items = items
        self.checkable = checkable

    # QAbstractTableModel interface -----------------------------------------------------------------------------------

    def rowCount(self, parent: Optional[QModelIndex] = None) -> int:
        return len(self.items)  # O(1)

    def columnCount(self, parent: Optional[QModelIndex] = None) -> int:
        return len(self.columns) + int(self.checkable)  # O(1)

    def data(self, index: QModelIndex, role: int) -> Any:
        if role == Qt.DisplayRole:
            if self.checkable:
                offset = 1
            else:
                offset = 0
            if (col_index := index.column()) or not self.checkable:
                column = self.columns[col_index - offset]  # O(1)
                item = self.items[index.row()]  # O(1)
                return column.get_value(item)
        elif role == Qt.TextAlignmentRole:
            if self.checkable:
                offset = 1
            else:
                offset = 0
            if (col_index := index.column()) or not self.checkable:
                column = self.columns[col_index - offset]  # O(1)
                return to_qt_alignment(column.align)
        elif role == Qt.ToolTipRole:
            col_index = index.column()
            column = self.get_column_by_index(col_index)
            context = TableContext(
                model=self,
                index=index,
                role=role,
                column_index=col_index,
                column=column,
            )  # TODO: should we check if the column has a tooltip callback before creating this?
            return column.get_tooltip(context)
        elif role == Qt.CheckStateRole and self.checkable and index.column() == 0:
            return Qt.Checked
        elif role == Qt.FontRole:
            FONT = QFont(DEFAULT_FONT_NAME)
            FONT.setPixelSize(DEFAULT_FONT_SIZE_PX)
            return FONT
        elif role == Qt.ForegroundRole:
            col_index = index.column()
            column = self.get_column_by_index(col_index)
            if column.cell_style is not None:
                context = TableContext(
                    model=self,
                    index=index,
                    role=role,
                    column_index=col_index,
                    column=column,
                )
                return column.get_cell_style(context).get("color")


    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> str:
        if orientation == Qt.Horizontal:
            if self.checkable:
                offset = 1

                # TEMP
                if section == 0:
                    return
                # END OF TEMP
            else:
                offset = 0

            if role == Qt.DisplayRole:
                column = self.columns[section - offset]  # O(1)
                if column.title is not None:
                    return column.title
            elif role == Qt.TextAlignmentRole:
                column = self.columns[section - offset]  # O(1)
                return to_qt_alignment(column.align)

        return super().headerData(section, orientation, role)

    # QTableModel interface -------------------------------------------------------------------------------------------
    def get_column_by_index(self, index: int) -> Column:
        offset = 1 if self.checkable else 0
        return self.columns[max(index - offset, 0)]  # TODO: properly address checkable column here

    def get_item_by_index(self, index: int) -> Any:
        return self.items[index]


class DoubleClickContext:
    def __init__(self, index: QModelIndex, table: "QTable"):
        self.index = index
        self.__table = table

    @property
    def cell(self) -> Tuple[int, int]:
        return (self.row_index, self.column_index)

    @property
    def row_index(self) -> int:
        return self.index.row()

    @property
    def column_index(self) -> int:
        return self.index.column()

    @property
    def column(self) -> Column:
        model = self.__table.model()
        return model.get_column_by_index(self.column_index)

    @property
    def item(self) -> Any:
        model = self.__table.model()
        return model.get_item_by_index(self.row_index)

    @property
    def raw_value(self) -> Any:
        return self.column.get_value(self.item)

    @property
    def value(self) -> str:
        """ Returns the displayed value. """
        return self.column.get_displayed_value(self.item)  # TODO: should ask the column or should ask the model?


class QTable(QTableView):
    """
    A table has basically columns and a collection of items.
    """

    #: on_double_click signal is emited when doubleClicked signal is handled
    on_double_click: Signal = Signal(DoubleClickContext)

    def __init__(self,
                 columns: List[Column],
                 items: Optional[List] = None,
                 *,
                 checkable: bool = False,
                 context_menu: List["ContextMenuAction"] = None,
                 alternate_row_colors: bool = True,
                 parent: QObject = None):
        super().__init__(parent=parent)
        self.columns = columns
        if items is None:
            items = []
        self.items = items
        self.context_menu = context_menu
        self.setAlternatingRowColors(alternate_row_colors)
        self.doubleClicked.connect(self.on_double_clicked)
        model = QTableModel(self.columns, self.items, checkable=checkable)
        self.setModel(model)
        self.verticalHeader().setDefaultSectionSize(DEFAULT_ROW_HEIGHT)
        self.__updating = False  # sentinel
        # TODO: improve the way we update the internals - maybe offering a high-level function that gets everything
        #       that is internal and is possible of updating?
        #       Also, need to eliminate the duplication here - we should only work in terms of what's inside the model
        #       this will prevent from view and model getting out of sync

    @property
    def columns(self) -> List[Column]:
        return self._columns

    @columns.setter
    def columns(self, columns: List[Column]):
        self._columns = columns
        # refresh the model
        if self.model() is not None:
            self.model().columns = columns

    @property
    def items(self) -> List:
        return self._items

    @items.setter
    def items(self, items: List[Any]):
        self._items = items
        # refresh the model
        if self.model() is not None:
            self.model().items = items

    @property
    def checkable(self) -> bool:
        return self.model().checkable

    @checkable.setter
    def checkable(self, checkable: bool):
        self.model().checkable = checkable

    @contextlib.contextmanager
    def updating_internals(self):
        self.__updating = True
        try:
            self.model().beginResetModel()
            yield
        finally:
            self.__updating = False
            self.model().endResetModel()
            self.refresh()

    def refresh(self):
        self.model()
        pass

    def set_selection_mode(self, selection_mode: SelectionMode):
        if selection_mode == SelectionMode.SINGLE_CELL:
            self.setSelectionMode(self.SingleSelection)
            self.setSelectionBehavior(self.SelectItems)
        elif selection_mode == SelectionMode.MULTI_CELLS:
            self.setSelectionMode(self.MultiSelection)
            self.setSelectionBehavior(self.SelectItems)
        elif selection_mode == SelectionMode.SINGLE_ROW:
            self.setSelectionMode(self.SingleSelection)
            self.setSelectionBehavior(self.SelectRows)
        elif selection_mode == SelectionMode.MULTI_ROWS:
            self.setSelectionMode(self.MultiSelection)
            self.setSelectionBehaviour(self.SelectRows)

    # Header visibility controls

    def show_vertical_header(self):
        self.verticalHeader().show()

    def hide_vertical_header(self):
        self.verticalHeader().hide()

    def set_vertical_header_visible(self, visible: bool):
        self.verticalHeader().setVisible(visible)

    def show_horizontal_header(self):
        self.horizontalHeader().show()

    def hide_horizontal_header(self):
        self.horizontalHeader().hide()

    def set_horizontal_header_visible(self, visible: bool):
        self.horizontalHeader().setVisible(visible)

    # Context Menu

    def contextMenuEvent(self, event: QContextMenuEvent):
        if not self.context_menu:
            return

        context = MenuActionContext(pos=event.pos(), table=self)
        enabled_actions = [a for a in self.context_menu if a.is_enabled(context)]
        if enabled_actions:
            menu = QMenu(parent=self)
            for context_menu_action in enabled_actions:
                action = QAction(parent=menu)
                action.setText(context_menu_action.get_caption(context))

                def on_action_triggered(checked: bool = False, *, context_menu_action=context_menu_action):
                    return context_menu_action.execute(context)

                action.triggered.connect(on_action_triggered)
                menu.addAction(action)

            pos = self.mapToGlobal(event.pos())
            menu.exec_(pos)

    # Double Click

    def on_double_clicked(self, index: QModelIndex):
        """
        Function handler listening whenever Qt fires the doubleClicked event.
        """
        double_click_context = DoubleClickContext(index=index, table=self)
        self.on_double_click.emit(double_click_context)

    # Selection

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection):
        print("from selection model", [(i.row(), i.column()) for i in self.selectionModel().selectedIndexes()])
        print()
        print("selected", [(i.row(), i.column()) for i in selected.indexes()])
        print("deselected", [(i.row(), i.column()) for i in deselected.indexes()])
        print("current", (self.currentIndex().row(), self.currentIndex().column()))
        print()
        print()
        print()
        super().selectionChanged(selected, deselected)


class SelectionContext:
    def __init__(self, selected_indexes, added, removed):
        self.selected_indexes = selected_indexes
        self.added = added
        self.removed = removed



class TableContext:
    """
    Lazy evaluation of properties relative to the data request context.
    The Qt MVC calls the data() in table model, passing the roles...
    Depending on the role, we will call callbacks in the column to retrieve things like
    cell style, font style, tooltip, etc...
    We pass the object of TableContext to the callback, and everything there is
    calculated on demand... which hopefully makes it more efficient
    """

    def __init__(self,
                 model: QTableModel,
                 index: QModelIndex,
                 role: int,
                 column_index: int,
                 column: Column,
                 ):
        self.__model = model
        self.index = index
        self.role = role
        self.column_index = column_index
        self.column = column

    @property
    def row_index(self) -> int:
        return self.index.row()

    @property
    def item(self) -> Any:
        return self.__model.get_item_by_index(self.row_index)

    @property
    def raw_value(self) -> Any:
        return self.column.get_value(self.item)

    @property
    def value(self) -> str:
        """ Returns the displayed value. """
        return self.column.get_displayed_value(self.item)


class MenuActionContext:
    """
    This class represents what gets passed to the context menu actions (ContextMenuAction)
    when the user requests a context menu on the table (for example, by performing a right-click)
    """

    def __init__(self,
                 pos: QPoint,
                 table: QTable,
                 ):
        self.__table = table
        self.pos = pos

    @property
    def model(self) -> QTableModel:
        return self.__table.model()

    @property
    def index(self) -> QModelIndex:
        return self.__table.indexAt(self.pos)

    @property
    def row_index(self) -> int:
        return self.index.row()

    @property
    def column_index(self) -> int:
        return self.index.column()

    @property
    def item(self) -> Any:
        return self.model.get_item_by_index(self.row_index)

    @property
    def column(self) -> Column:
        return self.model.get_column_by_index(self.column_index)

    @property
    def raw_value(self) -> Any:
        return self.column.get_value(self.item)

    @property
    def value(self) -> str:
        """ Returns the displayed value. """
        return self.column.get_displayed_value(self.item)


class ContextMenuAction(ABC):
    @abstractmethod
    def is_enabled(self, context: MenuActionContext) -> bool:
        pass

    @abstractmethod
    def get_caption(self, context: MenuActionContext) -> bool:
        pass

    @abstractmethod
    def execute(self, context: MenuActionContext):
        pass


def debug_trace():
    """
    Set a tracepoint in the Python debugger that works with Qt
    """
    import pdb
    import sys
    from PyQt5.QtCore import pyqtRemoveInputHook
    pyqtRemoveInputHook()
    # set up the debugger
    debugger = pdb.Pdb()
    debugger.reset()
    # custom next to get outside of function scope
    debugger.do_next(None)  # run the next command
    users_frame = sys._getframe().f_back  # frame where the user invoked `pyqt_set_trace()`
    debugger.interaction(users_frame, None)

    # TODO: should call QtCore.pyqtRestoreInputHook() ?


if __name__ == '__main__':
    # Making Ctrl+C work
    import signal

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Fixing PyQt issue on MacOS BigSur
    import os

    os.environ["QT_MAC_WANTS_LAYER"] = "1"

    app = QApplication([])


    def tooltip_callback(table_context: TableContext) -> str:
        item = table_context.item
        return f"{item.name} is {item.age} years old"


    def age_cell_style(table_context: TableContext) -> CellStyle:
        if table_context.item.age > 30:
            return CellStyle(color=QColor(200, 20, 100))

    columns = [
        Column("name", title="Name"),
        Column("age", align=Alignment.RIGHT, tooltip=tooltip_callback,
               cell_style=age_cell_style)
    ]


    @dataclass
    class Person:
        name: str
        age: int
        sex: str


    items = [
                Person(name="John", age=33, sex="M"),
                Person(name="Pam", age=22, sex="F"),
            ] * 10


    def echo_factory(n: int) -> ContextMenuAction:
        class EchoAction(ContextMenuAction):
            def is_enabled(self, context):
                return True

            def get_caption(self, context):
                return f"Echo {n}"

            def execute(self, context):
                print(f"Echo {n} - Cell: ({context.row_index}, "
                      f"{context.column_index}) has value: {context.raw_value!r}")

        return EchoAction()


    context_menu_actions = [
        *(echo_factory(n) for n in range(1, 11)),
    ]

    table = QTable(columns, items, checkable=True, context_menu=context_menu_actions)
    table.set_selection_mode(SelectionMode.MULTI_CELLS)
    # table.set_selection_mode(SelectionMode.SINGLE_ROW)
    table.show()
    table.set_vertical_header_visible(False)
    table.show_horizontal_header()


    # table.setStyleSheet("background-color: rgb(255, 255, 245); alternate-background-color: rgb(220,200,220);")

    def double_click_callback(context: DoubleClickContext):
        print(f"Double click happened:",
              f"  cell = {context.cell}",
              f"  column = {context.column}",
              f"  raw_value = {context.raw_value}",
              sep="\n")


    table.on_double_click.connect(double_click_callback)

    app.exec_()
