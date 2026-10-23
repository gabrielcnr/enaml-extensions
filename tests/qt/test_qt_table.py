from collections import Counter
from dataclasses import dataclass
from typing import Any

import pandas as pd
import pytest
from qtpy.QtCore import QAbstractTableModel, QEvent, QPoint
from qtpy.QtGui import QColor, QContextMenuEvent, QHelpEvent, QKeySequence, QPalette
from qtpy.QtTest import QTest
from qtpy.QtWidgets import QAbstractItemView, QApplication, QLineEdit, QMenu, QStyledItemDelegate, QToolTip

from enamlext.qt.qtable import QFilterWidget, QModelIndex, Qt, QTable, QTableModel, SelectionMode, make_custom_font
from enamlext.qt.table.column import Alignment, Column
from enamlext.qt.table.defs import CellStyle


class QTestTable(QTable):
    """
    A QTable with some funky testing capabilities.
    """

    def index(self, row_index: int, column_index: int) -> QModelIndex:
        return self.model().index(row_index, column_index)

    def data(self, row_index: int, column_index: int, role: int) -> Any:
        index = self.index(row_index, column_index)
        return self.model().data(index, role)

    def text(self, row_index: int, column_index: int) -> str:
        return self.data(row_index, column_index, Qt.ItemDataRole.DisplayRole)


@pytest.fixture
def table(qtbot):
    table = QTestTable(columns=[])
    qtbot.addWidget(table)
    return table


def test_displayed_data_basic(table):
    @dataclass
    class Person:
        name: str
        age: int

    items = [
        Person(name='John', age=33),
        Person(name='Pam', age=22),
    ]

    columns = [
        Column('name', title='Name'),
        Column('age', align=Alignment.RIGHT),
    ]

    with table.updating_internals():
        table.columns = columns
        table.items = items

    assert table.text(1, 0) == 'Pam'


@dataclass
class Person:
    name: str
    age: int


def test_cell_style_is_served_for_font_foreground_and_background_roles(table):
    def cell_style(context):
        if context.raw_value < 30:
            return CellStyle(color=QColor('red'), background=QColor('yellow'), font='bold')

    with table.updating_internals():
        table.columns = [Column('age', cell_style=cell_style)]
        table.items = [Person(name='John', age=33), Person(name='Pam', age=22)]

    assert table.data(1, 0, Qt.ItemDataRole.FontRole).bold()
    assert table.data(1, 0, Qt.ItemDataRole.ForegroundRole) == QColor('red')
    assert table.data(1, 0, Qt.ItemDataRole.BackgroundRole) == QColor('yellow')

    assert not table.data(0, 0, Qt.ItemDataRole.FontRole).bold()
    assert table.data(0, 0, Qt.ItemDataRole.ForegroundRole) is None
    assert table.data(0, 0, Qt.ItemDataRole.BackgroundRole) is None


@pytest.mark.parametrize(
    ('font_spec', 'bold', 'italic', 'underline'),
    [
        ('bold', True, False, False),
        ('italic', False, True, False),
        ('underline', False, False, True),
        ('bold italic underline', True, True, True),
    ],
)
def test_make_custom_font_styles(qapp, font_spec, bold, italic, underline):
    font = make_custom_font(font_spec)

    assert (font.bold(), font.italic(), font.underline()) == (bold, italic, underline)


def test_make_custom_font_size_and_family(qapp):
    font = make_custom_font('bold underline 12px Arial Narrow')

    assert font.bold()
    assert font.underline()
    assert font.pixelSize() == 12
    assert font.family() == 'Arial Narrow'


def test_cell_style_font_underline_reaches_the_font_role(table):
    with table.updating_internals():
        table.columns = [Column('name', cell_style=lambda context: CellStyle(font='underline'))]
        table.items = [Person(name='John', age=33)]

    font = table.data(0, 0, Qt.ItemDataRole.FontRole)

    assert font.underline()
    assert not font.italic()


def test_cell_style_callback_runs_once_per_cell_on_each_repaint(table):
    calls = Counter()

    def cell_style(context):
        calls[context.row_index, context.column_index] += 1
        return CellStyle(color=QColor('red'), background=QColor('yellow'), font='bold')

    with table.updating_internals():
        table.columns = [Column('name', cell_style=cell_style), Column('age', cell_style=cell_style)]
        table.items = [Person(name='John', age=33), Person(name='Pam', age=22)]
    table.resize(400, 300)

    calls.clear()
    table.viewport().grab()
    assert calls == {(0, 0): 1, (0, 1): 1, (1, 0): 1, (1, 1): 1}

    table.viewport().grab()
    assert calls == {(0, 0): 2, (0, 1): 2, (1, 0): 2, (1, 1): 2}


