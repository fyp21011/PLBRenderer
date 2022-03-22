import asyncio
import os
import tempfile
import sys
from typing import Callable, Dict, Type

import bpy
import mathutils
import numpy as np

sys.path.append('D:\\Programming\\renderer\\PLBRenderer')

from protocol import *


def _set_item_pose(item, pose):
    """ #TODO
    """
    assert len(pose) == 7, \
        f"expecting a pose vector of length 7 (3 location dims, 4 rotation dims), got {len(pose)}"
    item.location = pose[:3]
    item.rotation_mode = 'QUATERNION'
    item.rotation_quaternion = mathutils.Quaternion(pose[3:])

def add_rigid_body_mesh_message_handler(message: AddRigidBodyMeshMessage):
    """ #TODO
    """
    filename = message.mesh_name
    suffix = filename.split('.')
    if suffix:
        suffix = suffix[-1]
    else:
        raise ValueError(f'cannot infer the meshes file type: {filename}')
    if suffix.lower().strip() == '.dae':
        with tempfile.TemporaryFile() as mesh_file:
            temp_file_name = mesh_file.name
            mesh_file.write(message.mesh_file)
            bpy.ops.wm.collada_import(
                filepath = os.path.join(tempfile.gettempdir(), temp_file_name), 
                auto_connect = True, 
                find_chains = True, 
                fix_orientation = True
            )
            item = bpy.context.active_object
            item.name = message.mesh_name
            _set_item_pose(item, message.init_pose)
    else:
        raise NotImplementedError(f'*.{suffix} is not supported meshes file extension')


def add_rigid_body_primitive_message_handler(message: AddRigidBodyPrimitiveMessage):
    """ #TODO
    """
    #message.create_primitive_in_blender()
    eval(message.primitive_type)(**message.params)
    item = bpy.context.active_object
    item.name = message.primitive_name

def set_particles_message_handler(message: SetParticlesMessage):
    """ #TODO
    """
    vertices_np = message.particles.reshape((-1, 3))
    num_vertices = vertices_np.shape[0]
    vertices = [
        vertices_np[i, :]
        for i in range(num_vertices)
    ]
    face = [] #TODO
    if message.obj_name not in bpy.data.objects:
        # no such object, create one meshes object
        meshes = bpy.data.meshes.new(message.obj_name + "_point_cloud")
        object = bpy.data.objects.new(message.obj_name, meshes)
        bpy.context.collection.objects.link(object)
    else:
        # retrieve the existing meshes and prepare to edit it
        object = bpy.data.objects[message.obj_name]
        bpy.context.view_layer.objects.active = object
        meshes = object.data
        bpy.ops.object.mode_set(mode = "OBJECT")
        bpy.ops.object.shape_key_add(from_mix = False)
        meshes.clear_geometry()

    meshes.from_pydata(vertices, [], face)
    meshes.update()   
    # animation
    shapekey = object.shape_key_add(name = f"key {message.frame_idx}", from_mix = False)
    shapekey.value = 1
    shapekey.keyframe_insert(data_path = "value", frame = message.frame_idx)
    if message.prev_frame_idx != None:
        shapekey.value = 0
        shapekey.keyframe_insert(data_path = "value", frame = message.prev_frame_idx)
        prev_shapekey = meshes.shape_keys.key_blocks[f"key {message.prev_frame_idx}"]
        prev_shapekey.value = 0
        prev_shapekey.keyframe_insert(data_path = "value", frame = message.frame_idx)


def update_rigid_body_mesh_pose_message(message: UpdateRigidBodyPoseMessage):
    """ #TODO
    """
    if message.name in bpy.data.objects:
        obj = bpy.data.objects[message.name]
        _set_item_pose(obj, message.pose_vec)
        obj.keyframe_insert(data_path = 'location', frame = message.frame_idx)
        obj.keyframe_insert(data_path = 'rotation_quaternion', frame = message.frame_idx)
    else:
        raise ValueError(f"receive pose-updating message for {message.name},"+ \
            "but the object is not known by the Blender")

MSG_CALLBACK_TABLE: Dict[Type, Callable[[BaseMessage], None]] = {
    AddRigidBodyMeshMessage:         add_rigid_body_mesh_message_handler,
    AddRigidBodyPrimitiveMessage:    add_rigid_body_primitive_message_handler,
    SetParticlesMessage:             set_particles_message_handler,
    UpdateRigidBodyPoseMessage:  update_rigid_body_mesh_pose_message
}

def callback_entrance(message: BaseMessage) -> None:
    """ #TODO
    """
    message_type = type(message)
    if message_type in MSG_CALLBACK_TABLE:
        MSG_CALLBACK_TABLE[message_type](message)
    else:
        raise NotImplementedError(f"Message handler for {message_type} cannot be found")

def server_main():
    server = AsyncServer(callback_entrance)
    asyncio.run(server.run_server())

def test_main():
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
    
    
    mock_message = AddRigidBodyPrimitiveMessage(
        "cube_a", 
        "bpy.ops.mesh.primitive_cube_add",
        size = 1.0,
        location = [0.0, 0.1, 0.0],
        rotation = [0.0, 0.0, 0.6],
        scale = [0.2, 0.2, 1.0]
    )
    callback_entrance(mock_message)

    rotation_cnt = 0

    for frame_idx in range(0, 100, 10):
        mock_message = UpdateRigidBodyPoseMessage(
            'cube_a',
            [0.0, 0.0, 0.1 + 0.01 * frame_idx] + test_rotation[rotation_cnt],
            frame_idx
        )
        callback_entrance(mock_message)
        rotation_cnt += 1
        
        
def test_set_particles():
    import numpy as np
    X, Y = np.meshgrid(np.linspace(0, 10, 200), np.linspace(0, 5, 200))
    surface = np.concatenate(
        [
            np.expand_dims(X, axis = 2),
            np.expand_dims(Y, axis = 2),
            np.zeros((200, 200, 1))
        ], axis = 2
    )
    for i in range(0, 100, 10):
        message = SetParticlesMessage(surface + (np.random.rand(200, 200, 3) if i != 0 else 0.5), 'test_points', i)
        print(f'set shape for frame_idx = {message.frame_idx}, whose previous key is {message.prev_frame_idx}')
        callback_entrance(message)
        
test_set_particles()
#test_main()
