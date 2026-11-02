import sys
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopLoc import TopLoc_Location
def load(path):
    app=XCAFApp_Application.GetApplication_s()
    doc=TDocStd_Document(TCollection_ExtendedString('MDTV-XCAF'))
    app.InitDocument(doc)
    r=STEPCAFControl_Reader();r.SetNameMode(True);r.ReadFile(path);r.Transfer(doc)
    st=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    return doc,st
def name(l):
    n=TDataStd_Name()
    return n.Get_s if False else (l.FindAttribute(TDataStd_Name.GetID_s(),n) and n.Get().ToExtString())
def parts(path):
    """list of (name, shape) for top-level components"""
    doc,st=load(path)
    out=[]
    fl=TDF_LabelSequence();st.GetFreeShapes(fl)
    for i in range(1,fl.Length()+1):
        top=fl.Value(i)
        comps=TDF_LabelSequence()
        from OCP.XCAFDoc import XCAFDoc_ShapeTool
        if st.IsAssembly_s(top):
            XCAFDoc_ShapeTool.GetComponents_s(top,comps)
            for j in range(1,comps.Length()+1):
                c=comps.Value(j)
                sh=XCAFDoc_ShapeTool.GetShape_s(c)
                ref=TDF_LabelSequence()
                out.append((name(c),sh))
        else:
            out.append((name(top),XCAFDoc_ShapeTool.GetShape_s(top)))
    return out
def bb(sh):
    b=Bnd_Box();BRepBndLib.Add_s(sh,b);return [round(x,3) for x in b.Get()]
if __name__=='__main__':
    for n,s in parts(sys.argv[1])[:int(sys.argv[2]) if len(sys.argv)>2 else 10**6]:
        print(n,bb(s))
