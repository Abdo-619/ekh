import os,re,shutil,zipfile,tempfile
from datetime import datetime
import pandas as pd
import time
from data import COLUMNS,DATA_FILE,DB_FILE,DATA_DIR,PHOTOS_DIR,connect,get_df,save_dataframe,hash_password,verify_password

def norm(v):
    v=str(v or '').strip().lower()
    for a,b in {'أ':'ا','إ':'ا','آ':'ا','ة':'ه','ى':'ي','ؤ':'و','ئ':'ي'}.items(): v=v.replace(a,b)
    return re.sub(r'\s+',' ',v)

def search(query='',department='الكل',year='الكل'):
    x=get_df()
    if department and department!='الكل': x=x[x['القسم'].astype(str)==department]
    if year and year!='الكل': x=x[x['سنة التخرج'].astype(str)==str(year)]
    q=norm(query)
    if q:
        mask=pd.Series(False,index=x.index)
        for c in ['الاسم','الرقم الجامعي','رقم التسجيل','القسم','التخصص','الهاتف','الإيميل']: mask |= x[c].map(norm).str.contains(q,regex=False,na=False)
        x=x[mask]
    return x.reset_index(drop=True)

def departments(): return ['الكل']+sorted(get_df()['القسم'].dropna().astype(str).unique().tolist())
def years(): return ['الكل']+sorted({str(v).split('.')[0] for v in get_df()['سنة التخرج'].dropna() if str(v).strip()},reverse=True)
def stats():
    x=get_df(); return len(x),x['القسم'].value_counts().to_dict()

_FAILS={}
def authenticate(user,password):
    u=str(user or '').strip(); now=time.time()
    n,t=_FAILS.get(u,(0,0))
    if n>=5 and now-t<300: return False,'locked'
    c=connect(); r=c.execute('SELECT role,password FROM users WHERE username=?',(u,)).fetchone(); c.close()
    if r and verify_password(password,r['password']): _FAILS.pop(u,None); return True,r['role']
    _FAILS[u]=(n+1 if now-t<300 else 1,now); return False,''

# الصلاحيات: مدير = كل شيء، موظف = إضافة/تعديل/حذف، عرض فقط = بحث وعرض
def can(role,action):
    if role=='مدير': return True
    if role=='موظف': return action in ('edit',)
    return False
DENIED='⛔ ليست لديك صلاحية تنفيذ هذه العملية.'

def change_password(user,old,new):
    if not user: return '❌ سجّل الدخول أولاً.'
    if len(str(new or ''))<4: return '❌ كلمة المرور الجديدة قصيرة (4 أحرف على الأقل).'
    ok,_=authenticate(user,old)
    if not ok: return '❌ كلمة المرور الحالية غير صحيحة.'
    c=connect(); c.execute('UPDATE users SET password=? WHERE username=?',(hash_password(new),user)); c.execute('INSERT INTO audit_log(username,action,details) VALUES(?,?,?)',(user,'تغيير كلمة المرور',user)); c.commit(); c.close(); return '✅ تم تغيير كلمة المرور.'

def save_photo(path):
    """نسخ صورة الخريج إلى مجلد دائم بدلاً من المسار المؤقت."""
    if not path or not os.path.exists(str(path)): return path or ''
    if os.path.dirname(os.path.abspath(path))==os.path.abspath(PHOTOS_DIR): return path
    ext=os.path.splitext(path)[1].lower() or '.jpg'
    dest=os.path.join(PHOTOS_DIR,f'{int(time.time()*1000)}{ext}'); shutil.copy(path,dest); return dest
def users_list():
    c=connect(); x=pd.read_sql_query('SELECT username AS "اسم المستخدم", role AS "الصلاحية" FROM users',c); c.close(); return x
def add_user(username,password,role,actor):
    if not username or not password: return '❌ اسم المستخدم وكلمة المرور مطلوبان.',users_list()
    try:
        c=connect(); c.execute('INSERT INTO users VALUES(?,?,?)',(username.strip(),hash_password(password),role)); c.execute('INSERT INTO audit_log(username,action,details) VALUES(?,?,?)',(actor,'إضافة مستخدم',username)); c.commit(); c.close(); return '✅ تمت إضافة المستخدم.',users_list()
    except Exception: return '⚠️ اسم المستخدم موجود مسبقاً.',users_list()
def delete_user(username,actor):
    if username=='admin': return '❌ لا يمكن حذف المدير الأساسي.',users_list()
    c=connect(); c.execute('DELETE FROM users WHERE username=?',(username,)); c.execute('INSERT INTO audit_log(username,action,details) VALUES(?,?,?)',(actor,'حذف مستخدم',username)); c.commit(); c.close(); return '🗑️ تم حذف المستخدم.',users_list()

