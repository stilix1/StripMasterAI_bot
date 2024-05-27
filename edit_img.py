import os
import time

from PIL import Image, ImageFilter


# Функция для размытия изображения
def blur_image(image_path, radius=2):
    try:
        # Открываем изображение
        img = Image.open(image_path)

        # Размываем изображение
        blurred_img = img.filter(ImageFilter.GaussianBlur(radius))

        # Возвращаем размытое изображение
        return blurred_img
    except Exception as e:
        print("Произошла ошибка при размытии изображения:", e)
        return None


# Применяем размытие и сохраняем изображение
def edit_photo(file_path):
    input_image_path = os.path.join("tmp", "files", file_path)
    unique_name = int(time.time())
    output_image_path = os.path.join("tmp", "files", "final_photos", f"final_photo_{unique_name}.jpg")
    blurred_image = blur_image(input_image_path, 30)
    if blurred_image:
        blurred_image.save(output_image_path)
    return output_image_path
