"""
MultiSelect widget - allows for multiple selection/choices.
"""

from collections.abc import Collection, Sequence
from typing import Any

from atom.api import Atom, List
from atom.atom import observe
from atom.property import Property


def is_valid_selection(items: Collection[Any], selected_items: Collection[Any]) -> bool:
    selected_items_set = set(selected_items)
    items_set = set(items)
    return (
        (selected_items_set <= items_set)  # subset
        and (len(selected_items_set) == len(selected_items))  # no dupes
        and (len(items_set) == len(items))
    )


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

    def __init__(self, items: Sequence[Any], selected_items: Sequence[Any] | None = None):
        """
        The list of all available items must always be provided.
        Optionally the model can also be initialized with some selected_items.
        The list of available items then it's always calculated in terms of the other two above.
        """
        if selected_items is None:
            selected_items = []
        if not is_valid_selection(items, selected_items):
            raise MultiSelectInitError(
                f'{type(self).__name__} initialized with invalid lists. '
                f'The selected_items must bea a subset of all the items and '
                f'there must be no duplicates.'
            )
        with self.suppress_notifications():
            self.items = list(items)

        # Now, finally, we fire the notifications
        self.selected_items = list(selected_items)

    @observe('items', 'selected_items')
    def _refresh_available_items(self, change=None):
        if not is_valid_selection(self.items, self.selected_items):
            raise MultiSelectUpdateError(
                f'{type(self).__name__} invalid state after an update. '
                f'The selected_items must bea a subset of all the items and '
                f'there must be no duplicates.'
            )
        self.get_member('available_items').reset(self)  # type: ignore[attr-defined]  # Property, not plain Member

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