def test_cell_style_reflects_current_item_after_a_repaint(table):
    def cell_style(context):
        if context.raw_value < 30:
            return CellStyle(font='bold')

    person = Person(name='John', age=33)
    with table.updating_internals():
        table.columns = [Column('age', cell_style=cell_style)]
        table.items = [person]
    table.resize(400, 300)

    table.viewport().grab()
    person.age = 22

    assert table.data(0, 0, Qt.ItemDataRole.FontRole).bold()


class StyleRecordingDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super().__init__(parent)
        self.painted = {}

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        self.painted[index.row(), index.column()] = (
            option.backgroundBrush.color().name(),
            option.palette.color(QPalette.ColorRole.Text).name(),
            option.font.bold(),
            option.font.italic(),
        )


def test_each_cell_is_painted_with_its_own_cell_style(table):
    styles = {
        (0, 0): CellStyle(color=QColor('#ff0000'), background=QColor('#ffff00'), font='bold'),
        (0, 1): CellStyle(color=QColor('#0000ff'), background=QColor('#00ff00'), font='italic'),
        (1, 0): CellStyle(color=QColor('#800080'), background=QColor('#00ffff'), font='bold italic'),
        (1, 1): CellStyle(color=QColor('#008000'), background=QColor('#ffc0cb')),
    }

    def cell_style(context):
        return styles[context.row_index, context.column_index]

    with table.updating_internals():
        table.columns = [Column('name', cell_style=cell_style), Column('age', cell_style=cell_style)]
        table.items = [Person(name='John', age=33), Person(name='Pam', age=22)]
    table.resize(400, 300)
    delegate = StyleRecordingDelegate(parent=table)
    table.setItemDelegate(delegate)

    table.viewport().grab()

    assert delegate.painted == {
        (0, 0): ('#ffff00', '#ff0000', True, False),
        (0, 1): ('#00ff00', '#0000ff', False, True),
        (1, 0): ('#00ffff', '#800080', True, True),
        (1, 1): ('#ffc0cb', '#008000', False, False),
    }


def test_collect_stats_records_timings(table):
    column = Column('age', collect_stats=True)
    with table.updating_internals():
        table.columns = [column]
        table.items = [Person(name='John', age=33), Person(name='Pam', age=22)]
    column.stats.clear()  # populating the table already read every cell to size the columns

    assert table.text(0, 0) == '33'

    assert column.stats[Qt.ItemDataRole.DisplayRole]['n_calls'] == 1
    assert column.stats[Qt.ItemDataRole.DisplayRole]['cum_time'] >= 0


@pytest.mark.parametrize(
    ('order', 'expected'),
    [(Qt.SortOrder.AscendingOrder, ['22', '33', '41']), (Qt.SortOrder.DescendingOrder, ['41', '33', '22'])],
)
def test_sorting_by_a_column(qtbot, order, expected):
    table = QTestTable(columns=[Column('age')], items=[Person('John', 33), Person('Pam', 22), Person('Ann', 41)])
    qtbot.addWidget(table)

    table.sortByColumn(0, order)

    assert [table.text(row, 0) for row in range(3)] == expected


@pytest.mark.parametrize(
    ('order', 'expected'),
    [
        (Qt.SortOrder.AscendingOrder, ['', '<NA>', 'nan', '-1', '2']),
        (Qt.SortOrder.DescendingOrder, ['2', '-1', '', '<NA>', 'nan']),
    ],
)
def test_sorting_puts_missing_values_before_the_smallest(qtbot, order, expected):
    values = [2, None, -1, pd.NA, float('nan')]
    table = QTestTable(columns=[Column('x', use_getitem=True)], items=[{'x': v} for v in values])
    qtbot.addWidget(table)

    table.sortByColumn(0, order)

    assert [table.text(row, 0) for row in range(5)] == expected


def test_sorting_a_text_column_with_missing_values(qtbot):
    table = QTestTable(columns=[Column('x', use_getitem=True)], items=[{'x': v} for v in ['b', float('nan'), 'a']])
    qtbot.addWidget(table)

    table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    assert [table.text(row, 0) for row in range(3)] == ['nan', 'a', 'b']


