import enaml


def ask_yes_no(title: str, message: str, parent=None) -> bool:
    with enaml.imports():
        from enaml.stdlib.message_box import question

    button = question(parent, title, message)
    return button is not None and button.text == 'Yes'


def ask_text(title, message, text='', parent=None):
    with enaml.imports():
        from enamlext.widgets._text_input_dialog import TextInputDialog
        dlg = TextInputDialog(parent=parent, title=title, message=message,
                              text=text)
        if dlg.exec_():
            return dlg.text
