from unittest import mock

import pytest

from enamlext.widgets.multi_select_model import MultiSelectModel, MultiSelectUpdateError, is_valid_selection


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

    multi_select_model.observe('available_items', callback)

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
