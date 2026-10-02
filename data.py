import os, sqlite3, hashlib, secrets, tempfile, pandas as pd

BASE_DIR=os.path.dirname(os.path.abspath(__file__))

def _writable_dir(path):
    try:
        os.makedirs(path,exist_ok=True)
        t=os.path.join(path,'.w'); open(t,'w').close(); os.remove(t); return path
    except Exception:
        return None

# مجلد البيانات: يمكن تغييره بمتغير البيئة DATA_DIR (مثلاً /data على الاستضافات التي توفر قرصاً دائماً)
DATA_DIR=_writable_dir(os.environ.get('DATA_DIR') or BASE_DIR) or _writable_dir(os.path.join(tempfile.gettempdir(),'graduates_data'))
PHOTOS_DIR=_writable_dir(os.path.join(DATA_DIR,'photos')) or DATA_DIR
DB_FILE=os.path.join(DATA_DIR,'graduates.db')
DATA_FILE=os.path.join(DATA_DIR,'graduates.xlsx')
SEED_FILE=os.path.join(BASE_DIR,'graduates.xlsx')   # الملف المرفق مع المشروع لبذر البيانات الأولية
if DATA_DIR!=BASE_DIR:
    import shutil
    if not os.path.exists(DB_FILE) and os.path.exists(os.path.join(BASE_DIR,'graduates.db')):
        try: shutil.copy(os.path.join(BASE_DIR,'graduates.db'),DB_FILE)
        except Exception: pass

# ---------- كلمات المرور (مشفرة PBKDF2) ----------
def hash_password(p):
    salt=secrets.token_hex(8); h=hashlib.pbkdf2_hmac('sha256',str(p).encode(),salt.encode(),100_000).hex()
    return f'pbkdf2${salt}${h}'
def verify_password(p,stored):
    stored=str(stored or '')
    if not stored.startswith('pbkdf2$'): return secrets.compare_digest(stored,str(p))  # قيمة قديمة غير مشفرة
    try: _,salt,h=stored.split('$'); return secrets.compare_digest(hashlib.pbkdf2_hmac('sha256',str(p).encode(),salt.encode(),100_000).hex(),h)
    except Exception: return False
COLUMNS=['رقم التسجيل','الرقم الجامعي','الاسم','القسم','التخصص','المعدل التراكمي','تصنيف المرتبة','سنة التخرج','الإيميل','الهاتف','مشروع التخرج','الصورة']

def connect():
    c=sqlite3.connect(DB_FILE,timeout=30); c.row_factory=sqlite3.Row; return c

