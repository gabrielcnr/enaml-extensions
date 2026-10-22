import contextlib
import csv
import itertools
import logging
import math
import operator
import time
import warnings
import weakref
from abc import ABC, abstractmethod
from collections.abc import Collection, Iterable, Iterator
from dataclasses import dataclass
from enum import Enum, auto
from functools import lru_cache
from io import StringIO
from typing import Any, NamedTuple, cast

from qtpy.QtCore import (
    QAbstractTableModel,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    QPoint,
    Qt,
    Signal,
)
from qtpy.QtGui import QColor, QContextMenuEvent, QFont, QKeyEvent, QKeySequence, QMouseEvent, QPaintEvent, QPixmap
from qtpy.QtWidgets import (
    QAbstractItemView,
    QAction,
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

# Constants
from enamlext.qt.table.column import AUTO_ALIGN, Alignment, Column
from enamlext.qt.table.defs import CellStyle
from enamlext.qt.table.filtering import Filter, TableFilters
from enamlext.qt.table.table_context import TableContext

logger = logging.getLogger(__name__)

DEFAULT_ROW_HEIGHT = 23
DEFAULT_FONT_NAME = 'Calibri'
DEFAULT_FONT_SIZE_PX = 13

CHECKBOX_FLAG = (
    Qt.ItemFlag.ItemNeverHasChildren
    | Qt.ItemFlag.ItemIsEditable
    | Qt.ItemFlag.ItemIsUserCheckable
    | Qt.ItemFlag.ItemIsEnabled
)


RED = QColor(Qt.GlobalColor.red)


class SelectionMode(Enum):
    SINGLE_CELL = auto()
    MULTI_CELLS = auto()
    SINGLE_ROW = auto()
    MULTI_ROWS = auto()


QT_SELECTION = {
    SelectionMode.SINGLE_CELL: (
        QAbstractItemView.SelectionMode.SingleSelection,
        QAbstractItemView.SelectionBehavior.SelectItems,
    ),
    SelectionMode.MULTI_CELLS: (
        QAbstractItemView.SelectionMode.ExtendedSelection,
        QAbstractItemView.SelectionBehavior.SelectItems,
    ),
    SelectionMode.SINGLE_ROW: (
        QAbstractItemView.SelectionMode.SingleSelection,
        QAbstractItemView.SelectionBehavior.SelectRows,
    ),
    SelectionMode.MULTI_ROWS: (
        QAbstractItemView.SelectionMode.ExtendedSelection,
        QAbstractItemView.SelectionBehavior.SelectRows,
    ),
}


QT_ALIGNMENT_MAP = {
    Alignment.LEFT: int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
    Alignment.CENTER: int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter),
    Alignment.RIGHT: int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
}

QtAlignment = int


def to_qt_alignment(align: Alignment) -> QtAlignment:
    return QT_ALIGNMENT_MAP[align]


@lru_cache(maxsize=128)
def _load_scaled_pixmap(image_path: str, max_size: int = 24) -> QPixmap:
    # Cached so DecorationRole doesn't read the file from disk and rescale on
    # every repaint. Must only be called from the GUI thread (QPixmap requires
    # it), which is fine because QAbstractItemModel.data() always runs there.
    img = QPixmap()
    img.load(image_path)
    if img.height() > max_size:
        img = img.scaledToHeight(max_size)
    if img.width() > max_size:
        img = img.scaledToWidth(max_size)
    return img


@lru_cache(maxsize=256)
def make_custom_font(font_spec: str) -> QFont:
    font = QFont()
    tokens = font_spec.split()

    if 'bold' in tokens:
        font.setBold(True)
        tokens.remove('bold')

    if 'italic' in tokens:
        font.setItalic(True)
        tokens.remove('italic')

    if 'underline' in tokens:
        font.setItalic(True)
        tokens.remove('underline')

    for token in tokens[:]:
        if token.endswith('px'):
            font.setPixelSize(int(token[:-2]))
            tokens.remove(token)
            break
        if token.endswith('pt'):
            font.setPointSize(int(token[:-2]))
            tokens.remove(token)
            break

    # everything else must be the font family
    if tokens:
        family = ' '.join(tokens)
        font.setFamily(family)

    return font


class Cell(NamedTuple):
    row: int
    column: int


def default_convert_item(item):
    return item


