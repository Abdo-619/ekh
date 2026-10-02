import os, tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from functions import get_student

BASE=os.path.dirname(os.path.abspath(__file__))
LOGO=os.path.join(BASE,'assets','logo.png')
FONT_CANDIDATES=[os.path.join(BASE,'assets','fonts','DejaVuSans.ttf'),'/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    def ar(t): return get_display(arabic_reshaper.reshape(str(t)))
except Exception:            # المكتبتان غير متوفرتين: يُكتب النص دون تشكيل
    def ar(t): return str(t)

def _font():
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            try:
                if 'ArFont' not in pdfmetrics.getRegisteredFontNames(): pdfmetrics.registerFont(TTFont('ArFont',f))
                return 'ArFont'
            except Exception: pass
    return 'Helvetica'

def make_pdf(reg):
    s=get_student(reg)
    if not s: return None
    font=_font(); path=os.path.join(tempfile.gettempdir(),f'graduate_{"".join(ch for ch in str(reg) if ch.isalnum())}.pdf')
    c=canvas.Canvas(path,pagesize=A4); w,h=A4
    try: c.drawImage(LOGO,w/2-40,h-130,width=80,height=80,mask='auto')
    except Exception: pass
    c.setFont(font,18); c.drawCentredString(w/2,h-160,ar('جامعة البطانة'))
    c.setFont(font,14); c.drawCentredString(w/2,h-185,ar('سجل خريج'))
    c.line(50,h-200,w-50,h-200)
    y=h-235; c.setFont(font,12)
    for k,v in s.items():
        if k=='الصورة': continue
        c.drawRightString(w-55,y,ar(f'{k}: {v}')); y-=26
    c.setFont(font,9); c.drawCentredString(w/2,40,ar('University of Al-Butana — Graduates Management System'))
    c.save(); return path
