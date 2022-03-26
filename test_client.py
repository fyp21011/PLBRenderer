from time import sleep
from typing import List

import numpy as np

from protocol import *

messages: List[BaseMessage] = []

test_rotation = [
    [1.0000, 0.0000, 0.0000, 0.0000],
    [0.6603, 0.0000, 0.0000, -0.7510],
    [0.1280, 0.0000, 0.0000, 0.9918],
    [0.8293, 0.0000, 0.0000, 0.5588],
    [0.9673, -0.0000, -0.0000, -0.2538],
    [0.4481, -0.0000, -0.0000, -0.8940],
    [0.3755, 0.0000, 0.0000, 0.9268],
    [0.9440, 0.0000, 0.0000, 0.3300],
    [0.8712, -0.0000, -0.0000, -0.4910],
    [0.2065, -0.0000, -0.0000, -0.9785],
]

messages.append(AddRigidBodyPrimitiveMessage(
    "cube_a", 
    "bpy.ops.mesh.primitive_cube_add",
    size = 1.0,
    location = [0.0, 0.1, 0.0],
    rotation = [0.0, 0.0, 0.6],
    scale = [0.2, 0.2, 1.0]
))

NUM_VERTICES = 100

X, Y = np.meshgrid(np.linspace(0, 1, NUM_VERTICES), np.linspace(0, 1, NUM_VERTICES))
X = np.expand_dims(X, axis = 2)
Y = np.expand_dims(Y, axis = 2)
surface = np.concatenate(
    [X, Y, np.zeros((NUM_VERTICES, NUM_VERTICES, 1))],
    axis = 2
) + 0.005 * np.random.rand(NUM_VERTICES, NUM_VERTICES, 3)
surface = surface.reshape((-1, 3))

surface = np.concatenate(
    [surface, surface - np.array([0, 0, 0.01])],
    axis = 0
)

assert surface.shape == (NUM_VERTICES * NUM_VERTICES * 2, 3), \
    f"surface's shape is {surface.shape}, but expected to be ({NUM_VERTICES * NUM_VERTICES * 2}, 3)"

rotation_cnt = 0

for frame_idx in range(0, 100, 10):
    messages.append(PointCloudMessage(
        surface + (frame_idx / 10),
        'cloud',
        frame_idx
    ))
    messages.append(UpdateRigidBodyPoseMessage(
        'cube_a',
        [0.0, 0.0, 0.1 + 0.01 * frame_idx] + test_rotation[rotation_cnt],
        frame_idx
    ))
    rotation_cnt += 1

messages.append(
    FinishAnimationMessage('test_10', 100)
)

for message in messages:
    message.send()
    sleep(1)
    