@pytest.mark.parametrize(
    ('mode', 'selection_mode', 'behavior'),
    [
        (
            SelectionMode.SINGLE_CELL,
            QAbstractItemView.SelectionMode.SingleSelection,
            QAbstractItemView.SelectionBehavior.SelectItems,
        ),
        (
            SelectionMode.MULTI_CELLS,
            QAbstractItemView.SelectionMode.ExtendedSelection,
            QAbstractItemView.SelectionBehavior.SelectItems,
        ),
        (
            SelectionMode.SINGLE_ROW,
            QAbstractItemView.SelectionMode.SingleSelection,
            QAbstractItemView.SelectionBehavior.SelectRows,
        ),
        (
            SelectionMode.MULTI_ROWS,
            QAbstractItemView.SelectionMode.ExtendedSelection,
            QAbstractItemView.SelectionBehavior.SelectRows,
        ),
    ],
)
def test_set_selection_mode(table, mode, selection_mode, behavior):
    table.set_selection_mode(mode)
    assert table.selectionMode() == selection_mode
    assert table.selectionBehavior() == behavior


def test_copy_puts_the_selected_cells_on_the_clipboard_as_tsv(qtbot):
    table = QTestTable(
        columns=[Column('name'), Column('age')], items=[Person('John', 33), Person('Pam', 22)], sortable=False
    )
    qtbot.addWidget(table)
    table.set_selection_mode(SelectionMode.MULTI_CELLS)
    table.selectAll()

    QTest.keySequence(table, QKeySequence(QKeySequence.StandardKey.Copy))

    assert QApplication.clipboard().text().splitlines() == ['John\t33', 'Pam\t22']


def test_holding_ctrl_alt_switches_to_cell_selection_until_released(qtbot):
    table = QTestTable(columns=[Column('name')], items=[Person('John', 33)])
    qtbot.addWidget(table)
    table.set_selection_mode(SelectionMode.SINGLE_ROW)
    ctrl_alt = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier

    QTest.keyPress(table, Qt.Key.Key_Alt, ctrl_alt)
    assert table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectItems

    QTest.keyRelease(table, Qt.Key.Key_Alt, Qt.KeyboardModifier.ControlModifier)
    assert table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows


def test_right_click_on_a_table_without_custom_actions(qtbot, mocker):
    table = QTestTable(columns=[Column('name')], items=[Person('John', 33)])
    qtbot.addWidget(table)
    exec_menu = mocker.patch.object(QMenu, 'exec')

    event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(5, 5), QPoint(5, 5))
    table.contextMenuEvent(event)

    exec_menu.assert_not_called()  # no custom actions and no filters, so nothing to show


def test_ctrl_alt_on_a_table_whose_selection_mode_was_never_set(qtbot):
    table = QTestTable(columns=[Column('name')], items=[Person('John', 33)])
    qtbot.addWidget(table)
    ctrl_alt = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier

    QTest.keyPress(table, Qt.Key.Key_Alt, ctrl_alt)
    QTest.keyRelease(table, Qt.Key.Key_Alt, Qt.KeyboardModifier.ControlModifier)

    assert table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectItems


def test_model_without_items_is_empty(qapp):
    model = QTableModel([Column('name')])
    assert model.rowCount() == 0
    assert len(model) == 0


def test_right_click_on_a_header_opens_a_filter_that_filters_the_rows(qtbot):
    table = QTestTable(
        columns=[Column('name'), Column('age')],
        items=[Person('John', 33), Person('Pam', 22), Person('Ann', 41)],
        sortable=False,
    )
    qtbot.addWidget(table)
    table.show()
    qtbot.waitExposed(table)
    header = table.horizontalHeader()

    QTest.mouseClick(header.viewport(), Qt.MouseButton.RightButton, pos=QPoint(header.sectionPosition(1) + 5, 5))
    popup = table.findChild(QFilterWidget)
    assert popup is not None
    assert popup.isVisible()

    popup.findChild(QLineEdit).setText('> 30')
    QTest.keyClick(popup.findChild(QLineEdit), Qt.Key.Key_Return)

    assert [table.text(row, 0) for row in range(table.model().rowCount())] == ['John', 'Ann']


def test_operator_filter_on_a_column_mixing_numbers_and_text_keeps_the_matching_numbers(qtbot):
    table = QTestTable(
        columns=[Column('qty', use_getitem=True)], items=[{'qty': 5}, {'qty': 'n/a'}, {'qty': 50}], sortable=False
    )
    qtbot.addWidget(table)

    table.on_filter_changed(table.columns[0], '> 10')

    assert [table.text(row, 0) for row in range(table.model().rowCount())] == ['50']


@dataclass(frozen=True)
class Fruit:
    name: str


