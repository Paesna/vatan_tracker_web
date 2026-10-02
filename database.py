"""
[TR] Veritabanı Modülü / [EN] Database Module
[TR] Tüm PostgreSQL (Supabase) / SQLite bağlantılarını ve SQLAlchemy ORM modellerini yönetir. / [EN] Handles all PostgreSQL (Supabase) / SQLite connections and ORM models using SQLAlchemy.
[TR] Performans: bot her taramada tüm ürün durumunu TEK sorguda yükler, tüm değişiklikleri TEK işlemde (transaction)
     toplu yazar. Eskiden ürün başına 2-3 sorgu atılıyordu (Supabase'de binlerce ürün = dakikalar).
[EN] Performance: the bot loads the whole product state with ONE query per scan and writes all changes in ONE
     transaction using bulk statements. Previously it issued 2-3 queries per product (minutes on Supabase).
"""

import datetime
import json

from sqlalchemy import (create_engine, Column, String, Float, Integer, DateTime, ForeignKey, Index, Text,
                        text, inspect, insert, update, select, func)
from sqlalchemy.orm import declarative_base, sessionmaker

import config


# [TR] Her zaman Türkiye Saatini (UTC+3) döndüren yardımcı fonksiyon
# [EN] Helper function that always returns Turkey Time (UTC+3)
def get_tr_time():
    # Render'da çalışınca UTC dönüyor, bunu 3 saat ileri alarak Türkiye saati yapıyoruz.
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=3)


Base = declarative_base()


class Product(Base):
    __tablename__ = 'products'
    code = Column(String, primary_key=True)
    name = Column(String)
    url = Column(String)
    image_url = Column(String, nullable=True)
    base_price = Column(Float)
    first_seen = Column(DateTime)
    # [TR] v2 sütunları (eski veritabanlarına init_db() ekler) / [EN] v2 columns (added to old DBs by init_db())
    site = Column(String, nullable=True)
    category = Column(String, nullable=True)
    specs = Column(Text, nullable=True)
    # [TR] Son fiyat/stok burada da tutulur; panel tüm geçmişi okumak zorunda kalmaz.
    # [EN] Latest price/stock are denormalized here so the dashboard doesn't scan the whole history.
    last_price = Column(Float, nullable=True)
    in_stock = Column(Integer, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    last_change = Column(DateTime, nullable=True)


class PriceHistory(Base):
    __tablename__ = 'price_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, ForeignKey('products.code'))
    price = Column(Float)
    in_stock = Column(Integer)
    timestamp = Column(DateTime)
    __table_args__ = (Index("ix_price_history_code_timestamp", "code", "timestamp"),)


class SystemStatus(Base):
    __tablename__ = 'system_status'
    id = Column(Integer, primary_key=True)
    last_scan = Column(DateTime)


class TargetStatus(Base):
    """[TR] Site x kategori başına son tarama sağlığı. / [EN] Last crawl health per site x category."""
    __tablename__ = 'target_status'
    key = Column(String, primary_key=True)
    site = Column(String)
    category = Column(String)
    last_run = Column(DateTime)
    last_ok = Column(DateTime, nullable=True)
    ok = Column(Integer)
    blocked = Column(Integer)
    product_count = Column(Integer)
    pages = Column(Integer)
    requests = Column(Integer)
    duration = Column(Float)
    stop_reason = Column(String, nullable=True)
    error = Column(Text, nullable=True)


class ScanStat(Base):
    """[TR] Her tarama turunun hız istatistikleri. / [EN] Throughput statistics of every scan round."""
    __tablename__ = 'scan_stats'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime)
    duration = Column(Float)
    targets = Column(Integer)
    ok_targets = Column(Integer)
    blocked = Column(Integer)
    requests = Column(Integer)
    pages = Column(Integer)
    products = Column(Integer)
    bytes = Column(Integer)
    pages_per_sec = Column(Float)
    products_per_sec = Column(Float)
    avg_latency = Column(Float)
    parse_seconds = Column(Float)
    db_seconds = Column(Float)
    changes = Column(Integer)
    alerts = Column(Integer)
    __table_args__ = (Index("ix_scan_stats_timestamp", "timestamp"),)


