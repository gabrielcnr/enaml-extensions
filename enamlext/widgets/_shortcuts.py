from enaml.stdlib.message_box import question


def ask_yes_no(title, message, parent=None):
    button = question(parent, title, message)
    return button.text == 'Yes'

