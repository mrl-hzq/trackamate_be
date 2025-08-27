from flask import Blueprint, request, jsonify
from app.models import User
from app.schemas.user_schema import UserSchema
from app import db, bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

user_bp = Blueprint('user', __name__)
user_schema = UserSchema()

@user_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    errors = user_schema.validate(data)
    if errors:
        return jsonify(errors), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already registered"}), 409

    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(
        username=data['username'],
        name=data['name'],
        email=data['email'],
        password_hash=hashed_password
    )

    db.session.add(user)
    db.session.commit()

    return user_schema.dump(user), 201


@user_bp.route('/login', methods=['POST'])
# @cross_origin()
def login():
    data = request.get_json()
    # print("11111", data)
    user = User.query.filter_by(username=data['username']).first()
    print("22222",user)

    if not user or not bcrypt.check_password_hash(user.password_hash, data['password']):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({"access_token": access_token})


@user_bp.route('/me', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user_schema.dump(user)
