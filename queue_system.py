import numpy as np
from abc import abstractmethod
import networkx as nx

from data_parcser import Server, ServiceTable, CustomerQueue, Customer

INF = 1000000

class QueueSystem:
    '''
        仿真参数：
         - simulation_time: 仿真时长, int型
         - queue_capacity: 队伍容量, int型
         - call_center_structure: 呼叫中心结构, networkx.Graph类
         - router: 路由规则, string型
         - AWT: Acceptable waiting time, float型
    '''

    def __init__(self, simulation_time, queue_capacity, call_center_structure, router, AWT):
        self.T = simulation_time
        self.queue_capacity = queue_capacity
        self.structure = call_center_structure
        self.router = router
        self.AWT = AWT
        self.K = call_center_structure.contract_types_num # number of contract types
        self.I = call_center_structure.agent_groups_num # number of agent groups
        '''
            Counters:
                goodSL_num: number of served calls that have waited no more than AWT
                served_num: number of served calls
                abandoned_num: number of abandoned calls
                abandoned_afterAWT_num: number if abandoned calls after AWT
            Ratios:
                SL: service level, goodSL_num / (served_num + abandoned_afterAWT)
                abandon_ratio: abandoned_num / (served_num + abandoned_num)
                occupancy_ratio: sum(busy_agent_num) / (agent_num * T)
        '''
        self.goodSL_num = [[0 for i in range(K)] for j in range(T)]
        self.served_num = [[0 for i in range(K)] for j in range(T)]
        self.abandoned_num = [[0 for i in range(K)] for j in range(T)]
        self.abandoned_afterAWT_num = [[0 for i in range(K)] for j in range(T)]
        self.busy_agent_num = [[0 for i in range(I)] for j in range(T)]
        self.SL = [[0 for i in range(K)] for j in range(T)]
        self.abandon_ratio = [[0 for i in range(K)] for j in range(T)]
        self.occupancy_ratio = [[0 for i in range(I)] for j in range(T)]

    def clear(self):
        self.K = 0
        self.I = 0
        self.router = 'G'
        self.structure.clear()
        self.goodSL_num.clear()
        self.served_num.clear()
        self.abandoned_num.clear()
        self.abandoned_afterAWT_num.clear()
        self.busy_agent_num.clear()
        self.SL.clear()
        self.abandon_ratio.clear()
        self.occupancy_ratio.clear()

    def 
