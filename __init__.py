# https://github.com/sartak/anki-editor-autocomplete
# -*- coding: utf8 -*-

import re
from aqt import mw
from aqt import editor
from aqt.fields import FieldDialog
from anki.hooks import wrap
from anki.utils import splitFields, stripHTMLMedia
from anki.utils import json
import urllib.request, urllib.error, urllib.parse

RE_SUB_INVALID = re.compile(r"[^a-zA-Z0-9 \n\s]").sub

noAutocompleteFields = []

def mySetup(self, note, hide=True, focus=False):
    self.prevAutocomplete = ""

    # only initialize the autocompleter on Add Cards not in browser
    if self.note and self.addMode:
        self.web.eval(
            """
            document.styleSheets[0].addRule('.autocomplete', 'margin: 0.3em 0 1.0em 0; color: blue; text-decoration: underline; cursor: pointer;');

            // every second send the current state over
            setInterval(function () {
                if (currentField) {
                    var r = {
                        text: currentField.innerHTML,
                    };

                    pycmd("autocomplete:" + JSON.stringify(r));
                }
            }, 1000);
        """
        )


def myBridge(self, cmd, _old=None):
    if cmd.startswith("autocomplete"):
        (type, jsonText) = cmd.split(":", 1)
        result = json.loads(jsonText)
        text = self.mungeHTML(result["text"])

        # Work-around: delete all symbols from the search
        text = RE_SUB_INVALID("", text)

        if self.currentField is None:
            return
        # bail out if the user hasn't actually changed the field
        previous = "%d:%s" % (self.currentField, text)
        if self.prevAutocomplete == previous:
            return
        self.prevAutocomplete = previous

        if text == "" or len(text) > 500 or self.note is None:
            self.web.eval("$('.autocomplete').remove();")
            return

        field = self.note.model()["flds"][self.currentField]

        if field["name"] in noAutocompleteFields:
            field["no_autocomplete"] = True

        if "no_autocomplete" in list(field.keys()) and field["no_autocomplete"]:
            return

        # find a value from the same model and field whose
        # prefix is what the user typed so far
        model_name = self.note.model()["name"]
        field_name = field["name"]
        query = f'note:"{model_name}" "{field_name}:{text}*"'
        # query = "'note:%s' '%s:%s*'" % (
        # self.note.model()['name'],
        # field['name'],
        # text)

        col = self.note.col
        res = col.find_cards(query, order=True)

        if len(res) == 0:
            self.web.eval("$('.autocomplete').remove();")
            return

        # pull out the full value
        value = col.getCard(res[0]).note().fields[self.currentField]

        escaped = json.dumps(value)

        self.web.eval(
            """
            $('.autocomplete').remove();

            if (currentField) {
		$('<div class="autocomplete">' + %s + '</div>').click({field: currentField}, updateField).insertAfter(currentField)
            }

	    function updateField(event){
                currentField = event.data.field;
                currentField.innerHTML = %s;
                saveField("key");
                focusField(currentFieldOrdinal());
                caretToEnd();
	    }
        """
            % (escaped, escaped)
        )
    else:
        _old(self, cmd)


# XXX must figure out how to add noAutocomplete checkbox to form
def myLoadField(self, idx):
    fld = self.model["flds"][idx]
    f = self.form
    if "no_autocomplete" in list(fld.keys()):
        f.noAutocomplete.setChecked(fld["no_autocomplete"])


def mySaveField(self):
    # not initialized yet?
    if self.currentIdx is None:
        return
    idx = self.currentIdx
    fld = self.model["flds"][idx]
    f = self.form
    fld["no_autocomplete"] = f.noAutocomplete.isChecked()


editor.Editor.onBridgeCmd = wrap(editor.Editor.onBridgeCmd, myBridge, "around")
editor.Editor.setNote = wrap(editor.Editor.setNote, mySetup, "after")

# FieldDialog.loadField = wrap(FieldDialog.loadField, myLoadField, 'after')
# FieldDialog.saveField = wrap(FieldDialog.saveField, mySaveField, 'after')