class QTableModel(QAbstractTableModel):
    #: signal used to notify the view whenever checked_items changes
    on_checked_items: Signal = Signal(set)

    def __init__(
        self,
        columns: list[Column],
        items: list[Any] | None = None,
        *,
        checkable: bool = False,
        checked_items: Collection[Any] | None = None,
        parent: QObject | None = None,
        error_handling: str = 'graceful',  # TODO: other modes
        convert_item=default_convert_item,
    ):
        super().__init__(parent)
        self.columns = columns
        self._original_items: Iterable[Any] = [] if items is None else items
        self.checkable = checkable
        self.error_handling = error_handling
        if convert_item is None:
            convert_item = default_convert_item
        self.convert_item = convert_item

        # Filtering
        self._filtered_items: list[Any] = []
        self.filters = TableFilters()
        self._apply_filters()

        # Internally we keep track of which items are checked using a set
        if checked_items is None:
            checked_items = set()
        if not isinstance(checked_items, set):
            warnings.warn(
                f'QTableModel checked_items is recommend to be a '
                f'set, but got: {type(checked_items).__name__} instead - coercing to set',
                stacklevel=2,
            )
            checked_items = set(checked_items)
        self.checked_items = checked_items

        self._font = self._create_font()  # cache the font
        self._font_bold = self._create_font(bold=True)

        self._last_sorting_column: tuple[Column, int, Qt.SortOrder] | None = None

        self._cell_style_cache: dict | None = None

    def __len__(self):
        return len(self.items)  # O(1)

    # QAbstractTableModel interface -----------------------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self.items)  # O(1)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self.columns) + int(self.checkable)  # O(1)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        column_index = index.column()
        if column_index == 0 and self.checkable:
            return CHECKBOX_FLAG
        return super().flags(index)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        column = self.get_column_by_index(index.column())
        if column.collect_stats:
            t0 = time.perf_counter()
            result = self._data(index, role)
            t1 = time.perf_counter()
            column.record_stats(role=role, elapsed=t1 - t0)
            return result
        return self._data(index, role)

    def _data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            offset = 1 if self.checkable else 0
            if (col_index := index.column()) or not self.checkable:
                column = self.columns[col_index - offset]  # O(1)
                item = self.items[index.row()]  # O(1)
                return column.get_displayed_value(item)
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            offset = 1 if self.checkable else 0
            # Only the first column is checkable (index = 0) - so we need to account for that offset
            if (col_index := index.column()) or not self.checkable:
                column = self.columns[col_index - offset]  # O(1)
                # Fast path: fixed-align (or already-resolved AUTO_ALIGN) columns
                # don't need the row item — skip fetching/converting it on every cell.
                if (align := column.get_align_quick()) is not None:
                    return to_qt_alignment(align)
                item = self.convert_item(self.items[index.row()])  # O(1)
                try:
                    return to_qt_alignment(column.get_align(item))
                except Exception as exc:
                    if self.error_handling == 'graceful':
                        logger.warning(
                            'Error when resolving alignment for column: col_index = %r, '
                            'column.title = %r, index.row() = %r, exc = %r',
                            col_index,
                            column.title,
                            index.row(),
                            exc,
                        )
                    else:
                        raise
        elif role == Qt.ItemDataRole.ToolTipRole:
            col_index = index.column()
            column = self.get_column_by_index(col_index)
            context = TableContext(
                model=self,
                index=index,
                role=role,
                column_index=col_index,
                column=column,
                convert=self.convert_item,
            )  # TODO: should we check if the column has a tooltip callback before creating this?
            return column.get_tooltip(context)
        elif role == Qt.ItemDataRole.CheckStateRole and self.checkable and index.column() == 0:
            # TODO: think about using the check state of the vertical header to control checked items
            #       what if we want to have more than 1 column that is checkable?
            #       should we keep a collection of checked items separately or should we consider wrapping each
            #       item in a wrapper object that holds the checked state? how about a proxy object?
            item = self.items[index.row()]  # O(1)
            if item in self.checked_items:
                return Qt.CheckState.Checked
            return Qt.CheckState.Unchecked
        elif role == Qt.ItemDataRole.FontRole:
            col_index = index.column()
            column = self.get_column_by_index(col_index)
            if column.cell_style is not None:
                try:
                    style = self._get_cell_style(index, role, col_index, column)
                    if style is not None and (font_spec := style.get('font')) is not None:
                        return make_custom_font(font_spec)
                except Exception as exc:
                    if self.error_handling == 'graceful':
                        logger.warning(
                            'Error when resolving font for column: col_index = %r, '
                            'column.title = %r, index.row() = %r, exc = %r',
                            col_index,
                            column.title,
                            index.row(),
                            exc,
                        )
                    else:
                        raise

            return self._font

        elif role == Qt.ItemDataRole.ForegroundRole:
            col_index = index.column()
            column = self.get_column_by_index(col_index)
            if column.cell_style is not None:
                try:
                    style = self._get_cell_style(index, role, col_index, column)
                    if style is not None:
                        return style.get('color')
                except Exception as exc:
                    if self.error_handling == 'graceful':
                        logger.warning(
                            'Error when resolving foreground colour style for column: col_index = %r, '
                            'column.title = %r, index.row() = %r, exc = %r',
                            col_index,
                            column.title,
                            index.row(),
                            exc,
                        )
                    else:
                        raise

        elif role == Qt.ItemDataRole.BackgroundRole:
            col_index = index.column()
            column = self.get_column_by_index(col_index)
            if column.cell_style is not None:
                try:
                    style = self._get_cell_style(index, role, col_index, column)
                    if style is not None:
                        return style.get('background')
                except Exception as exc:
                    if self.error_handling == 'graceful':
                        logger.warning(
                            'Error when resolving background colour style for column: col_index = %r, '
                            'column.title = %r, index.row() = %r, exc = %r',
                            col_index,
                            column.title,
                            index.row(),
                            exc,
                        )
                    else:
                        raise

        elif role == Qt.ItemDataRole.DecorationRole:  # TODO: refactor (DRY)
            col_index = index.column()
            column = self.get_column_by_index(col_index)
            if column.image is not None:
                context = TableContext(
                    model=self,
                    index=index,
                    role=role,
                    column_index=col_index,
                    column=column,
                    convert=self.convert_item,
                )
                if image := column.get_image(context):
                    return _load_scaled_pixmap(image)

    def _get_cell_style(self, index: QModelIndex, role: int, col_index: int, column: Column) -> CellStyle | None:
        key = (index.row(), col_index)
        cache = self._cell_style_cache
        if cache is not None and key in cache:
            return cache[key]
        context = TableContext(
            model=self,
            index=index,
            role=role,
            column_index=col_index,
            column=column,
            convert=self.convert_item,
        )
        style = column.get_cell_style(context)
        if cache is not None:
            cache[key] = style
        return style

    @contextlib.contextmanager
    def caching_cell_styles(self):
        self._cell_style_cache = {}
        try:
            yield
        finally:
            self._cell_style_cache = None

    def sort(self, column_index, order=None) -> None:
        if self.columns:
            # TODO: instead of relying on column (positional) index we should
            #       be keeping a referencing to the column and improve
            #       Column identity and equality comparison to restore sorting
            column = self.columns[column_index]
            self._last_sorting_column = column, column_index, order
            self._apply_sorting()

    def _apply_sorting(self):
        if self._last_sorting_column is not None:
            previous_column, column_index, order = self._last_sorting_column
            try:
                column = self.columns[column_index]
            except IndexError:
                # TODO: we should still try to find if the column is there in another index
                return
            else:
                if column.title != previous_column.title:
                    # not very likely to be the same column - avoid sorting incorrectly
                    return
            self.beginResetModel()

            def sort_key(item):
                value = column.get_value(item)
                if isinstance(value, float) and math.isnan(value):
                    return float('-inf')
                return value

            descending = order == Qt.SortOrder.DescendingOrder  # Qt6 enums are not ints, so never truth-test them
            self._filtered_items = sorted(self._filtered_items, key=sort_key, reverse=descending)
            self.endResetModel()

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if index.column() == 0 and role == Qt.ItemDataRole.CheckStateRole and self.checkable:
            item = self.items[index.row()]
            if value == Qt.CheckState.Checked:
                self.checked_items.add(item)
                self.on_checked_items.emit(self.checked_items)
                return True
            if value == Qt.CheckState.Unchecked:
                self.checked_items.discard(item)
                self.on_checked_items.emit(self.checked_items)
                return True

        return False

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal:
            if self.checkable:
                offset = 1

                # TEMP
                if section == 0:
                    return None
                # END OF TEMP
            else:
                offset = 0

            if role == Qt.ItemDataRole.DisplayRole:
                column = self.columns[section - offset]  # O(1)
                if column.title is not None:
                    return column.title
            elif role == Qt.ItemDataRole.TextAlignmentRole:
                column = self.columns[section - offset]  # O(1)
                if len(self):
                    align = column.get_align(self.items[0])
                elif column.align is AUTO_ALIGN:
                    align = Alignment.LEFT
                else:
                    align = column.align
                return to_qt_alignment(align)
            elif role == Qt.ItemDataRole.ForegroundRole:
                column = self.columns[section - offset]  # O(1)
                if column in self.filters:
                    return RED

            elif role == Qt.ItemDataRole.FontRole:
                column = self.columns[section - offset]  # O(1)
                if column in self.filters:
                    return self._font_bold

        return super().headerData(section, orientation, role)

    # QTableModel interface -------------------------------------------------------------------------------------------
    def get_column_by_index(self, index: int) -> Column:
        offset = 1 if self.checkable else 0
        return self.columns[max(index - offset, 0)]  # TODO: properly address checkable column here

    def get_item_by_index(self, index: int) -> Any:
        return self.items[index]

    def get_cell_value(self, row_index: int, column_index: int) -> Any:
        if column_index or not self.checkable:
            column = self.columns[column_index]  # O(1)
            item = self.items[row_index]  # O(1)
            return column.get_value(item)

    @property
    def items(self) -> list[Any]:
        """read from the filtered items"""
        return self._filtered_items

    @items.setter
    def items(self, items: Iterable[Any]) -> None:
        """write to the original items (not filtered)"""
        self._original_items = items
        self._apply_filters()
        try:
            self._apply_sorting()
        except (IndexError, KeyError) as exc:
            logger.warning('It was not possible to re-apply the sorting configuration: %r', exc)

    def set_filter(self, column: Column, expression: str) -> None:
        self.filters.add_filter(Filter(column, expression))
        self._apply_filters()

    def _apply_filters(self) -> None:
        self.beginResetModel()
        self.refresh_filtered_items()
        self.endResetModel()

    def clear_filters(self):
        self.filters.clear()
        self._apply_filters()

    def refresh_filtered_items(self) -> None:
        """
        the problem here is that when we are applying the filters we are
        creating a new list - can we do that better?
        instead we could keep the items inside a proxy object which
        holds an internal mapping for the indexes
        (index in the original items -> index in the filtered items)
        """
        if self.filters:
            self._filtered_items = list(self.filters.filter_items(self._original_items))  # TODO: we really want a list?
        else:
            # Keep the caller's sequence (e.g. a DataFrameProxy) rather than copying it.
            self._filtered_items = cast('list[Any]', self._original_items)

    def _create_font(self, bold: bool = False) -> QFont:
        font = QFont(DEFAULT_FONT_NAME)
        font.setPixelSize(DEFAULT_FONT_SIZE_PX)
        if bold:
            font.setBold(True)
        return font


