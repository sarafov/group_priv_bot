How to use:
Run the priv_guard_bot.py

Requirement:
from flask import Flask, request
from telebot import types,util
from telebot.async_telebot import AsyncTeleBot
import asyncio
import os
from telebot import formatting
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import json
import urllib
from telebot.types import LinkPreviewOptions
import cv2
from PIL import Image
import piexif
from io import BytesIO
import logging
from detoxify import Detoxify
import aiohttp
from ultralytics import YOLO
import numpy as np
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.utils import get_file

Note:
Please download the weights for Places365 model and put in inside the configuration folder
Download link: https://github.com/GKalliatakis/Keras-VGG16-places365/releases/download/v1.0/vgg16-places365_weights_tf_dim_ordering_tf_kernels.h5
