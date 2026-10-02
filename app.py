import os, base64, inspect, html
import gradio as gr
from data import COLUMNS
from functions import *
from report import make_pdf

BASE = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE, 'assets', 'logo.png')
FAVICON_PATH = os.path.join(BASE, 'assets', 'favicon.png')

def _b64(p):
    with open(p, 'rb') as f: return base64.b64encode(f.read()).decode()
LOGO_B64 = _b64(LOGO_PATH)   # الشعار مضغوط (~30KB) ومضمَّن في الصفحة
HEADER_HTML = f'<div class="brand"><img src="data:image/png;base64,{LOGO_B64}" alt="شعار جامعة البطانة"><h1>نظام إدارة خريجي جامعة البطانة</h1><p>University of Al-Butana — Graduates Management System</p></div>'
LOGIN_LOGO = f'<div class="brand small"><img src="data:image/png;base64,{LOGO_B64}" alt="شعار"></div>'

CSS = '''
:root{--g:#1b6b2f;--g2:#e9f5ec}
html,body{direction:rtl}
.gradio-container{max-width:1200px!important;margin:auto!important;direction:rtl;text-align:right;padding:12px!important}
.gradio-container *{box-sizing:border-box}
.brand{text-align:center;padding:8px 0 4px}
.brand img{width:120px;height:auto;margin:0 auto;display:block}
.brand.small img{width:80px}
.brand h1{margin:8px 0 2px;color:var(--g);font-size:1.6rem;line-height:1.4}
.brand p{margin:0;color:#666;font-size:.9rem;direction:ltr}
/* الحقول والأزرار مناسبة للمس */
.gradio-container input,.gradio-container textarea,.gradio-container select{font-size:16px!important}
.gradio-container button{min-height:44px}
/* الصفوف تلتف على الشاشات الصغيرة */
.gradio-container .row{flex-wrap:wrap!important;gap:10px}
.gradio-container .row>*{min-width:200px!important;flex:1 1 200px!important}
/* الجداول: تمرير أفقي داخلي بدل كسر الصفحة */
.gradio-container .table-wrap,.gradio-container [class*="dataframe"]{overflow-x:auto!important;max-width:100%}
/* التبويبات: شريط قابل للتمرير */
.gradio-container .tab-wrapper,.gradio-container .tab-container,.gradio-container [role="tablist"]{overflow-x:auto!important;flex-wrap:nowrap!important;-webkit-overflow-scrolling:touch}
.gradio-container [role="tab"]{white-space:nowrap}
/* بطاقات الإحصائيات */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:8px 0}
.stat{background:var(--g2);border:1px solid #cfe6d5;border-radius:14px;padding:14px;text-align:center}
.stat b{display:block;font-size:1.7rem;color:var(--g)}
.stat span{font-size:.9rem;color:#333}
.stat.total{background:var(--g);border-color:var(--g)}.stat.total b,.stat.total span{color:#fff}
.bar{height:8px;border-radius:6px;margin-top:8px;background:#cfe6d5;overflow:hidden}
.bar i{display:block;height:100%;background:var(--g)}
footer{display:none!important}
@media(max-width:900px){.gradio-container{padding:8px!important}.brand h1{font-size:1.3rem}}
@media(max-width:600px){
  .gradio-container{padding:6px!important}
  .gradio-container .row>*{min-width:100%!important;flex-basis:100%!important}
  .brand img{width:96px}.brand h1{font-size:1.1rem}
  .stats{grid-template-columns:repeat(2,1fr)}.stat b{font-size:1.4rem}
  .gradio-container table{font-size:12px}
}
'''

def _kw(func, **kwargs):
    """تمرير css/theme/favicon في المكان الصحيح حسب إصدار gradio (Blocks أو launch)."""
    params = inspect.signature(func).parameters
    return {k: v for k, v in kwargs.items() if k in params}

THEME = gr.themes.Soft(primary_hue='green')