class DoubleClickContext:
    def __init__(self, index: QModelIndex, table: 'QTable'):
        self.index = index
        self.__table = table

    @property
    def cell(self) -> tuple[int, int]:
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
        """Returns the displayed value."""
        return self.column.get_displayed_value(self.item)  # TODO: should ask the column or should ask the model?


class SelectionContext:
    def __init__(
        self,
        table: 'QTable',
        selected_indexes: list[QModelIndex],
        current: QModelIndex,
        added: list[QModelIndex] | None,
        removed: list[QModelIndex] | None,
    ):
        self.__table = weakref.ref(table)
        self.selected_model_indexes = selected_indexes
        self.added_model_indexes = added
        self.removed_model_indexes = removed
        self.current_model_index = current

    @property
    def selected_indexes(self) -> list[Cell]:
        return [Cell(i.row(), i.column()) for i in self.selected_model_indexes]

    @property
    def added_indexes(self) -> list[Cell] | None:
        if self.added_model_indexes:
            return [Cell(i.row(), i.column()) for i in self.added_model_indexes]
        return None

    @property
    def removed_indexes(self) -> list[Cell] | None:
        if self.removed_model_indexes:
            return [Cell(i.row(), i.column()) for i in self.removed_model_indexes]
        return None

    @property
    def current_index(self) -> Cell:
        return Cell(self.current_model_index.row(), self.current_model_index.column())

    # TODO: distinguish between when selection is based on single cell, single row,
    #       multiple cells, multiple rows
    @property
    def selected_items(self) -> list[Any] | None:
        table = self.__table()
        if table is None:
            return None
        row_indexes = (i.row() for i in self.selected_model_indexes)
        return [table.model().get_item_by_index(i) for i in set(row_indexes)]

    @property
    def selected_values(self) -> Iterator[tuple[Cell, Any]]:
        table = self.__table()
        if table is not None:
            get_cell_value = table.model().get_cell_value
            for row_index, column_index in self.selected_indexes:
                yield Cell(row_index, column_index), get_cell_value(row_index, column_index)


