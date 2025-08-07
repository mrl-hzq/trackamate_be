from marshmallow import Schema, fields

class UserSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(required=True)
    email = fields.Email(required=True)
    password = fields.String(load_only=True, required=True)