def test_clicking_a_checkbox_toggles_the_checked_items(qtbot):
    apple, pear = Fruit('apple'), Fruit('pear')
    table = QTestTable(columns=[Column('name')], items=[apple, pear], checkable=True, sortable=False)
    qtbot.addWidget(table)
    table.show()
    qtbot.waitExposed(table)

    def click_checkbox(row: int) -> None:
        # the check indicator sits at the left edge of the checkbox column
        rect = table.visualRect(table.index(row, 0))
        QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(rect.left() + 8, rect.center().y()))

    with qtbot.waitSignal(table.on_checked_items):
        click_checkbox(1)
    assert table.checked_items == {pear}

    click_checkbox(1)
    assert table.checked_items == set()


def test_header_tooltip_is_shown_on_the_column_header(qtbot):
    table = QTestTable(
        columns=[Column('name'), Column('age', header_tooltip='Age in whole years')],
        items=[Person('John', 33)],
    )
    qtbot.addWidget(table)
    model = table.model()

    assert model.headerData(1, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole) == 'Age in whole years'
    assert model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole) is None


def test_header_tooltip_accounts_for_the_checkbox_column(qtbot):
    table = QTestTable(
        columns=[Column('name', header_tooltip='Full name'), Column('age')],
        items=[Fruit('apple')],
        checkable=True,
    )
    qtbot.addWidget(table)
    model = table.model()

    assert model.headerData(0, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole) is None
    assert model.headerData(1, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole) == 'Full name'
    assert model.headerData(2, Qt.Orientation.Horizontal, Qt.ItemDataRole.ToolTipRole) is None