class QTable(QTableView):
    """
    A table has basically columns and a collection of items.
    """

    #: on_double_click signal is emitted when doubleClicked signal is handled
    on_double_click: Signal = Signal(DoubleClickContext)

    #: on_selection signal is emitted whenever the selection on the table changes
    on_selection: Signal = Signal(SelectionContext)

    #: signal to notify whenever the checked items change
    on_checked_items: Signal = Signal(set)

    def __init__(
        self,
        columns: list[Column],
        items: list[Any] | None = None,
        *,
        checkable: bool = False,
        context_menu: list['ContextMenuAction'] | None = None,
        alternate_row_colors: bool = True,
        checked_items: Collection[Any] | None = None,
        sortable: bool = True,
        parent: QWidget | None = None,
        convert_item=None,
    ):
        super().__init__(parent=parent)
        self.columns = columns
        if items is None:
            items = []
        self.items = items
        self.context_menu = context_menu or []
        self.setAlternatingRowColors(alternate_row_colors)
        self.doubleClicked.connect(self.on_double_clicked)
        model = QTableModel(
            self.columns, self.items, checkable=checkable, checked_items=checked_items, convert_item=convert_item
        )
        model.on_checked_items.connect(self.on_model_checked_items_changed)
        self.setModel(model)
        self.verticalHeader().setDefaultSectionSize(DEFAULT_ROW_HEIGHT)
        self.sortable = sortable
        self.__updating = False  # sentinel
        # TODO: improve the way we update the internals - maybe offering a high-level function that gets everything
        #       that is internal and is possible of updating?
        #       Also, need to eliminate the duplication here - we should only work in terms of what's inside the model
        #       this will prevent from view and model getting out of sync

        # Horizontal header with filter capabilities
        h_header = QFilterableHeaderView(Qt.Orientation.Horizontal, parent=self)
        h_header.filterChanged.connect(self.on_filter_changed)
        h_header.setSectionsClickable(True)
        h_header.setSortIndicatorShown(True)
        self.setHorizontalHeader(h_header)

        self.__selection_mode = SelectionMode.MULTI_CELLS  # QTableView's own default: extended, per-item
        self.__selection_mode_override: SelectionMode | None = None

    # QTable installs its model, headers and selection model in __init__ and never removes them,
    # so these accessors narrow away the `| None` the Qt stubs declare.
    def model(self) -> QTableModel:
        return cast('QTableModel', super().model())

    def horizontalHeader(self) -> QHeaderView:
        return cast('QHeaderView', super().horizontalHeader())

    def verticalHeader(self) -> QHeaderView:
        return cast('QHeaderView', super().verticalHeader())

    def selectionModel(self) -> QItemSelectionModel:
        return cast('QItemSelectionModel', super().selectionModel())

    def paintEvent(self, event: QPaintEvent | None) -> None:
        # Font, Foreground and Background share one CellStyle per cell; scoping the
        # cache to a single paint means it can never serve a stale style.
        with self.model().caching_cell_styles():
            super().paintEvent(event)

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        """Supports copying when multiple cells are selected."""
        if event is None:
            return super().keyPressEvent(event)
        if event.matches(QKeySequence.StandardKey.Copy):
            selected_indexes = self.selectedIndexes()
            if selected_indexes:
                data = (
                    (i.row(), i.column(), self.model().data(i, role=Qt.ItemDataRole.DisplayRole))
                    for i in selected_indexes
                )
                rows = (
                    (v for _, _, v in cells) for _, cells in itertools.groupby(sorted(data), key=operator.itemgetter(0))
                )

                sio = StringIO()
                writer = csv.writer(sio, delimiter='\t')
                writer.writerows(rows)

                sio.seek(0)
                if (clipboard := QApplication.clipboard()) is not None:
                    clipboard.setText(sio.read())
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (
            event.modifiers() & Qt.KeyboardModifier.AltModifier
        ):
            if self.__selection_mode_override is None:
                self.__selection_mode_override = self.__selection_mode
                self.set_selection_mode(SelectionMode.MULTI_CELLS)
                self.clearSelection()
        else:
            return super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent | None) -> None:
        if event is None:
            return super().keyReleaseEvent(event)
        ctrl_alt_held = (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (
            event.modifiers() & Qt.KeyboardModifier.AltModifier
        )
        if not ctrl_alt_held and self.__selection_mode_override is not None:
            self.set_selection_mode(self.__selection_mode_override)
            self.__selection_mode_override = None
        return super().keyReleaseEvent(event)

    def on_filter_changed(self, column: Column, expression: str) -> None:
        self.model().set_filter(column, expression)

    def clear_filters(self):
        self.model().clear_filters()

    @property
    def columns(self) -> list[Column]:
        return self._columns

    @columns.setter
    def columns(self, columns: list[Column]):
        self._columns = columns
        # refresh the model
        if self.model() is not None:
            self.model().columns = columns

    @property
    def items(self) -> list:
        return self._items

    @items.setter
    def items(self, items: list[Any]):
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

    @property
    def sortable(self) -> bool:
        return self.isSortingEnabled()

    @sortable.setter
    def sortable(self, sortable: bool) -> None:
        self.setSortingEnabled(sortable)

    @contextlib.contextmanager
    def updating_internals(self):
        self.__updating = True

        try:
            self.model().beginResetModel()
            yield
        finally:
            self.__updating = False
            self.model().endResetModel()
            # TODO: it should be a controllable behaviour whether to always resize or
            #       resize only once - the problem is if the columns change
            if not hasattr(self, '_adjusted_columns_size') and self.columns and self.items:
                # print('adjusting column sizes for the first and only time')
                get_size = self.horizontalHeader().sectionSize
                self.adjust_column_sizes()
                self._adjusted_columns_size = True
                self._previous_colsizes = {c.title: get_size(i) for i, c in enumerate(self.columns)}
            elif hasattr(self, '_previous_colsizes'):
                resize = self.horizontalHeader().resizeSection
                for i, c in enumerate(self.columns):
                    resize(i, self._previous_colsizes.get(c.title, 100))

    def refresh(self):
        m = self.model()
        m.refresh_filtered_items()  # TODO: find a better way without requiring this
        top_left = m.index(0, 0)
        bottom_right = m.index(len(self.items), len(self.columns))
        m.dataChanged.emit(top_left, bottom_right)

    def refresh_one_cell(self, row: int, col: int) -> None:
        # how about filtering and sorting here?
        # perhaps we can say that ticking tables cannot be filtered or sorted?
        m = self.model()
        # dataChanged's bottomRight is inclusive — both indices must be the
        # same to invalidate exactly one cell.
        index = m.index(row, col)
        m.dataChanged.emit(index, index)

    def refresh_cells(self, rows, cols) -> None:
        # Group consecutive same-row updates into a single dataChanged emit so
        # we make N→k Python→Qt signal hops where k is the number of unique
        # rows. Range-emit invalidates every column in [min,max] of each row;
        # unchanged columns get re-fetched but paint identically — net win
        # whenever the changed columns of a row are reasonably clustered.
        m = self.model()
        if len(rows) == 0:
            return
        by_row: dict[int, list[int]] = {}
        for r, c in zip(rows, cols, strict=True):
            by_row.setdefault(int(r), []).append(int(c))
        for row, row_cols in by_row.items():
            cmin = min(row_cols)
            cmax = max(row_cols)
            m.dataChanged.emit(m.index(row, cmin), m.index(row, cmax))

    def set_selection_mode(self, selection_mode: SelectionMode) -> None:
        mode, behavior = QT_SELECTION[selection_mode]
        self.setSelectionMode(mode)
        self.setSelectionBehavior(behavior)
        self.__selection_mode = selection_mode

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

    def contextMenuEvent(self, event: QContextMenuEvent | None) -> None:
        if event is None:
            return
        default_actions = [ResetFiltersAction(table=self)]
        context_menu = self.context_menu + default_actions

        convert_item = self.model().convert_item
        context = MenuActionContext(pos=event.pos(), table=self, convert_item=convert_item)
        enabled_actions = [a for a in context_menu if a.is_enabled(context)]
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
            menu.exec(pos)

    # Double Click

    def on_double_clicked(self, index: QModelIndex):
        """
        Function handler listening whenever Qt fires the doubleClicked event.
        """
        double_click_context = DoubleClickContext(index=index, table=self)
        self.on_double_click.emit(double_click_context)

    # Selection

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection):
        super().selectionChanged(selected, deselected)
        selection_context = SelectionContext(
            table=self,
            selected_indexes=self.selectionModel().selectedIndexes(),
            added=selected.indexes(),
            removed=selected.indexes(),
            current=self.currentIndex(),
        )
        self.on_selection.emit(selection_context)

    def get_current_selection_context(self) -> SelectionContext:
        return SelectionContext(
            table=self,
            selected_indexes=self.selectionModel().selectedIndexes(),
            added=None,
            removed=None,
            current=self.currentIndex(),
        )

    # Checked Items

    def on_model_checked_items_changed(self, checked_items: set):
        """Just passes along the notification of the change on the checked items."""
        self.on_checked_items.emit(checked_items)

    @property
    def checked_items(self) -> set:
        if self.checkable:
            return self.model().checked_items
        return set()

    # Column Sizes
    def adjust_column_sizes(self) -> None:
        fm = self.fontMetrics()
        model = self.model()
        items = model.items
        for i, col in enumerate(self.columns):
            if col.size == 'auto':
                # THIS IS SUPER SLOW!
                self.resizeColumnToContents(i)
            elif col.size == 'just':
                # Consider the font metrics of the view
                # Here we are taking into account only the first thousand rows
                # because otherwise this would be very slow for millions of rows
                # It does not take into consideration the text in the header
                get_displayed_value = col.get_displayed_value
                size = 20
                for row_index in range(min(model.rowCount(), 1000)):
                    size = max(size, fm.horizontalAdvance(get_displayed_value(items[row_index])))
                self.horizontalHeader().resizeSection(i, size + 10)
            elif isinstance(col.size, int):
                self.horizontalHeader().resizeSection(i, col.size)
            elif col.size == 'ignore':
                continue
            else:
                raise ValueError(f'Invalid column size: {col.size}')


