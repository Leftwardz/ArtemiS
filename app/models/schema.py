from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    products = relationship('Product', back_populates='client', cascade="all, delete")
    drawings = relationship('Drawing', back_populates='client', cascade="all, delete")


class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    client_id = Column(Integer, ForeignKey('clients.id'))
    client = relationship('Client', back_populates='products')
    drawings = relationship('Drawing', back_populates='product', cascade="all, delete")
    paper_color = Column(String)
    orientation = Column(String)
    paper_size = Column(String)


class PrintingGroup(Base):
    __tablename__ = 'printing_groups'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)


class Printer(Base):
    __tablename__ = 'printers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)


class RegisteredPrinter(Base):
    __tablename__ = 'registered_printers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    display_name = Column(String)
    enabled = Column(String, default='1')
    notes = Column(String)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True)
    password = Column(String)
    privileges = Column(String)


class ConfigAccess(Base):
    __tablename__ = 'config_access'
    id = Column(Integer, primary_key=True, autoincrement=True)
    principal_name = Column(String, unique=True)
    principal_type = Column(String)


class Drawing(Base):
    __tablename__ = 'drawings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    client_id = Column(Integer, ForeignKey('clients.id'))
    client = relationship('Client', back_populates='drawings')
    product = relationship('Product', back_populates='drawings')
    item_type = Column(String)
    x1 = Column(String)
    x2 = Column(String)
    y1 = Column(String)
    y2 = Column(String)
    font_name = Column(String)
    font_size = Column(String)
    font_style = Column(String)
    orientation = Column(String)
    thickness = Column(String)
    dashed = Column(String)
    text = Column(String)
    file_columns = Column(String)
    barcode_height = Column(String)
    barcode_width = Column(String)
    line_distance = Column(String)
    segment_id = Column(String)
    tag = Column(String)
    proportion = Column(String)
    image = Column(LargeBinary)
    char_limit = Column(String)