def init_db():
    c=connect()
    c.execute('''CREATE TABLE IF NOT EXISTS graduates (id INTEGER PRIMARY KEY AUTOINCREMENT, registration TEXT UNIQUE NOT NULL, university_id TEXT, name TEXT NOT NULL, department TEXT, specialization TEXT, gpa TEXT, rank TEXT, graduation_year TEXT, email TEXT, phone TEXT, project TEXT, photo TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL, role TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, action TEXT, registration TEXT, details TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin',?,'مدير')",(hash_password(os.environ.get('ADMIN_PASSWORD') or '1234'),))
    # ترحيل كلمات المرور القديمة غير المشفرة
    for u,p in c.execute('SELECT username,password FROM users').fetchall():
        if not str(p).startswith('pbkdf2$'): c.execute('UPDATE users SET password=? WHERE username=?',(hash_password(p),u))
    # عند ضبط ADMIN_PASSWORD في الاستضافة تُطبَّق على حساب المدير
    if os.environ.get('ADMIN_PASSWORD'): c.execute("UPDATE users SET password=? WHERE username='admin'",(hash_password(os.environ['ADMIN_PASSWORD']),))
    c.commit(); c.close()
    if not os.path.exists(DB_FILE) or _count()==0: seed_from_excel_or_builtin()

def _count():
    c=connect(); n=c.execute('SELECT COUNT(*) FROM graduates').fetchone()[0]; c.close(); return n

def seed_from_excel_or_builtin():
    for f in (DATA_FILE,SEED_FILE):
      if os.path.exists(f):
        try:
            x=pd.read_excel(f,dtype=str).fillna('')
            if len(x):
                save_dataframe(x, 'system', 'استيراد البيانات الأولية'); return
        except Exception: pass
    # Fallback data used by the original project.
    rows=[]
    nis=[('BI8083','','ابرار شاكر عطا المولى حسين',3.35,'الثانية-القسم الأول'),('BI8104','','مرحب مهدي احمد محمد',3.24,'الثانية-القسم الأول'),('BI8105','','مروة عبد الله بابكر هونا',3.05,'الثانية-القسم الأول'),('BI8085','','ابوبكر بله مصطفى عبد الله',2.89,'الثانية-القسم الثاني'),('BI8108','','مهند النيل نور فضل المولى',2.88,'الثانية-القسم الثاني'),('BI8098','','فاطمة العوض ابراهيم احمد',2.81,'الثانية-القسم الثاني'),('BI8088','','امنا عبد الرحمن على محمد',2.70,'الثانية-القسم الثاني'),('BI8081','','ابتسام عزيز الدين محمد عبد الله',2.67,'الثانية-القسم الثاني'),('BI8093','','سعدية الشيخ عبد الله مرسال',2.50,'الثانية-القسم الثاني'),('BI8096','','عصام بكرى عبد الله حمود',2.44,'الثالثة'),('BI8089','','انعام زكى بابكر محمد',2.35,'الثالثة'),('BI8102','','مؤيد ابراهيم احمد الماضي',2.34,'الثالثة'),('BI8086','','الياس صابر الياس صالح',2.33,'الثالثة'),('BI8087','','امنا احمد مختار عبد الله',2.31,'الثالثة'),('BI8112','','المعز الرفيع مصطفى الخضر',2.02,'الثالثة')]
    for r,u,n,g,k in nis: rows.append([r,u,n,'نظم المعلومات','نظم المعلومات',g,k,'2026','','','',''])
    cs=[('BS8017','17-11182050','شيماء مجدى الحسين قاسم السيد',3.22,'الثانية-القسم الأول'),('BS8021','17-11216193','على سعد الدين احمد محمد',3.17,'الثانية-القسم الأول'),('BS8029','17-11045552','مريم عبد المنعم سعد محمد',3.17,'الثانية-القسم الأول'),('BS8035','17-11256382','ندى كمال الدين عمر احمد',3.12,'الثانية-القسم الأول'),('BS8051','17-11182711','سعيد خاطر احمد محمد',3.10,'الثانية-القسم الأول'),('BS8015','17-11182284','ريماء منصور الامين منصور',3.01,'الثانية-القسم الأول'),('BS8009','17-111548894','تبيان نور الدين دفع الله محمد',3.01,'الثانية-القسم الأول'),('BS8024','17-111548894','فاطمة مروان على عثمان',2.97,'الثانية-القسم الأول'),('BS8038','17-11148741','ودية عماد عباس محمد',2.96,'الثانية-القسم الأول'),('BS8003','17-11621000','اروى يوسف الريح عبد الله',2.83,'الثانية-القسم الأول'),('BS8034','17-21014499','نادرين محمد بدوى احمد',2.77,'الثانية-القسم الأول'),('BS8023','17-21015579','عيسى اكبر هارون اكبر',2.70,'الثانية-القسم الأول'),('BS8039','17-11196320','يسرا عبد الجبار حامد محمد',2.55,'الثانية-القسم الأول'),('BS8032','17-11248590','موسى إبراهيم محمد عيسى',2.41,'الثالثة'),('BS8014','17-11249552','رشا محبوب عينها حميده',2.36,'الثالثة'),('BS8007','17-11357353','اميرة خلف الله على عبد الرحمن',2.34,'الثالثة'),('BS8011','17-11111752','حفصة عبد الحافظ محمد عبد الرحمن',2.34,'الثالثة'),('BS8022','17-22000604','عماد الدين محمد عبد الله محمد',2.34,'الثالثة'),('BS8058','17-21001716','مصطفى محمد قرشي عبدالفتاح',2.29,'الثالثة'),('BS8001','17-21001716','احمد عبد الرحمن داود عبد الرحمن',2.23,'الثالثة'),('BS8028','17-11240562','مروة خلف الله محمد الحسين',2.20,'الثالثة'),('BS8016','16-110467062','أمل حمد بابر محمد',2.11,'الثالثة'),('BS8057','16-110417379','التجاني محمد احمد الهادي محمد',2.09,'الثالثة'),('BS8029','16-110417379','محمد احمد عبداللطيف فضل المولى احمد',2.06,'الثالثة'),('BS8056','16-110417379','محمد الفاتح عادل عطية عبدالهادي',2.04,'الثالثة')]
    for r,u,n,g,k in cs: rows.append([r,u,n,'علوم الحاسوب','علوم الحاسوب',g,k,'2026','','','',''])
    it=[('BT8055','17-11268051',3.60,'الأولى'),('BT8049','17-11542634',3.53,'الأولى'),('BT8046','17-21033421',3.20,'الثانية-القسم الأول'),('BT8098','17-12004376',3.08,'الثانية-القسم الأول'),('BT8095','17-12004376',3.07,'الثانية-القسم الأول'),('BT8044','17-11085978',2.85,'الثانية-القسم الثاني'),('BT8054','17-11083961',2.79,'الثانية-القسم الثاني'),('BT8082','17-11549714',2.79,'الثانية-القسم الثاني'),('BT8076','17-11010349',2.73,'الثانية-القسم الثاني'),('BT8077','17-11042769',2.69,'الثانية-القسم الثاني'),('BT8064','17-11010730',2.64,'الثانية-القسم الثاني'),('BT8057','17-11313821',2.61,'الثانية-القسم الثاني'),('BT8087','17-23001680',2.58,'الثانية-القسم الثاني'),('BT8066','17-11011687',2.57,'الثانية-القسم الثاني'),('BT8043','17-11622238',2.54,'الثانية-القسم الثاني'),('BT8062','17-1102036',2.53,'الثانية-القسم الثاني'),('BT8092','17-11554608',2.41,'الثانية'),('BT8060','17-11456563',2.37,'الثانية'),('BT8077','17-11337912',2.32,'الثانية'),('BT8086','17-23002853',2.21,'الثانية'),('BT8070','17-11365511',2.10,'الثانية'),('BT8059','17-11002774',2.07,'الثانية'),('BT8073','17-21024060',2.03,'الثانية')]
    for r,u,g,k in it: rows.append([r,u,'أضف الاسم هنا','تقانة المعلومات','تقانة المعلومات',g,k,'2026','','','',''])
    save_dataframe(pd.DataFrame(rows,columns=COLUMNS),'system','إنشاء البيانات الأولية')

def get_df():
    c=connect(); x=pd.read_sql_query('SELECT registration AS "رقم التسجيل", university_id AS "الرقم الجامعي", name AS "الاسم", department AS "القسم", specialization AS "التخصص", gpa AS "المعدل التراكمي", rank AS "تصنيف المرتبة", graduation_year AS "سنة التخرج", email AS "الإيميل", phone AS "الهاتف", project AS "مشروع التخرج", photo AS "الصورة" FROM graduates ORDER BY name',c); c.close(); return x.fillna('')

def save_dataframe(x,username='system',action='حفظ البيانات'):
    x=x.copy().fillna('')
    for col in COLUMNS:
        if col not in x: x[col]=''
    c=connect(); c.execute('DELETE FROM graduates')
    for _,r in x[COLUMNS].iterrows():
        if str(r['رقم التسجيل']).strip() and str(r['الاسم']).strip():
            c.execute('INSERT OR REPLACE INTO graduates(registration,university_id,name,department,specialization,gpa,rank,graduation_year,email,phone,project,photo) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',tuple(str(r[col]) for col in COLUMNS))
    c.execute('INSERT INTO audit_log(username,action,details) VALUES(?,?,?)',(username,action,f'{len(x)} سجل'))
    c.commit(); c.close(); export_excel_file(x)
    return get_df()

def export_excel_file(x=None):
    if x is None: x=get_df()
    x.to_excel(DATA_FILE,index=False); return DATA_FILE

init_db()