class MenuActionContext:
    """
    This class represents what gets passed to the context menu actions (ContextMenuAction)
    when the user requests a context menu on the table (for example, by performing a right-click)
    """

    def __init__(
        self,
        pos: QPoint,
        table: QTable,
        convert_item=default_convert_item,
    ):
        self.__table = table
        self.pos = pos
        if convert_item is None:
            convert_item = default_convert_item
        self.convert_item = convert_item

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
        return self.convert_item(self.raw_item)

    @property
    def raw_item(self) -> Any:
        if (row_index := self.row_index) != -1:
            return self.model.get_item_by_index(row_index)

    @property
    def column(self) -> Column | None:
        if (col_index := self.column_index) != -1:
            return self.model.get_column_by_index(col_index)
        return None

    @property
    def raw_value(self) -> Any:
        if (item := self.item) is not None and (column := self.column) is not None:  # TODO: use a different sentinel?
            return column.get_value(item)
        return None

    @property
    def value(self) -> str | None:
        """Returns the displayed value."""
        if (item := self.item) is not None and (column := self.column) is not None:  # TODO: use a different sentinel?
            return column.get_displayed_value(item)
        return None


class ContextMenuAction(ABC):
    @abstractmethod
    def is_enabled(self, context: MenuActionContext) -> bool:
        pass

    @abstractmethod
    def get_caption(self, context: MenuActionContext) -> str:
        pass

    @abstractmethod
    def execute(self, context: MenuActionContext):
        pass


