from dataprep import read_data
from data_parcser import CallCenterStrcut

def test():
    design_name = 'Xdesign'
    struct_data= read_data(design_name)
    CCS = CallCenterStrcut()
    CCS.build_Xdesign(struct_data)
    CCS.describe()

if __name__ == "__main__":
    test()