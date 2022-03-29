import asyncio
import os
import tempfile
import sys
from typing import Callable, Dict, Type

import bpy
import mathutils

sys.path.append('.')
from protocol import *


def _set_item_pose(item, pose):
    """ Set the pose for an object

    NOTE: no keyframe animation will be set

    Params
    ------
    item: the object whose pose will be set
    pose: the desired pose, a 7-dim vector for xyz-quat
    """
    assert len(pose) == 7, \
        f"expecting a pose vector of length 7 (3 location dims, 4 rotation dims), got {len(pose)}"
    item.location = pose[:3]
    item.rotation_mode = 'QUATERNION'
    item.rotation_quaternion = mathutils.Quaternion(pose[3:])

def _add_meshes_handler(message: MeshesMessage):
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


def _add_primitive_handler(message: AddRigidBodyPrimitiveMessage):
    #message.create_primitive_in_blender()
    eval(message.primitive_type)(**message.params)
    item = bpy.context.active_object
    item.name = message.primitive_name

def _point_cloud_message_handler(message: DeformableMeshesMessage):
    """ If the point cloud has already existed in the Blender scene,
    update the points; otherwise, create a new object. 
    """
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

    meshes.from_pydata(message.particles, [], message.faces)
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


def _update_pose_message(message: UpdateRigidBodyPoseMessage):
    """ A keyframe animation will be set to move the rigid body to the 
    new pose defined by the message
    """
    if message.name in bpy.data.objects:
        obj = bpy.data.objects[message.name]
        _set_item_pose(obj, message.pose_vec)
        obj.keyframe_insert(data_path = 'location', frame = message.frame_idx)
        obj.keyframe_insert(data_path = 'rotation_quaternion', frame = message.frame_idx)
    else:
        raise ValueError(f"receive pose-updating message for {message.name},"+ \
            "but the object is not known by the Blender")

def _animation_finish_handler(message: FinishAnimationMessage):
    """ #TODO
    """
    dir, _, = os.path.split(os.path.realpath(__file__))
    bpy.data.scenes[0].frame_start = 0
    bpy.data.scenes[0].frame_end = message.end_frame_idx
    bpy.ops.wm.save_as_mainfile(filepath = os.path.join(dir, message.exp_name + ".blend"))
    exit(0)

MSG_CALLBACK_TABLE: Dict[Type, Callable[[BaseMessage], None]] = {
    MeshesMessage:                  _add_meshes_handler,
    AddRigidBodyPrimitiveMessage:    _add_primitive_handler,
    DeformableMeshesMessage:         _point_cloud_message_handler,
    UpdateRigidBodyPoseMessage:      _update_pose_message,
    FinishAnimationMessage:          _animation_finish_handler
}

def callback_entrance(message: BaseMessage) -> None:
    """ #TODO
    """
    message_type = type(message)
    if message_type in MSG_CALLBACK_TABLE:
        MSG_CALLBACK_TABLE[message_type](message)
    else:
        raise NotImplementedError(f"Message handler for {message_type} cannot be found")


server = AsyncServer(callback_entrance)
asyncio.run(server.run_server())