class ResetFiltersAction(ContextMenuAction):
    def __init__(self, table: QTable):
        self.table = table

    def is_enabled(self, context: MenuActionContext) -> bool:
        return bool(self.table.model().filters)

    def get_caption(self, context: MenuActionContext) -> str:
        return 'Reset Filters'

    def execute(self, context: MenuActionContext) -> None:
        self.table.clear_filters()


class QFilterWidget(QWidget):
    def __init__(self, column, callback, filters, *, parent):
        super().__init__(parent)
        self.column = column
        self.callback = callback
        self.filters = filters
        self._setup_ui()

    def _setup_ui(self):
        caption = f'Filter: {self.column.title}'
        self.setWindowTitle(caption)

        layout = QVBoxLayout()

        label = QLabel(caption)
        label.font().setBold(True)
        layout.addWidget(label)

        self._input_field = input_field = QLineEdit()
        layout.addWidget(input_field)
        input_field.returnPressed.connect(self._notify_callback)

        if (current_filter := self.filters.get(self.column)) is not None:
            input_field.setText(str(current_filter))

        gb = QGroupBox()
        gb.setFlat(True)
        gb.setTitle('')

        gb_layout = QHBoxLayout()
        btn_ok = QPushButton('OK')
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._notify_callback)

        btn_cancel = QPushButton('Cancel')
        btn_cancel.setDefault(False)
        btn_cancel.clicked.connect(self.close)

        gb_layout.addStretch()
        gb_layout.addWidget(btn_ok)
        gb_layout.addWidget(btn_cancel)

        gb.setLayout(gb_layout)

        layout.addWidget(gb)

        self.setLayout(layout)

        self.setWindowFlags(Qt.WindowType.Popup)
        self.resize(200, 80)

    def popup(self, global_pos: QPoint) -> None:
        self.move(global_pos)
        self.show()
        self._input_field.setFocus()

    def _notify_callback(self, *args: object) -> None:
        expression = self._input_field.text().strip()
        self.callback(self.column, expression)
        self.close()


