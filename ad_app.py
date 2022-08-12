import flask
from flask import request
from flask.views import MethodView
from sqlalchemy import Column, DateTime, Integer, String, create_engine, func, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pydantic
from hashlib import md5

app = flask.Flask('app')
local_db = 'postgresql://flask_admin:admin@localhost:5433/flask_app'
engine = create_engine(local_db)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class HttpError(Exception):

    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message


@app.errorhandler(HttpError)
def handle_http_error(error):
    response = flask.jsonify({'message': error.message})
    response.status_code = error.status_code
    return response


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_name = Column(String(100), nullable=False, unique=True)
    password = Column(String(200), nullable=False)
    registration_time = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "user_name": self.user_name,
            "registration_time": int(self.registration_time.timestamp()),
            "id": self.id,
        }


class CreateUserValidator(pydantic.BaseModel):
    user_name: str
    password: str

    @pydantic.validator('password')
    def strong_password(cls, value):
        if len(value) < 8:
            raise ValueError('password should be at least 8 symbols')
        return value


class Advertisement(Base):
    __tablename__ = "ads"
    id = Column(Integer, primary_key=True)
    title = Column(String(355), nullable=False)
    description = Column(Text)
    creation_time = Column(DateTime, server_default=func.now())
    creator = Column(Integer, ForeignKey(User.id), nullable=False)

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "creation_time": int(self.creation_time.timestamp()),
            "creator": self.creator,
            "id": self.id,
        }


Base.metadata.create_all(engine)


class UserView(MethodView):

    def get(self, user_id=None):
        with Session() as session:
            if user_id is None:
                users = session.query(User).all()
                users_names = []
                for user in users:
                    users_names.append(user.to_dict())
                return flask.jsonify({'users': users_names})
            user = session.query(User).filter(User.id == user_id).first()
            if user is None:
                raise HttpError(400, 'No such user')
            return flask.jsonify({'user': user.to_dict()})

    def post(self):
        try:
            validated_data = CreateUserValidator(**request.json).dict()
        except pydantic.ValidationError as er:
            raise HttpError(400, er.errors())
        validated_data['password'] = str(md5(validated_data['password'].encode()).hexdigest())
        with Session() as session:
            new_user = User(**validated_data)
            session.add(new_user)
            session.commit()
            return flask.jsonify({'id': new_user.id})


class AdvertisementView(MethodView):

    def get(self, ad_id):
        with Session() as session:
            if ad_id is None:
                ads = session.query(Advertisement).all()
                ads_list = []
                for ad in ads:
                    ads_list.append(ad.to_dict())
                return flask.jsonify({'ads': ads_list})
            ad = session.query(Advertisement).filter(Advertisement.id == ad_id).first()
            if ad is None:
                raise HttpError(400, 'No such ad')
            return flask.jsonify({'ad': ad.to_dict()})

    def post(self):
        with Session() as session:
            new_ad = Advertisement(**request.json)
            session.add(new_ad)
            session.commit()
            return flask.jsonify({'id': new_ad.id})

    def put(self):
        new_data = request.json
        if "id" not in new_data:
            raise HttpError(400, 'No id was given')
        with Session() as session:
            item = session.query(Advertisement).get(new_data["id"])
            if item is None:
                raise HttpError(400, 'No such ad')
            if 'title' in new_data:
                item.title = new_data["title"]
            if 'description' in new_data:
                item.description = new_data["description"]
            session.add(item)
            session.commit()
            updated_item = session.query(Advertisement).get(new_data["id"])
            return flask.jsonify({'ad': updated_item.to_dict()})

    def delete(self, ad_id):
        with Session() as session:
            item = session.query(Advertisement).get(ad_id)
            session.delete(item)
            session.commit()
            return flask.jsonify({'ad': f'ad with id {ad_id} is no longer exists'})


app.add_url_rule('/show_user/<int:user_id>/', view_func=UserView.as_view('show_user'), methods=['GET'])
app.add_url_rule('/show_users/', view_func=UserView.as_view('show_users'), methods=['GET'])
app.add_url_rule('/cr_user/', view_func=UserView.as_view('create_user'), methods=['POST'])
app.add_url_rule('/show_ad/<int:ad_id>/', view_func=AdvertisementView.as_view('show_ad'), methods=['GET'])
app.add_url_rule('/show_ads/', defaults={'ad_id': None}, view_func=AdvertisementView.as_view('show_ads'), methods=['GET'])
app.add_url_rule('/cr_ad/', view_func=AdvertisementView.as_view('create_ad'), methods=['POST'])
app.add_url_rule('/update_ad/', view_func=AdvertisementView.as_view('update_ad'), methods=['PUT'])
app.add_url_rule('/delete_ad/<int:ad_id>/', view_func=AdvertisementView.as_view('delete_ad'), methods=['DELETE'])


# ______________________________________________________________________________________________________________________

@app.route('/test')
def test():

    return flask.jsonify({
        'status': 'it works!'
    })


@app.route('/test_p', methods=['POST'])
def test_post():

    headers = request.headers
    json = request.json
    qs = request.args
    return flask.jsonify({
        'status': 'it works too!',
        'headers': dict(headers),
        'json': dict(json),
        'qs': dict(qs)
    })


# with Session() as session:
#     users = session.query(User).all()
#     for user in users:
#         print(flask.jsonify(user.to_dict()))
