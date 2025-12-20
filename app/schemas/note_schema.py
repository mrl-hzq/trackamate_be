from marshmallow import Schema, fields, validate, validates, ValidationError, validates_schema

class NoteSchema(Schema):
    id = fields.Str(dump_only=True)
    user_id = fields.Str(required=True)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    content = fields.Str(required=True, validate=validate.Length(min=1))
    category = fields.Str(validate=validate.Length(max=50))
    note_type = fields.Str(required=True, validate=validate.OneOf(['one-time', 'recurring']))
    recurrence_interval_days = fields.Int()
    last_reset_date = fields.Date()
    next_due_date = fields.Date()
    is_done = fields.Bool()
    done_date = fields.DateTime()
    burn_id = fields.Str(allow_none=True)
    invest_id = fields.Str(allow_none=True)
    commitment_id = fields.Str(allow_none=True)
    notification_enabled = fields.Bool()
    notification_type = fields.Str(validate=validate.OneOf(['specific', 'relative']), allow_none=True)
    notification_datetime = fields.DateTime(allow_none=True)
    notification_minutes_before = fields.Int(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @validates('recurrence_interval_days')
    def validate_recurrence_interval(self, value):
        # Get note_type from the data being validated
        if self.context.get('note_type') == 'recurring':
            if value is None or value < 1:
                raise ValidationError('recurrence_interval_days must be at least 1 for recurring notes')

    @validates('notification_minutes_before')
    def validate_notification_minutes(self, value):
        if value is not None and value <= 0:
            raise ValidationError('notification_minutes_before must be greater than 0')

    @validates_schema
    def validate_notification_fields(self, data, **kwargs):
        """Validate notification field combinations"""
        notification_enabled = data.get('notification_enabled', False)
        notification_type = data.get('notification_type')
        notification_datetime = data.get('notification_datetime')
        notification_minutes_before = data.get('notification_minutes_before')
        next_due_date = data.get('next_due_date')

        if notification_enabled:
            # If notifications are enabled, type must be specified
            if not notification_type:
                raise ValidationError('notification_type must be either "specific" or "relative" when notification_enabled is True')

            # Validate specific type requirements
            if notification_type == 'specific':
                if not notification_datetime:
                    raise ValidationError('notification_datetime is required when notification_type is "specific"')

            # Validate relative type requirements
            elif notification_type == 'relative':
                if notification_minutes_before is None:
                    raise ValidationError('notification_minutes_before is required when notification_type is "relative"')
                if not next_due_date:
                    raise ValidationError('Cannot set relative notification without a due date (next_due_date required)')
