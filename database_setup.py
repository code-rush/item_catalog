
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# A user table to store user information
class User(Base):
	__tablename__='user'

	id = Column(Integer, primary_key=True)
	name = Column(String(100), nullable=False)
	email = Column(String(300), nullable=False)
	picture = Column(String(300))

	
# restaurant table to store information related to each restaurants
class Restaurant(Base):
	__tablename__ = 'restaurant'

	name = Column(String(100), nullable = False)
	id = Column(Integer, primary_key = True)
	description = Column(String)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)

	@property 
	def serialize(self):
	#Returns restaurant items in easily serializeable format
		return {
			'name': self.name,
			'id': self.id,
			'description': self.description,
			'user_id': self.user_id
		}

# menu table to store items in a restaurant
class MenuItem(Base):
	__tablename__='menu_item'

	name = Column(String(100), nullable = False)
	id = Column(Integer, primary_key = True)
	course = Column(String(200))
	description = Column(String(500))
	price = Column(String(10))
	picture = Column(String)
	restaurant_id = Column(Integer, ForeignKey('restaurant.id'))
	restaurant = relationship(Restaurant)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)
	

	@property
	def serialize(self):
	#Returns menu items in easily serializeable format
		return {
			'name': self.name,
			'description': self.description,
			'id': self.id,
			'price': self.price,
			'course': self.course,
			'picture': self.picture,
			'user_id': self.user_id
		}



engine = create_engine('postgres://qurvbumcbwpjbn:5dLFEnI8bcGVu-YG7XMI5T7gZi@ec2-54-235-153-179.compute-1.amazonaws.com:5432/d7edpfc5ima8p5')
Base.metadata.create_all(engine)

