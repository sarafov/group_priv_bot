## Usage

### Running the Bot

To start the `@group_priv_bot`, a bot to manage privacy within Telegram group chat, simply run the following command:

```bash
python priv_guard_bot.py
```

This will start the @group_priv_bot, enabling the full functionality of the privacy bot.

### Requirement Libraries

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

- ### Weights for Places365 Model

Please download the pre-trained weights for the Places365 model and place them inside the `configuration` folder.

- **Download Link**: [vgg16-places365_weights](https://github.com/GKalliatakis/Keras-VGG16-places365/releases/download/v1.0/vgg16-places365_weights_tf_dim_ordering_tf_kernels.h5)