def audit():
    c=connect(); x=pd.read_sql_query('SELECT username AS "المستخدم", action AS "العملية", registration AS "رقم التسجيل", details AS "التفاصيل", created_at AS "التاريخ" FROM audit_log ORDER BY id DESC LIMIT 300',c); c.close(); return x

def add_student(values,actor='admin'):
    reg,uid,name,dept,spec,gpa,rank,year,email,phone,project,photo=values
    x=get_df(); reg=str(reg or '').strip(); name=str(name or '').strip()
    if not reg or not name:return '❌ رقم التسجيل والاسم مطلوبان.',x
    if reg in x['رقم التسجيل'].astype(str).str.strip().tolist():return '⚠️ رقم التسجيل موجود مسبقاً.',x
    row=dict(zip(COLUMNS,[reg,uid or '',name,dept or '',spec or '',gpa or '',rank or '',year or '',email or '',phone or '',project or '',save_photo(photo)]))
    y=pd.concat([x,pd.DataFrame([row])],ignore_index=True); out=save_dataframe(y,actor,'إضافة خريج'); return '✅ تمت إضافة الخريج.',out

def update_student(values,actor='admin'):
    reg,uid,name,dept,spec,gpa,rank,year,email,phone,project,photo=values; x=get_df(); m=x['رقم التسجيل'].astype(str).str.strip()==str(reg or '').strip()
    if not m.any():return '❌ لم يتم العثور على السجل.',x
    i=x.index[m][0]
    for c,v in zip(COLUMNS,[reg,uid,name,dept,spec,gpa,rank,year,email,phone,project,save_photo(photo) or x.at[i,'الصورة']]): x.at[i,c]=v or ''
    return '✅ تم تعديل البيانات.',save_dataframe(x,actor,'تعديل خريج')

def delete_student(reg,actor='admin'):
    x=get_df(); m=x['رقم التسجيل'].astype(str).str.strip()==str(reg or '').strip()
    if not m.any(): return '❌ لم يتم العثور على السجل.',x
    x=x[~m].reset_index(drop=True); return '🗑️ تم حذف الخريج.',save_dataframe(x,actor,'حذف خريج')

def import_excel(path,actor='admin'):
    if not path:return '❌ اختر ملف Excel.',get_df()
    try:
        x=pd.read_excel(path,dtype=str).fillna('')
        return '✅ تم استيراد البيانات بنجاح.',save_dataframe(x,actor,'استيراد Excel')
    except Exception as e:return f'❌ خطأ: {e}',get_df()
def export_excel():
    from data import export_excel_file
    return export_excel_file()

def backup_database(actor='admin'):
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S'); out=os.path.join(tempfile.gettempdir(),f'backup_graduates_{stamp}.zip')
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.write(DB_FILE,os.path.basename(DB_FILE));
        if os.path.exists(DATA_FILE): z.write(DATA_FILE,os.path.basename(DATA_FILE))
    c=connect(); c.execute('INSERT INTO audit_log(username,action,details) VALUES(?,?,?)',(actor,'نسخة احتياطية',out)); c.commit(); c.close(); return out

def get_student(reg):
    x=get_df(); m=x['رقم التسجيل'].astype(str).str.strip()==str(reg or '').strip(); return x[m].iloc[0].to_dict() if m.any() else None

def public_search(reg):
    s=get_student(reg)
    if not s:return '❌ لم يتم العثور على خريج بهذا الرقم.'
    return '\n'.join([f'### 🎓 بيانات الخريج',f'**الاسم:** {s["الاسم"]}',f'**رقم التسجيل:** {s["رقم التسجيل"]}',f'**الرقم الجامعي:** {s["الرقم الجامعي"]}',f'**القسم:** {s["القسم"]}',f'**التخصص:** {s["التخصص"]}',f'**المعدل التراكمي:** {s["المعدل التراكمي"]}',f'**سنة التخرج:** {s["سنة التخرج"]}'])

def load_for_edit(reg):
    s=get_student(reg)
    if not s: return ('❌ لم يتم العثور على السجل.',)+('',)*11
    def g(k):
        v=s[k]; return v
    return ('✅ تم جلب البيانات، عدّل ما تريد ثم احفظ.',g('الرقم الجامعي'),g('الاسم'),g('القسم'),g('التخصص'),g('المعدل التراكمي') or None,g('تصنيف المرتبة'),g('سنة التخرج') or None,g('الإيميل'),g('الهاتف'),g('مشروع التخرج'),None)
