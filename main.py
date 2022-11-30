# MicroPython example of reading the Person Sensor from Useful Sensors on a
# Micro:bit and using it to control a ring:bit robot car. See
# https://usfl.ink/ps_dev for full documentation on the module, and README.md in
# this project for details on wiring and assembly.

from microbit import *

from Cutebot import *

import struct
import time

# The person sensor has the I2C ID of hex 62, or decimal 98.
PERSON_SENSOR_I2C_ADDRESS = 0x62

# We will be reading raw bytes over I2C, and we'll need to decode them into
# data structures. These strings define the format used for the decoding, and
# are derived from the layouts defined in the developer guide.
PERSON_SENSOR_I2C_HEADER_FORMAT = "BBH"
PERSON_SENSOR_I2C_HEADER_BYTE_COUNT = struct.calcsize(
    PERSON_SENSOR_I2C_HEADER_FORMAT)

PERSON_SENSOR_FACE_FORMAT = "BBBBBBbB"
PERSON_SENSOR_FACE_BYTE_COUNT = struct.calcsize(PERSON_SENSOR_FACE_FORMAT)

PERSON_SENSOR_FACE_MAX = 4
PERSON_SENSOR_RESULT_FORMAT = PERSON_SENSOR_I2C_HEADER_FORMAT + \
    "B" + PERSON_SENSOR_FACE_FORMAT * PERSON_SENSOR_FACE_MAX + "H"
PERSON_SENSOR_RESULT_BYTE_COUNT = struct.calcsize(PERSON_SENSOR_RESULT_FORMAT)

# How long to pause between sensor polls.
PERSON_SENSOR_DELAY = 0.2

# Constants to control the movement behavior.
TURN_THRESHOLD = 10
TURN_SPEED = 40
MIN_FACE_WIDTH = 30
MAX_FACE_WIDTH = 35
MOVE_SPEED = 100

# Set up the ring:bit controller.
CB = CUTEBOT()

# Keep looping and reading the person sensor results.
while True:
    read_data = i2c.read(PERSON_SENSOR_I2C_ADDRESS,
                         PERSON_SENSOR_RESULT_BYTE_COUNT)
    offset = 0
    (pad1, pad2, payload_bytes) = struct.unpack_from(
        PERSON_SENSOR_I2C_HEADER_FORMAT, read_data, offset)
    offset = offset + PERSON_SENSOR_I2C_HEADER_BYTE_COUNT

    # If the I2C read failed with bad values, pause and then retry.
    if payload_bytes != (PERSON_SENSOR_RESULT_BYTE_COUNT - 7):
        time.sleep(PERSON_SENSOR_DELAY)
        continue

    (num_faces) = struct.unpack_from("B", read_data, offset)
    num_faces = int(num_faces[0])
    offset = offset + 1

    faces = []
    for i in range(num_faces):
        (box_confidence, box_left, box_top, box_right, box_bottom, id_confidence, id,
         is_facing) = struct.unpack_from(PERSON_SENSOR_FACE_FORMAT, read_data, offset)
        offset = offset + PERSON_SENSOR_FACE_BYTE_COUNT
        face = {
            "box_confidence": box_confidence,
            "box_left": box_left,
            "box_top": box_top,
            "box_right": box_right,
            "box_bottom": box_bottom,
            "id_confidence": id_confidence,
            "id": id,
            "is_facing": is_facing,
        }
        faces.append(face)
    checksum = struct.unpack_from("H", read_data, offset)

    # If we've found any faces, the largest should be the first in the list, so
    # use that to turn our robot to point at it.
    left_speed = 0
    right_speed = 0
    if num_faces > 0:
        main_face = faces[0]
        face_center_x = (main_face["box_left"] + main_face["box_right"]) / 2
        face_width = main_face["box_right"] - main_face["box_left"]
        # Decide if we need to turn based on the position of the face.
        turn_direction = (face_center_x - 128)
        if turn_direction < -TURN_THRESHOLD:
            left_speed = -TURN_SPEED
            right_speed = TURN_SPEED
        elif turn_direction > TURN_THRESHOLD:
            left_speed = TURN_SPEED
            right_speed = -TURN_SPEED
        # If the face is too big, move away, or too small, move forward.
        elif face_width < MIN_FACE_WIDTH:
            left_speed = MOVE_SPEED
            right_speed = MOVE_SPEED
        elif face_width > MAX_FACE_WIDTH:
            left_speed = -MOVE_SPEED
            right_speed = -MOVE_SPEED
        else:
            left_speed = 0
            right_speed = 0
    print(left_speed, right_speed)
    if left_speed != 0 or right_speed != 0:
        CB.set_motors_speed(left_speed, right_speed)
        time.sleep(0.02)
    CB.set_motors_speed(0, 0)
    time.sleep(PERSON_SENSOR_DELAY)
