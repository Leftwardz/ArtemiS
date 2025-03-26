from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, attributes
import hashlib
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


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True)
    password = Column(String)
    privileges = Column(String)


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


class DataBase:
    def __init__(self, location):
        self.db_location = location
        self.read_engine = None
        self.write_engine = None
        self.session = None

    @staticmethod
    def create_hash(text):
        sha256_hash = hashlib.sha256()
        sha256_hash.update(text.encode('utf-8'))
        return sha256_hash.hexdigest()

    def connect_to_database(self, mode):
        """
        :param mode: ['ro': Read Only, 'rw': Read Write]
        """
        try:
            if mode == 'ro':
                self.read_engine = create_engine(f'sqlite:///{self.db_location}', connect_args={'uri': 'ro'})
            elif mode == 'rw':
                self.write_engine = create_engine(f'sqlite:///{self.db_location}', connect_args={'uri': 'rw'})
            else:
                raise(f'O modo {mode} não existe, deve ser "ro" ou "rw"')

            Session = sessionmaker(bind=self.write_engine)
            self.session = Session()

        except Exception as e:
            raise(f'Erro ao conectar com o banco: {e}')

    def create_tables(self):
        self.connect_to_database('rw')
        Base.metadata.create_all(self.write_engine)

    def search_clients(self, name=''):
        self.connect_to_database('ro')
        clients_objects = self.session.query(Client).filter(Client.name.like(f'%{name}%')).all()
        self.session.close()

        return clients_objects

    def search_clients_names(self, name=''):
        self.connect_to_database('ro')
        clients_objects = self.session.query(Client).filter(Client.name.like(f'%{name}%')).order_by(Client.name).all()
        self.session.close()

        return [i.name for i in clients_objects]

    def insert_client(self, client_name):
        self.connect_to_database('rw')

        client_object = Client(name=client_name)
        self.session.add(client_object)
        self.session.commit()

        self.session.close()

    def delete_client(self, client_name):
        self.connect_to_database('rw')

        client_object = self.session.query(Client).filter_by(name=client_name).first()
        if client_object:
            self.session.delete(client_object)
            self.session.commit()
            self.session.close()
            return True
        else:
            self.session.close()
            return False

    def delete_product(self, client_name, product_name):
        self.connect_to_database('rw')

        client_id = self.session.query(Client).filter_by(name=client_name).first().id
        product = self.session.query(Product).filter_by(name=product_name, client_id=client_id).first()
        if product:
            self.session.delete(product)
            self.session.commit()
            self.session.close()
            return True
        else:
            self.session.close()
            return False

    def search_product(self, client_name, product_name):
        self.connect_to_database('rw')

        client_id = self.session.query(Client).filter_by(name=client_name).first().id
        product = self.session.query(Product).filter_by(name=product_name, client_id=client_id).first()

        if product:
            self.session.close()
            return product
        else:
            self.session.close()
            return None

    def search_color(self, client_name, product_name):
        self.connect_to_database('ro')

        client_id = self.session.query(Client).filter_by(name=client_name).first().id
        product = self.session.query(Product).filter_by(name=product_name, client_id=client_id).first()
        if product:
            color = product.paper_color
        else:
            color = None

        self.session.close()
        return color

    def insert_product(self, product_name, client_name, color, orientation, paper_size):
        self.connect_to_database('rw')

        client_object = self.session.query(Client).filter_by(name=client_name).first()

        product = Product(name=product_name, paper_color=color, orientation=orientation, paper_size=paper_size)

        client_object.products.append(product)

        self.session.add(product)
        self.session.commit()

        self.session.close()

    def change_or_add_product_name(self, client_name, product_name, new_name, color, orientation, paper_size):
        self.connect_to_database('rw')

        client_id = self.session.query(Client).filter_by(name=client_name).first().id
        product = self.session.query(Product).filter_by(name=product_name, client_id=client_id).first()
        if product:
            product.name = new_name
            product.paper_color = color
            product.orientation = orientation
            product.paper_size = paper_size
            self.session.commit()
        else:
            self.insert_product(new_name, client_name, color, orientation, paper_size)

        self.session.close()

    def search_products(self, client_name):
        self.connect_to_database('ro')

        client_object = self.session.query(Client).filter_by(name=client_name).first()
        result = sorted([i.name for i in client_object.products])

        self.session.close()

        return result

    def save_drawings(self, client_name, product_name, drawings):
        """
        :param drawings_dict: []

        """
        self.connect_to_database('rw')

        client_id = self.session.query(Client).filter_by(name=client_name).first().id
        product = self.session.query(Product).filter_by(name=product_name, client_id=client_id).first()

        batch_size = 100  # Tamanho do lote para inserção em lotes
        batch = []
        for drawings_dict in drawings:
            drawing = Drawing(
                client_id=client_id,
                product_id=product.id,
                **drawings_dict
            )
                # item_type=drawings_dict['item_type'],
                # x1=drawings_dict['x1'],
                # x2=drawings_dict['x2'],
                # y2=drawings_dict['y2'],
                # y1=drawings_dict['y1'],
                # font_name=drawings_dict['font_name'],
                # font_size=drawings_dict['font_size'],
                # font_style=drawings_dict['font_style'],
                # orientation=drawings_dict['orientation'],
                # thickness=drawings_dict['thickness'],
                # dashed=drawings_dict['dashed'],
                # text=drawings_dict['text'],
                # file_columns=drawings_dict['file_columns'],
                # barcode_height=drawings_dict['barcode_height'],
                # barcode_width=drawings_dict['barcode_width'],
                # line_distance=drawings_dict['line_distance'],
                # segment_id=drawings_dict['segment_id'],
                # tag=drawings_dict['tag'],
                # proportion=drawings_dict['proportion'],
                # image=drawings_dict['image'],
                # char_limit=drawings_dict['char_limit']
            # )
            batch.append(drawing)

            if len(batch) >= batch_size:
                self.session.bulk_save_objects(batch)
                batch = []

            # product.drawings.append(drawing)
            # self.session.add(drawing)

        if batch:
            self.session.bulk_save_objects(batch)

        self.session.commit()
        self.session.close()

    def consult_drawings_from_product(self, client_name, product_name):
        self.connect_to_database('ro')

        client = self.session.query(Client).filter_by(name=client_name).first()
        if client:
            client_id = client.id
        else:
            self.session.close()
            return []

        product = self.session.query(Product).filter_by(name=product_name, client_id=client_id).first()
        if product:
            result = []
            for draw in product.drawings:
                draw_dict = attributes.instance_dict(draw)
                draw_dict.pop('_sa_instance_state')
                draw_dict.pop('product_id')
                draw_dict.pop('client_id')
                draw_dict.pop('id')
                result.append(draw_dict)
        else:
            result = []

        self.session.close()

        return result

    def del_all_drawing_from_product(self, client_name, product_name):
        self.connect_to_database('rw')

        client_id = self.session.query(Client).filter_by(name=client_name).first().id
        product = self.session.query(Product).filter_by(name=product_name, client_id=client_id).first()
        drawings = product.drawings
        if drawings:
            self.session.query(Drawing).filter(Drawing.product_id == product.id).delete()
            self.session.commit()

        self.session.close()

    def search_printers(self):
        self.connect_to_database('ro')

        result = self.session.execute(select(Printer.__table__.columns.name))

        return [i.name for i in result]

    def save_printers(self, printers_list):
        self.connect_to_database('rw')

        printers_in_db = self.session.query(Printer).all()

        for printer in printers_in_db:
            self.session.delete(printer)

        self.session.commit()
        for printer in printers_list:
            self.session.add(Printer(name=printer))

        self.session.commit()

        self.session.close()

    def has_login(self):
        self.connect_to_database('ro')
        users_objects = self.session.query(User).filter(User.username.like(f'%')).all()
        self.session.close()
        if [i.username for i in users_objects]:
            return True
        else:
            return False

    def register_user(self, username, password, privileges):
        self.connect_to_database('rw')

        password = self.create_hash(password)
        user = User(username=username.lower(),
                    password=password,
                    privileges=privileges)

        self.session.add(user)
        self.session.commit()
        self.session.close()

    def verify_user(self, username, password):
        self.connect_to_database('ro')
        user_objects = self.session.query(User).filter(User.username.like(username)).first()
        self.session.close()

        if user_objects:
            return user_objects.password == self.create_hash(password)
        else:
            return False

    def users_list(self):
        self.connect_to_database('rw')

        users_in_db = self.session.query(User).all()

        return [i.username.capitalize() for i in users_in_db]

    def delete_user(self, username):
        self.connect_to_database('rw')

        user_in_db = self.session.query(User).filter(User.username.like(username)).first()

        if user_in_db:
            self.session.delete(user_in_db)
        else:
            raise f'Usuário {username} não encontrado na base'
        self.session.commit()
        self.session.close()

    def product_exists(self, client_name, product_name):

        self.connect_to_database('ro')

        client = self.session.query(Client).filter_by(name=client_name).first()
        if not client:
            self.session.close()
            return False

        client_id = client.id
        product = self.session.query(Product).filter_by(name=product_name, client_id=client_id).first()
        self.session.close()
        if product:
            return True
        else:
            return False

    def search_print_group(self):
        self.connect_to_database('ro')

        result = self.session.execute(select(PrintingGroup.__table__.columns.name))

        return [i.name for i in result]

    def insert_print_group(self, name):
        self.connect_to_database('rw')

        printing_group = PrintingGroup(name=name)

        self.session.add(printing_group)
        self.session.commit()

        self.session.close()

    def delete_print_group(self, name):
        self.connect_to_database('rw')

        print_group = self.session.query(PrintingGroup).filter(PrintingGroup.name.like(name)).first()

        if print_group:
            self.session.delete(print_group)
        else:
            raise Exception(f'Grupo {print_group} não encontrado na base')
        self.session.commit()
        self.session.close()


if __name__ == '__main__':
    db = DataBase('database.db')
    db.create_tables()
    print(db.has_login())
    print(db.verify_user('nathan', '1234f567'))

