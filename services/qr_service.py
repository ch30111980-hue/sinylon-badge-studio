import qrcode
import os
from PIL import Image

def generate_qr_code(data_string, output_path):
    """
    Génère un QR Code épuré aux couleurs Sinylon avec un niveau d'erreur H (haute résilience).
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data_string)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#000000", back_color="#FFFFFF")
    img.save(output_path)
    return output_path