def test_hovering_a_header_shows_its_tooltip(qtbot):
    table = QTestTable(
        columns=[Column('name'), Column('age', header_tooltip='Age in whole years')],
        items=[Person('John', 33)],
        sortable=False,
    )
    qtbot.addWidget(table)
    table.show()
    qtbot.waitExposed(table)
    header = table.horizontalHeader()
    pos = QPoint(header.sectionViewportPosition(1) + 5, header.height() // 2)

    QApplication.sendEvent(header.viewport(), QHelpEvent(QEvent.Type.ToolTip, pos, header.viewport().mapToGlobal(pos)))

    qtbot.waitUntil(lambda: QToolTip.isVisible() and QToolTip.text() == 'Age in whole years')
    QToolTip.hideText()


def test_cell_style_border_outlines_the_cell_and_keeps_its_background(qtbot):
    def cell_style(context):
        if context.raw_value == 22:
            return CellStyle(border=QColor('#ff0000'), background=QColor('#ffff00'))
        return None

    table = QTestTable(
        columns=[Column('age', cell_style=cell_style)],
        items=[Person('John', 33), Person('Pam', 22)],
        sortable=False,
    )
    qtbot.addWidget(table)
    table.resize(300, 200)
    image = table.viewport().grab().toImage()

    styled = table.visualRect(table.index(1, 0))
    plain = table.visualRect(table.index(0, 0))
    assert image.pixelColor(styled.left() + 1, styled.center().y()).name() == '#ff0000'
    assert image.pixelColor(styled.right() - 1, styled.center().y()).name() == '#ff0000'
    assert image.pixelColor(styled.center().x(), styled.top() + 1).name() == '#ff0000'
    assert image.pixelColor(styled.center().x(), styled.bottom() - 1).name() == '#ff0000'
    assert image.pixelColor(styled.center().x() - 20, styled.center().y()).name() == '#ffff00'
    assert image.pixelColor(plain.left() + 1, plain.center().y()).name() != '#ff0000'


def test_cell_style_border_does_not_run_the_style_callback_again(qtbot):
    calls = Counter()

    def cell_style(context):
        calls[context.row_index] += 1
        return CellStyle(border=QColor('#ff0000'))

    table = QTestTable(columns=[Column('age', cell_style=cell_style)], items=[Person('John', 33), Person('Pam', 22)])
    qtbot.addWidget(table)
    table.resize(300, 200)

    calls.clear()
    table.viewport().grab()

    assert calls == {0: 1, 1: 1}


def test_an_app_supplied_delegate_still_replaces_the_default_one(qtbot):
    painted = []

    class AppDelegate(QStyledItemDelegate):
        def paint(self, painter, option, index):
            painted.append((index.row(), index.column()))
            super().paint(painter, option, index)

    table = QTestTable(columns=[Column('age')], items=[Person('John', 33)])
    qtbot.addWidget(table)
    table.setItemDelegate(AppDelegate(table))
    table.resize(300, 200)
    table.viewport().grab()

    assert (0, 0) in painted


def test_cell_style_border_lands_on_the_right_cell_in_a_checkable_table(qtbot):
    def cell_style(context):
        return CellStyle(border=QColor('#ff0000')) if context.raw_value == 'pear' else None

    table = QTestTable(
        columns=[Column('name', cell_style=cell_style)],
        items=[Fruit('apple'), Fruit('pear')],
        checkable=True,
        sortable=False,
    )
    qtbot.addWidget(table)
    table.resize(300, 200)
    image = table.viewport().grab().toImage()

    name_cell = table.visualRect(table.index(1, 1))
    checkbox_cell = table.visualRect(table.index(1, 0))
    assert image.pixelColor(name_cell.left() + 1, name_cell.center().y()).name() == '#ff0000'
    assert image.pixelColor(checkbox_cell.left() + 1, checkbox_cell.center().y()).name() != '#ff0000'


def test_cell_flags_match_what_the_base_model_reports(qapp):
    model = QTableModel([Column('name'), Column('age')], [Person('John', 33)])
    base = QAbstractTableModel.flags

    assert model.flags(model.index(0, 1)) == base(model, model.index(0, 1))
    assert model.flags(QModelIndex()) == base(model, QModelIndex())


def test_checkbox_column_flags(qapp):
    model = QTableModel([Column('name')], [Person('John', 33)], checkable=True)
    flags = model.flags(model.index(0, 0))

    assert flags & Qt.ItemFlag.ItemIsUserCheckable
    assert not flags & Qt.ItemFlag.ItemIsSelectable
    assert model.flags(model.index(0, 1)) == QAbstractTableModel.flags(model, model.index(0, 1))


def test_roles_the_model_does_not_handle_return_none(table):
    with table.updating_internals():
        table.columns = [Column('name')]
        table.items = [Person('John', 33)]

    assert table.data(0, 0, Qt.ItemDataRole.EditRole) is None
    assert table.data(0, 0, Qt.ItemDataRole.UserRole) is None


def test_a_failing_cell_style_is_logged_once_per_role_and_painting_goes_on(table, caplog):
    def cell_style(context):
        raise ValueError('boom')

    with table.updating_internals():
        table.columns = [Column('name', cell_style=cell_style)]
        table.items = [Person('John', 33)]
    caplog.clear()

    assert table.data(0, 0, Qt.ItemDataRole.FontRole) == table.model()._font
    assert table.data(0, 0, Qt.ItemDataRole.ForegroundRole) is None
    assert table.data(0, 0, Qt.ItemDataRole.BackgroundRole) is None
    detail = "for column: col_index = 0, column.title = 'Name', index.row() = 0, exc = ValueError('boom')"
    assert [r.getMessage() for r in caplog.records] == [
        f'Error when resolving font {detail}',
        f'Error when resolving foreground colour style {detail}',
        f'Error when resolving background colour style {detail}',
    ]


def test_a_failing_cell_style_raises_when_errors_are_not_graceful(table):
    def cell_style(context):
        raise ValueError('boom')

    with table.updating_internals():
        table.columns = [Column('name', cell_style=cell_style)]
        table.items = [Person('John', 33)]
    table.model().error_handling = 'raise'

    with pytest.raises(ValueError, match='boom'):
        table.model()._data(table.index(0, 0), Qt.ItemDataRole.ForegroundRole)


def test_cell_style_context_reads_each_value_once_and_only_when_asked(table):
    reads = Counter()

    class CountingColumn(Column):
        def get_value_by_attribute_lookup(self, item):
            reads[item.name] += 1
            return super().get_value_by_attribute_lookup(item)

    def cell_style(context):
        if context.item.name == 'Pam':
            return None
        return CellStyle(font='bold') if context.raw_value == context.raw_value else None

    with table.updating_internals():
        table.columns = [CountingColumn('age', cell_style=cell_style)]
        table.items = [Person('John', 33), Person('Pam', 22)]
    reads.clear()

    table.data(0, 0, Qt.ItemDataRole.FontRole)
    table.data(1, 0, Qt.ItemDataRole.FontRole)

    assert reads == {'John': 1}


def test_a_cell_style_callback_can_override_context_values(table):
    def cell_style(context):
        context.raw_value = -context.raw_value
        context.item = 'replaced'
        return CellStyle(font='bold') if context.raw_value < 0 and context.item == 'replaced' else None

    with table.updating_internals():
        table.columns = [Column('age', cell_style=cell_style)]
        table.items = [Person('John', 33)]

    assert table.data(0, 0, Qt.ItemDataRole.FontRole).bold()
