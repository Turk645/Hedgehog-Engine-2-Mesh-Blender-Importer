bl_info = {
    "name": "Hedgehog Engine 2 Animation Import",
    "author": "Turk",
    "version": (1, 0, 0),
    "blender": (2, 82, 0),
    "location": "File > Import-Export",
    "description": "A script to import animations from Hedgehog Engine 2 games",
    "warning": "",
    "category": "Import-Export",
}
import sys
import bpy
import bmesh
import os
import io
import struct
import math
import mathutils
from bpy.props import (BoolProperty,
                       FloatProperty,
                       StringProperty,
                       EnumProperty,
                       CollectionProperty
                       )
from bpy_extras.io_utils import ImportHelper

class HedgeEngineAnimation(bpy.types.Operator, ImportHelper):
    bl_idname = "custom_import_scene.hedgeenganim"
    bl_label = "Import"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".model"
    filter_glob: StringProperty(
            default="*.pxd",
            options={'HIDDEN'},
            )
    filepath: StringProperty(subtype='FILE_PATH',)
    files: CollectionProperty(type=bpy.types.PropertyGroup)
    
    def draw(self, context):
        pass
    def execute(self, context):
        Arm = bpy.context.active_object
        Scene = bpy.context.scene
        if Arm.type == 'ARMATURE':
            CurFile = open(self.filepath,"rb")
            
            
            CurFile.seek(0x58)
            PlayRate = struct.unpack('<f', CurFile.read(0x4))[0]
            FrameCount = int.from_bytes(CurFile.read(4),byteorder='little')
            Scene.render.fps = FrameCount/PlayRate
            Scene.frame_end = FrameCount
            TableCount = int.from_bytes(CurFile.read(8),byteorder='little') #actually bone count, and bone table is actually a frame table
            TableOffset = int.from_bytes(CurFile.read(8),byteorder='little')+0x40
            
            
            CurFile.seek(TableOffset)
            utils_set_mode("POSE")
            
            BoneTable = []
            for x in range(TableCount):
                CurFile.seek(TableOffset+0x48*x)
                PosBoneCount = int.from_bytes(CurFile.read(8),byteorder='little')
                PosBoneOffset = int.from_bytes(CurFile.read(8),byteorder='little')+0x40
                PosBoneData = int.from_bytes(CurFile.read(8),byteorder='little')+0x40
                RotBoneCount = int.from_bytes(CurFile.read(8),byteorder='little')
                RotBoneOffset = int.from_bytes(CurFile.read(8),byteorder='little')+0x40
                RotBoneData = int.from_bytes(CurFile.read(8),byteorder='little')+0x40
                ScaleBoneCount = int.from_bytes(CurFile.read(8),byteorder='little')
                ScaleBoneOffset = int.from_bytes(CurFile.read(8),byteorder='little')+0x40
                ScaleBoneData = int.from_bytes(CurFile.read(8),byteorder='little')+0x40
                FrameTable = {}
                for y in range(PosBoneCount):
                    CurFile.seek(PosBoneOffset+0x2*y)
                    tmpFrame = int.from_bytes(CurFile.read(2),byteorder='little')
                    CurFile.seek(PosBoneData+0x10*y)
                    tmpPos = struct.unpack('<fff', CurFile.read(0xC))
                    FT = FrameTable.get("Frame:"+str(tmpFrame))
                    if not FT:
                        FT = FrameTable["Frame:"+str(tmpFrame)]={}
                    FT["Pos"] = tmpPos
                for y in range(RotBoneCount):
                    CurFile.seek(RotBoneOffset+0x2*y)
                    tmpFrame = int.from_bytes(CurFile.read(2),byteorder='little')
                    CurFile.seek(RotBoneData+0x10*y)
                    tmpPos = struct.unpack('<ffff', CurFile.read(0x10))
                    FT = FrameTable.get("Frame:"+str(tmpFrame))
                    if not FT:
                        FT = FrameTable["Frame:"+str(tmpFrame)]={}
                    FT["Rot"] = (tmpPos[3],tmpPos[0],tmpPos[1],tmpPos[2])
                for y in range(ScaleBoneCount):
                    CurFile.seek(ScaleBoneOffset+0x2*y)
                    tmpFrame = int.from_bytes(CurFile.read(2),byteorder='little')
                    CurFile.seek(ScaleBoneData+0x10*y)
                    tmpPos = struct.unpack('<fff', CurFile.read(0xC))
                    FT = FrameTable.get("Frame:"+str(tmpFrame))
                    if not FT:
                        FT = FrameTable["Frame:"+str(tmpFrame)]={}
                    FT["Scale"] = tmpPos
                BoneTable.append(FrameTable)
            for x in range(FrameCount): #FrameCount
                Scene.frame_set(x)
                for y in range(len(BoneTable)):
                    Frame = BoneTable[y].get("Frame:"+str(x))
                    if Frame:
                        Pos = Frame.get("Pos")
                        Rot = Frame.get("Rot")
                        Scale = Frame.get("Scale")
                        Bone = Arm.pose.bones[y]
                        
                        if Bone.parent:
                            ParentMat = Bone.parent.matrix.copy()
                        else:
                            ParentMat = mathutils.Matrix()
                        DiffMat = ParentMat - Bone.matrix
                        
                        if Pos:
                            Bone.location = Arm.convert_space(pose_bone=Bone,matrix = ParentMat @ ((mathutils.Matrix.Translation(Frame["Pos"]))),from_space='POSE',to_space='LOCAL').translation
                            Bone.keyframe_insert("location")
                        if Rot:
                            Bone.rotation_quaternion = Arm.convert_space(pose_bone=Bone,matrix = ParentMat @ ((mathutils.Quaternion(Frame["Rot"])).to_matrix().to_4x4()),from_space='POSE',to_space='LOCAL').to_quaternion()
                            Bone.keyframe_insert("rotation_quaternion")
                        if Scale:
                            Bone.scale = Frame["Scale"]
                            Bone.keyframe_insert("scale")
                    
            
            CurFile.close()
            del CurFile
        return {'FINISHED'}

def utils_set_mode(mode):
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode=mode, toggle=False)

def menu_func_import(self, context):
    self.layout.operator(HedgeEngineAnimation.bl_idname, text="Hedgehog Engine (.pxd)")
        
def register():
    bpy.utils.register_class(HedgeEngineAnimation)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    
def unregister():
    bpy.utils.unregister_class(HedgeEngineAnimation)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
        
if __name__ == "__main__":
    register()
