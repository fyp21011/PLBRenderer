import asyncio
import os
import tempfile
from typing import Callable, Dict, Type

import bpy
import mathutils

from protocol import *


def _set_item_pose(item, pose):
    assert len(pose) == 7, \
        f"expecting a pose vector of length 7 (3 location dims, 4 rotation dims), got {len(pose)}"
    item.location = pose[:3]
    item.rotation_quaternion = mathutils.Quaternion(pose[3:])

def add_rigid_body_mesh_message_handler(message: AddRigidBodyMeshMessage):
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
    message.create_primitive_in_blender()
    item = bpy.context.active_object
    item.name = message.primitive_name

def set_particles_message_handler(message: SetParticlesMessage):
    vertices_np = message.particles.reshape((-1, 3))
    num_vertices = vertices_np.shape[0]
    vertices = [
        vertices_np[i, :]
        for i in range(num_vertices)
    ]
    if message.obj_name not in bpy.context.objects:
        meshes = bpy.data.meshes.new(message.obj_name + "_point_cloud")
        object = bpy.data.objects.new(message.obj_name, meshes)
    else:
        object = bpy.context.object[message.obj_name]
        meshes = object.data
    
    meshes.from_pydata(vertices, [], [])
    meshes.update()

def update_rigid_body_mesh_pose_message(message: UpdateRigidBodyPoseMessage):
    if message.name in bpy.context.objects:
        obj = bpy.context.objects[message.name]
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
    message_type = type(message)
    if message_type in MSG_CALLBACK_TABLE:
        MSG_CALLBACK_TABLE[message_type](message)
    else:
        raise NotImplementedError(f"Message handler for {message_type} cannot be found")

def server_main():
    server = AsyncServer(callback_entrance)
    asyncio.run(server.run_server())

def test_main():
    mock_message = AddRigidBodyPrimitiveMessage(
        "cube_a", 
        "bpy.ops.mesh.primitive_cube_add",
        size = 1.0,
        location = [0.0, 0.1, 0.0],
        rotation = [0.0, 0.6, 0.0, 0.8],
        scale = [0.2, 0.2, 1.0]
    )
    callback_entrance(mock_message)

    for frame_idx in range(0, 100, 10):
        mock_message = UpdateRigidBodyPoseMessage(
            'cube_a',
            [
                0.0, 0.0, 0.1 + 0.01 * frame_idx,
                0.0, 0.6, 0.0, 0.8
            ],
            frame_idx
        )
        callback_entrance(mock_message)
