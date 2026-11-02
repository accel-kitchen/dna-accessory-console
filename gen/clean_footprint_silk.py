"""Remove imported silk that obstructs tiny LED / module pads; retain Fab geometry.

Pad geometry, numbering and models are untouched. Run once before rebuild.
"""
from pathlib import Path
import pcbnew as pcb, shutil
root=Path(__file__).resolve().parents[1]
lib=root/'lib'/'footprints.pretty'
backup=root/'design'/'pre-redesign-20261008'/'footprints.pretty'
backup.mkdir(exist_ok=True)
for name in ['SMD4_XL-1010RGBC_XLG','MODULE_102010448','JST_B2B-PH-SM4-TB']:
    file=lib/(name+'.kicad_mod')
    if not (backup/file.name).exists():shutil.copy2(file,backup/file.name)
    fp=pcb.FootprintLoad(str(lib),name)
    old={p.GetNumber():tuple(p.GetPosition()) for p in fp.Pads()}
    if name!='JST_B2B-PH-SM4-TB':
      for item in list(fp.GraphicalItems()):
        if item.GetLayer() in (pcb.F_SilkS,pcb.B_SilkS):fp.Delete(item)
    assert old=={p.GetNumber():tuple(p.GetPosition()) for p in fp.Pads()}
    if len(fp.Models())==0:
        m=pcb.FP_3DMODEL();m.m_Filename={'SMD4_XL-1010RGBC_XLG':'','MODULE_102010448':'${KIPRJMOD}/lib/102010448/102010448.step','JST_B2B-PH-SM4-TB':'${KIPRJMOD}/lib/B2B_PH_SM4_TB/B2B-PH-SM4-TB.step'}[name]
        if m.m_Filename:
            m.m_Rotation=pcb.VECTOR3D(-90,0,0);m.m_Scale=pcb.VECTOR3D(1,1,1);m.m_Show=True;fp.Add3DModel(m)
    pcb.FootprintSave(str(lib),fp)
    print('Cleaned silk only:',file.name)
