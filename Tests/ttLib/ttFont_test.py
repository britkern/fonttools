import io
import os
import re
import random
from fontTools.ttLib import TTFont, newTable, registerCustomTableClass, unregisterCustomTableClass
from fontTools.ttLib.tables.DefaultTable import DefaultTable

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")


class CustomTableClass(DefaultTable):

    def decompile(self, data, ttFont):
        self.numbers = list(data)

    def compile(self, ttFont):
        return bytes(self.numbers)

    # not testing XML read/write


table_C_U_S_T_ = CustomTableClass  # alias for testing


TABLETAG = "CUST"


def normalize_TTX(string):
    string = re.sub(' ttLibVersion=".*"', "", string)
    string = re.sub('checkSumAdjustment value=".*"', "", string)
    string = re.sub('modified value=".*"', "", string)
    return string


def test_registerCustomTableClass():
    font = TTFont()
    font[TABLETAG] = newTable(TABLETAG)
    font[TABLETAG].data = b"\x00\x01\xff"
    f = io.BytesIO()
    font.save(f)
    f.seek(0)
    assert font[TABLETAG].data == b"\x00\x01\xff"
    registerCustomTableClass(TABLETAG, "ttFont_test", "CustomTableClass")
    try:
        font = TTFont(f)
        assert font[TABLETAG].numbers == [0, 1, 255]
        assert font[TABLETAG].compile(font) == b"\x00\x01\xff"
    finally:
        unregisterCustomTableClass(TABLETAG)


def test_registerCustomTableClassStandardName():
    registerCustomTableClass(TABLETAG, "ttFont_test")
    try:
        font = TTFont()
        font[TABLETAG] = newTable(TABLETAG)
        font[TABLETAG].numbers = [4, 5, 6]
        assert font[TABLETAG].compile(font) == b"\x04\x05\x06"
    finally:
        unregisterCustomTableClass(TABLETAG)


ttxTTF = r"""<?xml version="1.0" encoding="UTF-8"?>
<ttFont sfntVersion="\x00\x01\x00\x00" ttLibVersion="4.9.0">
  <hmtx>
    <mtx name=".notdef" width="300" lsb="0"/>
  </hmtx>
</ttFont>
"""


ttxOTF = """<?xml version="1.0" encoding="UTF-8"?>
<ttFont sfntVersion="OTTO" ttLibVersion="4.9.0">
  <hmtx>
    <mtx name=".notdef" width="300" lsb="0"/>
  </hmtx>
</ttFont>
"""


def test_sfntVersionFromTTX():
    # https://github.com/fonttools/fonttools/issues/2370
    font = TTFont()
    assert font.sfntVersion == "\x00\x01\x00\x00"
    ttx = io.StringIO(ttxOTF)
    # Font is "empty", TTX file will determine sfntVersion
    font.importXML(ttx)
    assert font.sfntVersion == "OTTO"
    ttx = io.StringIO(ttxTTF)
    # Font is not "empty", sfntVersion in TTX file will be ignored
    font.importXML(ttx)
    assert font.sfntVersion == "OTTO"


def test_virtualGlyphId():
    otfpath = os.path.join(DATA_DIR, "TestVGID-Regular.otf")
    ttxpath = os.path.join(DATA_DIR, "TestVGID-Regular.ttx")

    otf = TTFont(otfpath)

    ttx = TTFont()
    ttx.importXML(ttxpath)

    with open(ttxpath, encoding="utf-8") as fp:
        xml = normalize_TTX(fp.read()).splitlines()

    for font in (otf, ttx):
        GSUB = font["GSUB"].table
        assert GSUB.LookupList.LookupCount == 37
        lookup = GSUB.LookupList.Lookup[32]
        assert lookup.LookupType == 8
        subtable = lookup.SubTable[0]
        assert subtable.LookAheadGlyphCount == 1
        lookahead = subtable.LookAheadCoverage[0]
        assert len(lookahead.glyphs) == 46
        assert "glyph00453" in lookahead.glyphs

        out = io.StringIO()
        font.saveXML(out)
        outxml = normalize_TTX(out.getvalue()).splitlines()
        assert xml == outxml


def test_setGlyphOrder_also_updates_glyf_glyphOrder():
    # https://github.com/fonttools/fonttools/issues/2060#issuecomment-1063932428
    font = TTFont()
    font.importXML(os.path.join(DATA_DIR, "TestTTF-Regular.ttx"))
    current_order = font.getGlyphOrder()

    assert current_order == font["glyf"].glyphOrder

    new_order = list(current_order)
    while new_order == current_order:
        random.shuffle(new_order)

    font.setGlyphOrder(new_order)

    assert font.getGlyphOrder() == new_order
    assert font["glyf"].glyphOrder == new_order
