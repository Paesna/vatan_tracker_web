"""
[TR] Veritabanı Modülü / [EN] Database Module
[TR] Tüm PostgreSQL (Supabase) bağlantılarını ve SQLAlchemy ORM modellerini yönetir. / [EN] Handles all PostgreSQL (Supabase) connections and ORM models using SQLAlchemy.
[TR] 'products' ve 'price_history' tablolarının şemasını tanımlar. / [EN] Defines the Schema for 'products' and 'price_history'.
"""

from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, ForeignKey, text, inspect
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
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

class PriceHistory(Base):
    __tablename__ = 'price_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, ForeignKey('products.code'))
    price = Column(Float)
    in_stock = Column(Integer)
    timestamp = Column(DateTime)

class SystemStatus(Base):
    __tablename__ = 'system_status'
    id = Column(Integer, primary_key=True)
    last_scan = Column(DateTime)

# [TR] Veritabanı motoru ve oturum oluşturucu / [EN] Database engine and session maker
engine = create_engine(config.DB_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """[TR] Tabloları oluşturur (eğer yoksa). / [EN] Creates the tables (if they don't exist)."""
    Base.metadata.create_all(engine)
    
    # [TR] Varolan products tablosuna image_url sütunu eklemek için basit bir geçiş (migration) / [EN] Simple migration to add image_url
    inspector = inspect(engine)
    if 'products' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('products')]
        if 'image_url' not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE products ADD COLUMN image_url VARCHAR"))

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

def add_product(code, name, url, base_price, image_url=None):
    """[TR] Yeni ürünü tabloya ekler. / [EN] Adds a new product to the table."""
    with SessionLocal() as session:
        # [TR] Ürün zaten varsa eklemez (IGNORE mantığı) / [EN] Does not add if product already exists (IGNORE logic)
        exists = session.query(Product).filter_by(code=code).first()
        if not exists:
            new_prod = Product(
                code=code, 
                name=name, 
                url=url, 
                image_url=image_url,
                base_price=base_price, 
                first_seen=get_tr_time()
            )
            session.add(new_prod)
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
        new_history = PriceHistory(
            code=code,
            price=price,
            in_stock=in_stock,
            timestamp=get_tr_time()
        )
        session.add(new_history)
        session.commit()

def update_last_scan():
    """[TR] Son tarama zamanını günceller. / [EN] Updates the last scan time."""
    with SessionLocal() as session:
        status = session.query(SystemStatus).first()
        if not status:
            status = SystemStatus(id=1, last_scan=get_tr_time())
            session.add(status)
        else:
            status.last_scan = get_tr_time()
        session.commit()

def get_last_scan():
    """[TR] Son tarama zamanını getirir. / [EN] Gets the last scan time."""
    with SessionLocal() as session:
        status = session.query(SystemStatus).first()
        if status:
            return status.last_scan
    return None
