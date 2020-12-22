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
        self.t = 0
        self.queue = []
        self.queue_capacity = queue_capacity
        self.structure = call_center_structure
        self.router = router
        self.AWT = AWT
        self.K = call_center_structure.contract_types_num # number of contract types
        self.I = call_center_structure.agent_groups_num # number of agent groups
        self.customer_nodes = list(call_center_structure.G.nodes())[:self.K] # first K nodes are customer nodes
        self.agent_nodes = list(call_center_structure.G.nodes())[self.K:] # remain nodes are agent nodes
        self.calls_flow = {} # record the arrival time of each call
        self.service_flow = [] # record the call sorted by service finish time
        self.patience_flow = [] # record the call sorted by patience time 
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
        self.goodSL_num = {c: 0 for c in self.customer_nodes}
        self.served_num = {c: 0 for c in self.customer_nodes}
        self.abandoned_num = {c: 0 for c in self.customer_nodes}
        self.abandoned_afterAWT_num = {c: 0 for c in self.customer_nodes}
        self.busy_agent_num = {s: 0 for s in self.agent_nodes}
        self.SL = {c: [] for c in self.customer_nodes}
        self.abandon_ratio = {c: [] for c in self.customer_nodes}
        self.occupancy_ratio = {s: [] for s in self.agent_nodes}
        '''
            random generator, only support the specific (poisson, exponential, exponential) combination
        '''
        if self.structure.distribution['arrival'] == 'poisson':
            self.arrival_generator = np.random.exponential
        if self.structure.distribution['service'] == 'exponential':
            self.service_generator = np.random.exponential
        if self.structure.distribution['patience'] == 'exponential':
            self.patience_generator = np.random.exponential

        self.current_event = [] # record current arrival event and service event
        
        self.agent_groups = {}
        for i in range(self.I):
            name = self.agent_nodes[i]
            capacity = call_center_structure.nodes[name]['capacity']
            self.agent_groups[name] = ServiceTable(name, [Server(name, i) for i in range(capacity)])

    def clear(self):
        self.t = 0
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

    def generate_calls_flow(self, call_flow_size):
        ''' generate call flow and convert it to second format'''
        for c in self.customer_nodes:
            intervals = self.arrival_generator(self.structure.G.nodes[c]['lmbda'], (call_flow_size, ))
            arrival_time = intervals.cumsum() * 60
            self.calls_flow[c] = arrival_time.astype(int)

    def check_arrival_event(self):
        for c in self.calls_flow:
            for i, arrival_time in enumerate(self.calls_flow[c]):
                if arrival_time <= self.t:
                    self.current_event.append(('arrival', c, arrival_time, i))
                else:
                    break

    def check_service_event(self):
        for i, S in enumerate(self.service_flow):
            if S.finish_time <= self.t:
                self.agent_groups[S.name].servers[S.index].finish_order()
                self.current_event.append(('service', S, i))
            else:
                break

    def check_abandon_event(self):
        for i, C in enumerate(self.patience_flow):
            if C.patience_time <= self.t:
                self.current_event.append(('patience', C, i))
            else:
                break

    def choose_server_byG(self, C, choices):
        '''select agent group with longest idle time(earlist last finish time)'''
        choices.sort(key=lambda x: self.agent_groups[x].last_finish_time)
        return choices[0]

    def choose_server(self, C):
        choices = list(self.structure.G[C.name])
        for i, v in choices:
            if not self.agent_groups[v].is_available:
                choices.pop(i)
        if len(choices) == 0:
            return -1
        if len(choices) == 1:
            return choices[0]
        if self.router == 'G':
            return self.choose_server_byG(C, choices)
    
    def choose_customer_byG(self, S, choices):
        if len(self.queue) == 0:
            return -1
        for i, C in self.queue:
            if C.name in choices:
                return i
        return -1

    def choose_customer(self, S):
        choices = list(self.structure.G[S.name])
        if self.router == 'G':
            return self.choose_customer_byG(S, choices)
           
    def insert_into_service_flow(self, S):
        index = len(self.service_flow)
        for i, S_ in enumerate(self.service_flow):
            if S_.finish_time >= S.finish_time:
                index = i
                break
        self.service_flow.insert(index, S)

    def insert_into_patience_flow(self, C):
        index = len(self.patience_flow)
        for i, C_ in enumerate(self.patience_flow):
            if C_.patience_time >= C.patience_time:
                index = i
                break
        self.patience_flow.insert(index, C)

    def assign_customer_to_server(self, C, s):
        '''s is the agent group name'''
        service_time = int(self.service_generator(self.structure.G[s][C.name]['mu']) * 60)
        index = self.agent_groups[s].get_idlest_server_index
        self.agent_groups[s].servers[index].receive_order(self.t, C.name, service_time)
        self.insert_into_service_flow(self.agent_groups[s].servers[index])

    def put_into_queue(self, C):
        name = C.name
        patience_time = int(self.patience_generator(self.structure.G.nodes[name]['nu']) * 60)
        C.patience_time = self.t + patience_time
        C.queue_index = len(self.queue)
        self.queue.append(C) # don't consider queue capacity
        self.insert_into_patience_flow(C)

    def step(self):
        self.check_arrival_event()
        self.check_service_event()
        self.check_abandon_event()
        for event in self.current_event:
            if event[0] == 'arrival':
                c, i = event[1], event[-1]
                self.calls_flow[c].pop(i)
                C = Customer(event[1], event[2])
                s = self.choose_server(C)
                if s == -1:
                    self.put_into_queue(C)
                else:
                    self.assign_customer_to_server(C, s)
                    self.goodSL_num[C.name] += 1
            elif event[0] == 'service':
                S, i = event[1], event[-1]
                self.service_flow.pop(i)
                index = self.choose_customer(S)
                if index != -1:
                    C = self.queue[index]
                    self.served_num[C.name] += 1
                    if C.waiting_time <= self.AWT:
                        self.goodSL_num[C.name] += 1    
                    self.assign_customer_to_server(C, S.name)
                    self.queue.pop(index)
            elif event[0] == 'abandon':
                C, i = event[1], event[-1]
                self.patience_flow.pop(i)
                self.abandoned_num[C.name] += 1
                if C.waiting_time > self.AWT:
                    self.abandoned_afterAWT_num[C.name] += 1
                self.queue.pop(C.queue_index)
                
