"""
MultiSelect widget - allows for multiple selection/choices.
"""
from typing import Optional
from unittest import mock

import pytest
from atom.api import Atom, List
from atom.atom import observe
from atom.property import Property


def is_valid_selection(items: List, selected_items: List) -> bool:
    selected_items_set = set(selected_items)
    items_set = set(items)
    return ((selected_items_set <= items_set)  # subset
            and (len(selected_items_set) == len(selected_items))  # no dupes
            and (len(items_set) == len(items)))


class MultiSelectInitError(ValueError):
    pass


class MultiSelectUpdateError(RuntimeError):
    pass


class MultiSelectModel(Atom):
    #: collection of all available items for selection
    items = List()

    #: collection of currently selected items
    selected_items = List()

    #: collection of items still up for grabs (read-only!)
    available_items = Property(cached=True)

    def __init__(self, items: List, selected_items: Optional[List] = None):
        """
        The list of all available items must always be provided.
        Optionally the model can also be initialized with some selected_items.
        The list of available items then it's always calculated in terms of the other two above.
        """
        if selected_items is None:
            selected_items = []
        if not is_valid_selection(items, selected_items):
            raise MultiSelectInitError(f"{type(self).__name__} initialized with invalid lists. "
                                       f"The selected_items must bea a subset of all the items and "
                                       f"there must be no duplicates.")
        with self.suppress_notifications():
            self.items = items

        # Now, finally, we fire the notifications
        self.selected_items = selected_items

    @observe("items", "selected_items")
    def _refresh_available_items(self, change=None):
        if not is_valid_selection(self.items, self.selected_items):
            raise MultiSelectUpdateError(f"{type(self).__name__} invalid state after an update. "
                                         f"The selected_items must bea a subset of all the items and "
                                         f"there must be no duplicates.")
        self.get_member("available_items").reset(self)

    @available_items.getter
    def get_available_items(self):
        return [i for i in self.items if i not in self.selected_items]

    def invert_selection(self):
        self.selected_items = self.available_items

    def select_all(self):
        self.selected_items = self.items

    def select_none(self):
        self.selected_items = []

    def select(self, items):
        # TODO: preserve the order of the original list of items
        selected_items = list(self.selected_items)
        selected_items.extend(items)
        self.selected_items = selected_items

    def unselect(self, items):
        items = set(items)
        self.selected_items = [item for item in self.selected_items if item not in items]


    clear_selection = select_none


def test_is_valid_selection():
    # there should be no duplicated items
    # the items should respect original order/sequence
    assert is_valid_selection([1, 2, 3], [1, 3])
    assert is_valid_selection([1, 2, 3], [])
    assert is_valid_selection([1, 2, 3], [1, 2, 3])
    assert not is_valid_selection([1, 2, 3], [1, 2, 3, 4])
    assert not is_valid_selection([1, 2, 3], [1, 2, 5])


def test_multi_select_model_refreshes_available_items_correctly():
    multi_select_model = MultiSelectModel(items=[1, 2, 3, 4], selected_items=[2, 3])
    assert multi_select_model.available_items == [1, 4]

    multi_select_model.items = [1, 2, 3, 4, 5]
    assert multi_select_model.available_items == [1, 4, 5]

    multi_select_model.selected_items = [1, 2, 3, 4, 5]
    assert multi_select_model.available_items == []


def test_can_observe_on_available_items_notifications():
    multi_select_model = MultiSelectModel(items=[1, 2, 3, 4], selected_items=[2, 3])

    callback = mock.Mock(spec=True)

    multi_select_model.observe("available_items", callback)

    multi_select_model.selected_items = [2, 3, 4]

    callback.assert_called_once()


def test_exception_is_raised_when_model_reaches_invalid_state_after_update():
    multi_select_model = MultiSelectModel(items=[1, 2, 3, 4], selected_items=[2, 3])
    with pytest.raises(MultiSelectUpdateError):
        multi_select_model.selected_items = [2, 2, 3]


def test_invert_selection():
    multi_select_model = MultiSelectModel(items=[1, 2, 3, 4], selected_items=[2, 3])
    assert multi_select_model.available_items == [1, 4]

    multi_select_model.invert_selection()
    assert multi_select_model.available_items == [2, 3]
    assert multi_select_model.selected_items == [1, 4]