# ---------- دوال الواجهة ----------
def dashboard_html():
    total, counts = stats()
    mx = max(counts.values()) if counts else 1
    cards = f'<div class="stat total"><b>{total}</b><span>إجمالي الخريجين</span></div>'
    for k, v in counts.items():
        cards += f'<div class="stat"><b>{int(v)}</b><span>{html.escape(str(k))}</span><div class="bar"><i style="width:{int(v)/mx*100:.0f}%"></i></div></div>'
    return f'<div class="stats">{cards}</div>'

def login_action(u, p):
    ok, role = authenticate(u, p)
    if ok:
        return (gr.update(visible=False), gr.update(visible=True), f'✅ تم الدخول — الصلاحية: **{role}**',
                str(u).strip(), role, dashboard_html(), search())
    msg = '⏳ محاولات كثيرة خاطئة. حاول بعد 5 دقائق.' if role == 'locked' else '❌ اسم المستخدم أو كلمة المرور غير صحيحة.'
    return gr.update(visible=True), gr.update(visible=False), msg, '', '', gr.update(), gr.update()

def logout_action():
    return gr.update(visible=True), gr.update(visible=False), '', '', '', ''

def do_search(q, d, y):
    x = search(q, d, y); return f'### 🔎 عدد النتائج: {len(x)}', x

def detail(reg):
    s = get_student(reg)
    if not s: return '❌ لم يتم العثور على الخريج.'
    return '\n'.join([f'## 🎓 {s["الاسم"]}', f'**رقم التسجيل:** {s["رقم التسجيل"]}  ', f'**الرقم الجامعي:** {s["الرقم الجامعي"]}  ', f'**القسم:** {s["القسم"]}  ', f'**التخصص:** {s["التخصص"]}  ', f'**المعدل:** {s["المعدل التراكمي"]}  ', f'**المرتبة:** {s["تصنيف المرتبة"]}  ', f'**سنة التخرج:** {s["سنة التخرج"]}  ', f'**الإيميل:** {s["الإيميل"]}  ', f'**الهاتف:** {s["الهاتف"]}  ', f'**مشروع التخرج:** {s["مشروع التخرج"]}'])

def h_add(*a):
    *vals, user, role = a
    if not can(role, 'edit'): return DENIED, gr.update()
    return add_student(vals, user)

def h_update(*a):
    *vals, user, role = a
    if not can(role, 'edit'): return DENIED, gr.update()
    return update_student(vals, user)

def h_delete(reg, user, role):
    if not can(role, 'edit'): return DENIED, gr.update()
    return delete_student(reg, user)

def h_import(path, user, role):
    if role != 'مدير': return DENIED, gr.update()
    return import_excel(path, user)

def h_backup(user, role):
    if role != 'مدير': return None
    return backup_database(user)

def h_add_user(u, p, r, user, role):
    if role != 'مدير': return DENIED, gr.update()
    return add_user(u, p, r, user)

def h_del_user(u, user, role):
    if role != 'مدير': return DENIED, gr.update()
    return delete_user(u, user)

def h_users(role): return users_list() if role == 'مدير' else users_list().iloc[0:0]
def h_audit(role): return audit() if role == 'مدير' else audit().iloc[0:0]

