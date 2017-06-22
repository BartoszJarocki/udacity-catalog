from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, User, Category, Item

engine = create_engine('sqlite:///catalog.db')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

session = DBSession()

# Create two users
user_one = User(name="Bartosz Jarocki", email="jarocki.bartek@gmail.com")
session.add(user_one)
session.commit()

user_one = session.query(User).filter_by(email=user_one.email).one()

user_two = User(name="Katarzyna Jarocka", email="kasia@gmail.com")
session.add(user_two)
session.commit()

user_two = session.query(User).filter_by(email=user_two.email).one()

# Create two categories for each user
category_one = Category(title="Mobile", user_id=user_one.id)
session.add(category_one)
session.commit()

category_one = session.query(Category).filter_by(title=category_one.title).one()

category_two = Category(title="Web", user_id=user_one.id)
session.add(category_two)
session.commit()

category_two = session.query(Category).filter_by(title=category_two.title).one()

category_three = Category(title="AI", user_id=user_two.id)
session.add(category_three)
session.commit()

category_three = session.query(Category).filter_by(title=category_three.title).one()

category_four = Category(title="VR", user_id=user_two.id)
session.add(category_four)
session.commit()

category_four = session.query(Category).filter_by(title=category_four.title).one()

# Create four products for each category
for i in range(0, 60):
    if i < 4:
        item_one = Item(title="%s company %s" % (category_one.title, str(i % 4)), description="This is a nice %s %s company." % (str(i % 4), category_one.title), category_id=category_one.id, user_id=user_one.id)
    elif i < 8:
        item_one = Item(title="%s company %s" % (category_two.title, str(i % 4)), description="This is a nice %s %s company." % (str(i % 4), category_two.title), category_id=category_two.id, user_id=user_one.id)
    elif i < 12:
        item_one = Item(title="%s company %s" % (category_three.title, str(i % 4)), description="This is a nice %s %s company." % (str(i % 4), category_three.title), category_id=category_three.id, user_id=user_two.id)
    else:
        item_one = Item(title="%s company %s" % (category_four.title, str(i % 4)), description="This is a nice %s %s company." % (str(i % 4), category_four.title), category_id=category_four.id, user_id=user_two.id)
    session.add(item_one)
    session.commit()

print "All items were added..."