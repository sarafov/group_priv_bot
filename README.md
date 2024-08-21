Sure! Here's the raw Markdown code for the `README.md`:

```markdown
# Priv Guard Bot

`Priv Guard Bot` is a Python-based project designed to provide various privacy and security-related functionalities using a combination of Flask, Telebot, image processing, and deep learning techniques.

## Requirements

Ensure you have the following Python packages installed:

```bash
pip install Flask pyTelegramBotAPI pycryptodome Pillow opencv-python detoxify aiohttp ultralytics tensorflow numpy piexif
```

## Usage

### Running the Bot

To start the `Priv Guard Bot`, simply run the following command:

```bash
python priv_guard_bot.py
```

This will start the Flask application and the Telegram bot, enabling the full functionality of the privacy guard services.

### Project Structure

- **Flask**: Used to create a simple web server for handling requests.
- **Telebot**: For managing interactions with the Telegram bot.
- **AsyncTeleBot**: Allows for asynchronous operations within the bot, ensuring smooth performance.
- **Cryptography (AES)**: Provides encryption and decryption functionalities.
- **PIL (Pillow)**: Image processing capabilities.
- **OpenCV**: More advanced image processing, including face detection.
- **Detoxify**: For content moderation using deep learning.
- **YOLO**: Object detection capabilities.
- **TensorFlow**: Deep learning framework for various models, including Places365.

### Weights for Places365 Model

Please download the pre-trained weights for the Places365 model and place them inside the `configuration` folder.

- **Download Link**: [vgg16-places365_weights](https://github.com/GKalliatakis/Keras-VGG16-places365/releases/download/v1.0/vgg16-places365_weights_tf_dim_ordering_tf_kernels.h5)

### Included Libraries

- **Flask**: A micro web framework.
- **Telebot**: Used for creating Telegram bots.
- **AES (Crypto.Cipher)**: Advanced Encryption Standard for securing data.
- **PIL (Pillow)**: Python Imaging Library for opening, manipulating, and saving images.
- **OpenCV**: An open-source computer vision library.
- **Detoxify**: A Python library to detect toxic comments.
- **YOLO**: You Only Look Once, a real-time object detection system.
- **TensorFlow**: An open-source platform for machine learning.
- **Piexif**: Manipulates EXIF data in images.
- **AIOHTTP**: An asynchronous HTTP client/server framework.
- **Ultralytics**: For running YOLO object detection.
- **NumPy**: A library for numerical computing.