def _motor_olustur(url):
    if url.startswith("sqlite"):
        # [TR] Bot ve dashboard aynı SQLite dosyasını kullandığında kilitlenme hatalarını önlemek için bekleme süresi.
        # [EN] Timeout to avoid "database is locked" errors when bot and dashboard share the same SQLite file.
        return create_engine(url, connect_args={"timeout": 30})
    # [TR] pool_pre_ping: 7/24 çalışırken sunucunun kapattığı bayat bağlantıları otomatik yeniler.
    #      values_plus_batch: toplu UPDATE'leri satır satır değil, 100'lük paketlerle gönderir (Supabase'de büyük fark).
    # [EN] pool_pre_ping: transparently replaces stale connections dropped by the server during 24/7 operation.
    #      values_plus_batch: sends bulk UPDATEs in pages of 100 instead of row by row (big win on Supabase).
    sema = url.split(":", 1)[0]
    ek = {"executemany_mode": "values_plus_batch"} if sema in ("postgresql", "postgresql+psycopg2") else {}
    return create_engine(url, pool_pre_ping=True, **ek)


# [TR] Veritabanı motoru ve oturum oluşturucu / [EN] Database engine and session maker
engine = _motor_olustur(config.DB_URL)
SessionLocal = sessionmaker(bind=engine)


def configure_engine(url):
    """[TR] Motoru başka bir veritabanına yönlendirir (testler/benchmark). / [EN] Re-points the engine (tests)."""
    global engine
    engine = _motor_olustur(url)
    SessionLocal.configure(bind=engine)
    return engine


_V2_SUTUNLAR = {
    "image_url": "VARCHAR", "site": "VARCHAR", "category": "VARCHAR", "specs": "TEXT",
    "last_price": "FLOAT", "in_stock": "INTEGER", "last_seen": "TIMESTAMP", "last_change": "TIMESTAMP",
}


def init_db():
    """
    [TR] Tabloları oluşturur ve eski şemayı v2'ye taşır (eksik sütunlar, indeks, site/kategori/son fiyat doldurma).
    [EN] Creates tables and migrates the old schema to v2 (missing columns, index, site/category/last price backfill).
    """
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    mevcut = {col['name'] for col in inspector.get_columns('products')}
    eksik = [s for s in _V2_SUTUNLAR if s not in mevcut]
    if eksik:
        with engine.begin() as conn:
            for sutun in eksik:
                conn.execute(text(f"ALTER TABLE products ADD COLUMN {sutun} {_V2_SUTUNLAR[sutun]}"))
    with engine.begin() as conn:
        # [TR] Eski kurulumlarda geçmiş tablosunda indeks yoktu; ürün başına son kayıt sorgusu tüm tabloyu tarıyordu.
        # [EN] Old installs had no index on history; the per-product latest-row query scanned the whole table.
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_price_history_code_timestamp ON price_history (code, timestamp)"))
    _v2_doldur()


def _v2_doldur():
    """[TR] Eski satırlar için site, kategori, özellik ve son fiyat/stok bilgisini doldurur. / [EN] Backfills v2 fields."""
    import categories
    with engine.connect() as conn:
        eksikler = conn.execute(
            select(Product.code, Product.name, Product.url, Product.site, Product.category, Product.specs,
                   Product.last_price, Product.base_price, Product.first_seen)
            .where((Product.site.is_(None)) | (Product.category.is_(None)) | (Product.last_price.is_(None)))
        ).all()
        if not eksikler:
            return
        # [TR] Ürün başına en son geçmiş satırı (tipli sorgu: SQLite'ta da tarih nesnesi döner).
        # [EN] Latest history row per product (typed query: returns datetime objects on SQLite too).
        son_id = select(PriceHistory.code, func.max(PriceHistory.id).label("mid")).group_by(PriceHistory.code).subquery()
        son = {r.code: r for r in conn.execute(
            select(PriceHistory.code, PriceHistory.price, PriceHistory.in_stock, PriceHistory.timestamp)
            .join(son_id, PriceHistory.id == son_id.c.mid)).all()}

    guncellemeler = []
    for r in eksikler:
        site = r.site or config.site_bul(r.code, r.url)
        kategori = r.category or categories.kategori_tahmin_et(r.name)
        gecmis = son.get(r.code)
        fiyat = r.last_price if r.last_price is not None else (gecmis.price if gecmis else r.base_price)
        stok = gecmis.in_stock if gecmis else 0
        ozellik = r.specs or json.dumps(categories.ozellikleri_cikar(kategori, r.name), ensure_ascii=False)
        zaman = gecmis.timestamp if gecmis else r.first_seen
        guncellemeler.append({"code": r.code, "site": site, "category": kategori, "specs": ozellik,
                              "last_price": fiyat, "in_stock": stok, "last_change": zaman, "last_seen": zaman})
    with SessionLocal.begin() as session:
        session.execute(update(Product), guncellemeler)
    print(f"🛠️ [TR] {len(guncellemeler)} eski ürün kaydı v2 şemasına taşındı. / [EN] Migrated {len(guncellemeler)} legacy rows to v2.")


