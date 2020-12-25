from queue_system import QueueSystem, INF
from dataprep import read_data
from data_parcser import CallCenterStrcut
def run(design_name):
    struct_data= read_data(design_name)
    CCS = CallCenterStrcut()
    if design_name == 'Ndesign':
        CCS.build_Ndesign(struct_data)
    elif design_name == 'Xdesign':
        CCS.build_Xdesign(struct_data)
    elif design_name == 'Wdesign':
        CCS.build_Wdesign(struct_data)
    elif design_name == 'general_design':
        CCS.build_general_design(struct_data)
    test_queue = QueueSystem(360000, INF, CCS, 'G', 1000, 3600, 20, 80, 999)
    test_queue.run()
if __name__ == "__main__":
    run('Xdesign')     