class QFilterableHeaderView(QHeaderView):
    filterChanged = Signal(Column, str)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is not None and event.button() == Qt.MouseButton.RightButton:
            table = cast('QTable', self.parent())
            model = table.model()
            column_index = self.logicalIndexAt(event.position().toPoint())
            column = model.get_column_by_index(column_index)
            filter_widget = QFilterWidget(column, self.filter_callback, model.filters, parent=table)
            filter_widget.popup(event.globalPosition().toPoint())

        super().mousePressEvent(event)

    def filter_callback(self, column: Column, expression: str):
        # TODO: use column index?
        self.filterChanged.emit(column, expression)


def debug_trace():
    """
    Set a tracepoint in the Python debugger that works with Qt
    """
    import pdb
    import sys

    from qtpy import QtCore

    # Only PyQt installs an input hook that fights pdb for stdin; PySide has none to remove.
    if hasattr(QtCore, 'pyqtRemoveInputHook'):
        QtCore.pyqtRemoveInputHook()
    # set up the debugger
    debugger = pdb.Pdb()
    debugger.reset()
    # custom next to get outside of function scope
    debugger.do_next('')  # run the next command
    users_frame = sys._getframe().f_back  # frame where the user invoked `pyqt_set_trace()`
    debugger.interaction(users_frame, None)

    # TODO: should call QtCore.pyqtRestoreInputHook() ?