# ---------- الواجهة ----------
blocks_kw = _kw(gr.Blocks.__init__, title='نظام إدارة خريجي جامعة البطانة', css=CSS, theme=THEME)
with gr.Blocks(**blocks_kw) as demo:
    gr.HTML(HEADER_HTML)
    with gr.Accordion('🌐 بوابة الخريج العامة — بدون تسجيل دخول', open=False):
        gr.Markdown('يمكن لأي خريج الاستعلام عن بياناته باستخدام رقم التسجيل فقط.')
        pubreg = gr.Textbox(label='رقم التسجيل'); pubbtn = gr.Button('🔎 استعلام عام', variant='primary'); pubout = gr.Markdown()
        pubbtn.click(public_search, pubreg, pubout); pubreg.submit(public_search, pubreg, pubout)

    session_user = gr.State(''); session_role = gr.State('')

    login_box = gr.Group()
    with login_box:
        gr.HTML(LOGIN_LOGO); gr.Markdown('## 🔐 تسجيل الدخول للإدارة')
        user = gr.Textbox(label='اسم المستخدم', autofocus=False)
        pw = gr.Textbox(label='كلمة المرور', type='password')
        lb = gr.Button('🔐 دخول', variant='primary'); ls = gr.Markdown()

    main = gr.Group(visible=False)
    with main:
        with gr.Row():
            refresh = gr.Button('🔄 تحديث لوحة التحكم'); logout = gr.Button('🚪 تسجيل الخروج')
        with gr.Tabs():
            with gr.Tab('📊 لوحة التحكم'):
                dash = gr.HTML()
                alltable = gr.Dataframe(headers=COLUMNS, interactive=False, wrap=True)
                refresh.click(lambda: (dashboard_html(), search()), outputs=[dash, alltable])
            with gr.Tab('🔎 البحث'):
                with gr.Row():
                    q = gr.Textbox(label='بحث شامل'); d = gr.Dropdown(departments(), value='الكل', label='القسم'); y = gr.Dropdown(years(), value='الكل', label='سنة التخرج')
                sb = gr.Button('🔍 بحث', variant='primary'); ss = gr.Markdown(); table = gr.Dataframe(headers=COLUMNS, interactive=False, wrap=True)
                sb.click(do_search, [q, d, y], [ss, table]); q.submit(do_search, [q, d, y], [ss, table])
                gr.Markdown('### 🎓 عرض خريج بالتفصيل')
                regdetail = gr.Textbox(label='رقم التسجيل'); detailbtn = gr.Button('عرض التفاصيل'); detailout = gr.Markdown()
                detailbtn.click(detail, regdetail, detailout); regdetail.submit(detail, regdetail, detailout)
            with gr.Tab('➕ إضافة'):
                with gr.Row(): a1 = gr.Textbox(label='رقم التسجيل *'); a2 = gr.Textbox(label='الرقم الجامعي'); a3 = gr.Textbox(label='الاسم *')
                with gr.Row():
                    a4 = gr.Dropdown(departments()[1:], label='القسم', allow_custom_value=True); a5 = gr.Textbox(label='التخصص'); a6 = gr.Number(label='المعدل'); a7 = gr.Textbox(label='تصنيف المرتبة'); a8 = gr.Number(label='سنة التخرج', precision=0, value=2026)
                with gr.Row(): a9 = gr.Textbox(label='الإيميل'); a10 = gr.Textbox(label='الهاتف'); a11 = gr.Textbox(label='مشروع التخرج')
                a12 = gr.File(label='صورة الخريج', type='filepath', file_types=['image'])
                addb = gr.Button('➕ حفظ', variant='primary'); adds = gr.Markdown()
                addb.click(h_add, [a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, session_user, session_role], [adds, table])
            with gr.Tab('✏️ تعديل / حذف'):
                with gr.Row(): e1 = gr.Textbox(label='رقم التسجيل'); loadb = gr.Button('📂 جلب البيانات')
                with gr.Row(): e2 = gr.Textbox(label='الرقم الجامعي'); e3 = gr.Textbox(label='الاسم'); e4 = gr.Dropdown(departments()[1:], label='القسم', allow_custom_value=True); e5 = gr.Textbox(label='التخصص')
                with gr.Row(): e6 = gr.Number(label='المعدل'); e7 = gr.Textbox(label='تصنيف المرتبة'); e8 = gr.Number(label='سنة التخرج', precision=0); e9 = gr.Textbox(label='الإيميل'); e10 = gr.Textbox(label='الهاتف')
                e11 = gr.Textbox(label='مشروع التخرج'); e12 = gr.File(label='الصورة', type='filepath', file_types=['image'])
                with gr.Row(): ub = gr.Button('💾 حفظ التعديل', variant='primary'); db = gr.Button('🗑️ حذف', variant='stop')
                es = gr.Markdown()
                loadb.click(load_for_edit, e1, [es, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12])
                ub.click(h_update, [e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12, session_user, session_role], [es, table])
                db.click(h_delete, [e1, session_user, session_role], [es, table])
            with gr.Tab('📥 Excel والتقارير'):
                gr.Markdown('استيراد ملف Excel **يستبدل** البيانات الحالية (للمدير فقط).')
                imp = gr.File(label='ملف Excel', type='filepath', file_types=['.xlsx']); ib = gr.Button('📥 استيراد'); ims = gr.Markdown()
                ib.click(h_import, [imp, session_user, session_role], [ims, alltable])
                dl = gr.DownloadButton('⬇️ تصدير Excel'); dl.click(export_excel, outputs=dl)
                backup = gr.Button('💾 إنشاء نسخة احتياطية (للمدير)'); bo = gr.File(label='ملف النسخة الاحتياطية')
                backup.click(h_backup, [session_user, session_role], bo)
                gr.Markdown('### 🖨️ تقرير خريج')
                preg = gr.Textbox(label='رقم التسجيل'); pdf = gr.DownloadButton('⬇️ إنشاء/تحميل تقرير PDF')
                pdf.click(make_pdf, preg, pdf)
            with gr.Tab('👥 المستخدمون'):
                gr.Markdown('### 🔑 تغيير كلمة مروري')
                with gr.Row(): oldp = gr.Textbox(label='كلمة المرور الحالية', type='password'); newp = gr.Textbox(label='كلمة المرور الجديدة', type='password')
                chb = gr.Button('تغيير كلمة المرور'); chs = gr.Markdown()
                chb.click(change_password, [session_user, oldp, newp], chs)
                gr.Markdown('### إدارة المستخدمين (للمدير فقط)')
                ul = gr.Dataframe(interactive=False)
                with gr.Row(): nu = gr.Textbox(label='اسم المستخدم الجديد'); np_ = gr.Textbox(label='كلمة المرور', type='password'); nr = gr.Dropdown(['مدير', 'موظف', 'عرض فقط'], value='موظف', label='الصلاحية')
                ub2 = gr.Button('➕ إضافة مستخدم')
                with gr.Row(): ud = gr.Textbox(label='اسم المستخدم للحذف'); db2 = gr.Button('🗑️ حذف مستخدم')
                us = gr.Markdown(); lu = gr.Button('🔄 عرض المستخدمين')
                lu.click(h_users, session_role, ul)
                ub2.click(h_add_user, [nu, np_, nr, session_user, session_role], [us, ul])
                db2.click(h_del_user, [ud, session_user, session_role], [us, ul])
            with gr.Tab('🧾 سجل التدقيق'):
                al = gr.Dataframe(interactive=False); ab = gr.Button('🔄 عرض/تحديث السجل')
                ab.click(h_audit, session_role, al)

    lb.click(login_action, [user, pw], [login_box, main, ls, session_user, session_role, dash, alltable])
    pw.submit(login_action, [user, pw], [login_box, main, ls, session_user, session_role, dash, alltable])
    logout.click(logout_action, outputs=[login_box, main, ls, session_user, session_role, pw])

if __name__ == '__main__':
    # الاستضافات (Hugging Face / Render / Railway ...) تحدد المنفذ عبر PORT، والافتراضي 7860
    port = int(os.environ.get('PORT', 7860))
    launch_kw = _kw(demo.launch, css=CSS, theme=THEME, favicon_path=FAVICON_PATH, allowed_paths=[os.path.join(BASE, 'assets')])
    if 'css' in blocks_kw: launch_kw.pop('css', None); launch_kw.pop('theme', None)
    demo.queue(default_concurrency_limit=8).launch(server_name='0.0.0.0', server_port=port, show_error=True, **launch_kw)
