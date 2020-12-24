from queue_system import QueueSystem, INF
from dataprep import read_data
from data_parcser import CallCenterStrcut
def run():
    design_name = 'Xdesign'
    struct_data= read_data(design_name)
    CCS = CallCenterStrcut()
    CCS.build_Xdesign(struct_data)
    test_queue = QueueSystem(360000, INF, CCS, 'G', 200, 80)
    test_queue.run()
if __name__ == "__main__":
    run()     