import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_upload_file(file, folder_name):
    """
    Save uploaded file to the specified folder

    Args:
        file: FileStorage object from request.files
        folder_name: Name of the subfolder (burn, invest, commit)

    Returns:
        str: Relative path to the saved file, or None if failed
    """
    if file and allowed_file(file.filename):
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"

        # Create full path
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder_name)

        # Ensure directory exists
        os.makedirs(upload_path, exist_ok=True)

        # Save file
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)

        # Return relative path for database storage
        return f"uploads/{folder_name}/{unique_filename}"

    return None

def delete_upload_file(file_path):
    """
    Delete uploaded file from filesystem

    Args:
        file_path: Relative path to the file (e.g., 'uploads/burn/abc123.jpg')

    Returns:
        bool: True if deletion successful, False otherwise
    """
    if file_path:
        try:
            full_path = os.path.join(os.path.dirname(current_app.config['UPLOAD_FOLDER']), file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    return False