if __name__ == '__main__':
    # Making Ctrl+C work
    import signal
    import uuid

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Fixing PyQt issue on MacOS BigSur
    import os

    os.environ['QT_MAC_WANTS_LAYER'] = '1'

    app = QApplication([])

    def tooltip_callback(table_context: TableContext) -> str:
        item = table_context.item
        return f'{item.name} is {item.age} years old'

    def age_cell_style(table_context: TableContext) -> CellStyle | None:
        if table_context.item.age > 30:
            return CellStyle(color=QColor(200, 20, 100))
        return None

    columns = [
        Column('name', title='Name'),
        Column('age', align=Alignment.RIGHT, tooltip=tooltip_callback, cell_style=age_cell_style),
    ]

    @dataclass(frozen=True)
    class Person:
        id: uuid.UUID
        name: str
        age: int
        sex: str

    people_kwargs: list[dict[str, Any]] = [
        {'name': 'John', 'age': 33, 'sex': 'M'},
        {'name': 'Pam', 'age': 22, 'sex': 'F'},
    ]

    items = [Person(id=uuid.uuid4(), **kw) for kw in itertools.islice(itertools.cycle(people_kwargs), 0, 10)]

    def echo_factory(n: int) -> ContextMenuAction:
        class EchoAction(ContextMenuAction):
            def is_enabled(self, context):
                return True

            def get_caption(self, context):
                return f'Echo {n}'

            def execute(self, context):
                print(
                    f'Echo {n} - Cell: ({context.row_index}, {context.column_index}) has value: {context.raw_value!r}'
                )

        return EchoAction()

    context_menu_actions = [
        *(echo_factory(n) for n in range(1, 11)),
    ]

    table = QTable(columns, items, checkable=True, context_menu=context_menu_actions)
    table.set_selection_mode(SelectionMode.MULTI_CELLS)
    # table.set_selection_mode(SelectionMode.SINGLE_ROW)
    table.set_vertical_header_visible(False)
    table.show_horizontal_header()

    # table.setStyleSheet("background-color: rgb(255, 255, 245); alternate-background-color: rgb(220,200,220);")

    def double_click_callback(context: DoubleClickContext):
        print(
            'Double click happened:',
            f'  cell = {context.cell}',
            f'  column = {context.column}',
            f'  raw_value = {context.raw_value}',
            sep='\n',
        )

    table.on_double_click.connect(double_click_callback)

    def selection_callback(context: SelectionContext):
        print(
            f'Selected indexes: {context.selected_indexes}',
            f'Added: {context.added_indexes}',
            f'Removed: {context.removed_indexes}',
            f'Current: {context.current_index}',
            sep='\n',
        )

    table.on_selection.connect(selection_callback)

    def checked_items_callback(checked_items: set):
        print('Checked items:', checked_items)

    table.on_checked_items.connect(checked_items_callback)

    table.show()

    app.exec()