# =====================================================================================
# [TR] TOPLU (BATCH) İŞLEMLER - bot bunları kullanır / [EN] BULK OPERATIONS - used by the bot
# =====================================================================================

def durum_yukle():
    """
    [TR] Tüm ürünlerin karşılaştırma için gereken durumunu TEK sorguda yükler.
    [EN] Loads the comparison state of every product with ONE query.

    Returns:
        dict: code -> {"name", "url", "image_url", "base_price", "site", "category", "last_price", "in_stock",
                       "last_seen", "last_change"}
    """
    with engine.connect() as conn:
        satirlar = conn.execute(select(
            Product.code, Product.name, Product.url, Product.image_url, Product.base_price, Product.site,
            Product.category, Product.last_price, Product.in_stock, Product.last_seen, Product.last_change)).all()
    return {r.code: dict(r._mapping) for r in satirlar}


def toplu_yaz(yeni_urunler=(), guncellemeler=None, gecmis=(), hedef_durumlari=(), istatistik=None, son_tarama=None):
    """
    [TR] Bir taramanın tüm değişikliklerini tek işlemde (transaction) yazar. / [EN] Writes a scan's changes atomically.

    Args:
        yeni_urunler: [TR] products satırları (dict listesi). / [EN] products rows.
        guncellemeler: [TR] {code: {sütun: değer}} / [EN] {code: {column: value}}
        gecmis: [TR] price_history satırları. / [EN] price_history rows.
        hedef_durumlari: [TR] target_status satırları. / [EN] target_status rows.
        istatistik: [TR] scan_stats satırı. / [EN] scan_stats row.
        son_tarama: [TR] system_status.last_scan değeri. / [EN] value for system_status.last_scan.
    """
    with SessionLocal.begin() as session:
        if yeni_urunler:
            session.execute(insert(Product), list(yeni_urunler))
        if guncellemeler:
            session.execute(update(Product), [{"code": kod, **alanlar} for kod, alanlar in guncellemeler.items()])
        if gecmis:
            session.execute(insert(PriceHistory), list(gecmis))
        if hedef_durumlari:
            # [TR] merge() satır başına SELECT atar; mevcut anahtarları bir kez okuyup toplu ekle/güncelle.
            # [EN] merge() issues a SELECT per row; read existing keys once, then bulk insert/update.
            mevcut = set(session.scalars(select(TargetStatus.key)).all())
            yeni = [d for d in hedef_durumlari if d["key"] not in mevcut]
            # [TR] Başarısız turda "son başarı" zamanı silinmesin. / [EN] Keep the last success time on failures.
            eski = [{k: v for k, v in d.items() if not (k == "last_ok" and v is None)}
                    for d in hedef_durumlari if d["key"] in mevcut]
            if yeni:
                session.execute(insert(TargetStatus), yeni)
            if eski:
                session.execute(update(TargetStatus), eski)
        if istatistik:
            session.add(ScanStat(**istatistik))
        if son_tarama is not None:
            status = session.get(SystemStatus, 1) or session.query(SystemStatus).first()
            if status is None:
                session.add(SystemStatus(id=1, last_scan=son_tarama))
            else:
                status.last_scan = son_tarama


# =====================================================================================
# [TR] PANEL SORGULARI / [EN] DASHBOARD QUERIES
# =====================================================================================

def urun_tablosu():
    """[TR] Panel için tüm ürünler (son fiyat ürün satırında). / [EN] All products for the dashboard."""
    with engine.connect() as conn:
        satirlar = conn.execute(select(Product)).mappings().all()
    return [dict(r) for r in satirlar]


def fiyat_gecmisi(code):
    """[TR] Tek bir ürünün fiyat geçmişi (indeksli sorgu). / [EN] Price history of one product (indexed)."""
    with engine.connect() as conn:
        satirlar = conn.execute(select(PriceHistory.timestamp, PriceHistory.price, PriceHistory.in_stock)
                                .where(PriceHistory.code == code).order_by(PriceHistory.timestamp)).all()
    return [dict(r._mapping) for r in satirlar]


def pencere_fiyatlari(baslangic):
    """[TR] Verilen zamandan beri ürün başına en yüksek/en düşük fiyat. / [EN] Max/min price per product since t."""
    with engine.connect() as conn:
        satirlar = conn.execute(select(PriceHistory.code, func.max(PriceHistory.price).label("max_price"),
                                       func.min(PriceHistory.price).label("min_price"))
                                .where(PriceHistory.timestamp >= baslangic)
                                .group_by(PriceHistory.code)).all()
    return {r.code: (r.max_price, r.min_price) for r in satirlar}


def tum_zamanlar_en_dusuk():
    """[TR] Ürün başına tüm zamanların en düşük fiyatı. / [EN] All-time lowest price per product."""
    with engine.connect() as conn:
        satirlar = conn.execute(select(PriceHistory.code, func.min(PriceHistory.price).label("p"))
                                .group_by(PriceHistory.code)).all()
    return {r.code: r.p for r in satirlar}


def hedef_durumlari():
    """[TR] Site sağlığı tablosu. / [EN] Site health table."""
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(select(TargetStatus)).mappings().all()]


def tarama_istatistikleri(limit=300):
    """[TR] Son taramaların hız istatistikleri (eskiden yeniye). / [EN] Recent scan throughput (oldest first)."""
    with engine.connect() as conn:
        satirlar = conn.execute(select(ScanStat).order_by(ScanStat.id.desc()).limit(limit)).mappings().all()
    return [dict(r) for r in reversed(satirlar)]


# =====================================================================================
# [TR] ESKİ TEKİL FONKSİYONLAR (geriye dönük uyumluluk) / [EN] LEGACY SINGLE-ROW FUNCTIONS (compatibility)
# =====================================================================================

def is_db_empty():
    """[TR] Products tablosunun boş olup olmadığını kontrol eder. / [EN] Checks if the products table is empty."""
    with SessionLocal() as session:
        count = session.query(Product).count()
        return count == 0


def get_product_base(code):
    """[TR] Ürünün base (temel) fiyat bilgisini getirir. / [EN] Fetches the base price info of the product."""
    with SessionLocal() as session:
        product = session.query(Product).filter_by(code=code).first()
        if product:
            return {"base_price": product.base_price, "url": product.url, "image_url": product.image_url}
    return None


def get_last_history(code):
    """[TR] Ürünün kaydedilen en son fiyat geçmişini getirir. / [EN] Fetches the latest recorded price history of the product."""
    with SessionLocal() as session:
        history = session.query(PriceHistory).filter_by(code=code).order_by(PriceHistory.timestamp.desc()).first()
        if history:
            return {"price": history.price, "in_stock": history.in_stock}
    return None


def add_product(code, name, url, base_price, image_url=None, site=None, category=None, specs=None):
    """[TR] Yeni ürünü tabloya ekler. / [EN] Adds a new product to the table."""
    with SessionLocal() as session:
        # [TR] Ürün zaten varsa eklemez (IGNORE mantığı) / [EN] Does not add if product already exists (IGNORE logic)
        exists = session.query(Product).filter_by(code=code).first()
        if not exists:
            simdi = get_tr_time()
            session.add(Product(code=code, name=name, url=url, image_url=image_url, base_price=base_price,
                                first_seen=simdi, site=site or config.site_bul(code, url), category=category,
                                specs=specs, last_price=base_price, last_seen=simdi, last_change=simdi))
            session.commit()


def update_product_image(code, image_url):
    """[TR] Mevcut bir ürünün resim linkini günceller. / [EN] Updates the image url of an existing product."""
    with SessionLocal() as session:
        product = session.query(Product).filter_by(code=code).first()
        if product and not product.image_url:
            product.image_url = image_url
            session.commit()


def update_base_price(code, new_base_price):
    """[TR] Ürünün base fiyatını günceller. / [EN] Updates the base price of the product."""
    with SessionLocal() as session:
        product = session.query(Product).filter_by(code=code).first()
        if product:
            product.base_price = new_base_price
            session.commit()


def add_price_history(code, price, in_stock):
    """[TR] Fiyat/stok değiştiğinde geçmişe yeni satır ekler. / [EN] Adds a new row to history when price/stock changes."""
    with SessionLocal() as session:
        simdi = get_tr_time()
        session.add(PriceHistory(code=code, price=price, in_stock=in_stock, timestamp=simdi))
        product = session.get(Product, code)
        if product:
            product.last_price, product.in_stock, product.last_change = price, in_stock, simdi
        session.commit()


def get_all_product_codes():
    """[TR] Veritabanındaki tüm ürün kodlarını getirir. / [EN] Fetches all product codes in the database."""
    with SessionLocal() as session:
        return [row[0] for row in session.query(Product.code).all()]


def update_last_scan():
    """[TR] Son tarama zamanını günceller. / [EN] Updates the last scan time."""
    toplu_yaz(son_tarama=get_tr_time())


def get_last_scan():
    """[TR] Son tarama zamanını getirir. / [EN] Gets the last scan time."""
    with SessionLocal() as session:
        status = session.query(SystemStatus).first()
        if status:
            return status.last_scan
    return None
